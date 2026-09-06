from __future__ import annotations

from copy import deepcopy
import json
import os
import re
import tempfile
from ipaddress import ip_network
from pathlib import Path
from typing import Literal, Mapping
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator


_INTERVAL = re.compile(r"^[1-9][0-9]*(?:s|m|h|d)$")


class RuleSetItem(BaseModel):
    enabled: bool = True
    tag: str = Field(min_length=1, max_length=128)
    type: Literal["remote", "local", "inline"] = "remote"
    format: Literal["binary", "source"] = "binary"
    url: str = ""
    path: str = ""
    download_detour: str = "direct"
    update_interval: str = "1d"
    outbound: str = ""
    ip_cidr: list[str] = Field(default_factory=list)
    ip_cidr_match_source: bool = False

    @field_validator("ip_cidr", mode="before")
    @classmethod
    def parse_ip_cidrs(cls, value):
        if isinstance(value, str):
            return [item.strip() for item in value.replace(",", "\n").splitlines() if item.strip()]
        return value

    @field_validator("tag", "url", "path", "download_detour", "update_interval", "outbound", mode="before")
    @classmethod
    def strip_strings(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_source(self):
        if not self.enabled:
            return self
        if self.type == "remote":
            parsed = urlparse(self.url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                raise ValueError(f"Remote rule set {self.tag} requires an HTTP(S) URL")
            if self.update_interval and not _INTERVAL.fullmatch(self.update_interval):
                raise ValueError(
                    f"Remote rule set {self.tag} update_interval must look like 30m, 12h or 1d"
                )
        elif self.type == "local":
            if not self.path:
                raise ValueError(f"Local rule set {self.tag} requires a path")
        else:
            if not self.ip_cidr:
                raise ValueError(f"Inline IP rule set {self.tag} requires at least one IP or CIDR")
            normalized = []
            for value in self.ip_cidr:
                try:
                    network = str(ip_network(value.strip(), strict=False))
                except (AttributeError, ValueError) as exc:
                    raise ValueError(f"Inline IP rule set {self.tag} contains an invalid IP/CIDR: {value}") from exc
                if network not in normalized:
                    normalized.append(network)
            self.ip_cidr = normalized
        return self


class RuleSetsSettings(BaseModel):
    cache_enabled: bool = True
    cache_path: str = "/var/lib/marzban/sing-box-cache.db"
    items: list[RuleSetItem] = Field(default_factory=list)

    @field_validator("cache_path", mode="before")
    @classmethod
    def strip_cache_path(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_unique_tags(self):
        if self.cache_enabled and not self.cache_path:
            raise ValueError("Rule set cache path is required when cache is enabled")
        tags = [item.tag for item in self.items if item.enabled]
        duplicates = sorted({tag for tag in tags if tags.count(tag) > 1})
        if duplicates:
            raise ValueError("Duplicate rule set tags: " + ", ".join(duplicates))
        return self


def load_rule_sets(path: str) -> tuple[RuleSetsSettings, bool]:
    source = Path(path)
    if not source.exists():
        return RuleSetsSettings(), False
    try:
        return RuleSetsSettings.model_validate_json(source.read_text(encoding="utf-8")), True
    except (OSError, ValueError) as exc:
        raise ValueError(f"Unable to load sing-box rule sets: {exc}") from exc


def save_rule_sets(path: str, settings: RuleSetsSettings) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=".marzban-sing-box-rule-sets-", suffix=".json.tmp", dir=destination.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(settings.model_dump(), file, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _definition(item: RuleSetItem) -> dict:
    if item.type == "inline":
        return {
            "type": "inline",
            "tag": item.tag,
            "rules": [{"ip_cidr": item.ip_cidr}],
        }
    value = {"type": item.type, "tag": item.tag, "format": item.format}
    if item.type == "remote":
        value["url"] = item.url
        if item.download_detour:
            value["download_detour"] = item.download_detour
        if item.update_interval:
            value["update_interval"] = item.update_interval
    else:
        value["path"] = item.path
    return value


def _route_rule(item: RuleSetItem) -> dict:
    rule = {
        "rule_set": [item.tag],
        "action": "route",
        "outbound": item.outbound,
    }
    if item.ip_cidr_match_source:
        rule["rule_set_ip_cidr_match_source"] = True
    return rule


def merge_rule_sets(config: Mapping, settings: RuleSetsSettings) -> dict:
    """Inject managed rule-set definitions/rules without replacing custom route rules."""
    result = deepcopy(dict(config))
    route = result.setdefault("route", {})
    if not isinstance(route, dict):
        raise ValueError("sing-box route must be an object before rule sets are applied")
    existing_sets = route.get("rule_set", [])
    if not isinstance(existing_sets, list):
        raise ValueError("sing-box route.rule_set must be an array")
    existing_tags = {
        item.get("tag") for item in existing_sets
        if isinstance(item, dict) and isinstance(item.get("tag"), str)
    }
    active = [item for item in settings.items if item.enabled]
    conflicts = sorted(existing_tags.intersection(item.tag for item in active))
    if conflicts:
        raise ValueError(
            "Rule set tags already exist in advanced JSON: " + ", ".join(conflicts)
        )
    route["rule_set"] = existing_sets + [_definition(item) for item in active]
    existing_rules = route.get("rules", [])
    if not isinstance(existing_rules, list):
        raise ValueError("sing-box route.rules must be an array")
    managed_rules = [_route_rule(item) for item in active if item.outbound]
    route["rules"] = managed_rules + existing_rules
    if settings.cache_enabled:
        experimental = result.setdefault("experimental", {})
        if not isinstance(experimental, dict):
            raise ValueError("sing-box experimental must be an object")
        cache = experimental.setdefault("cache_file", {})
        if not isinstance(cache, dict):
            raise ValueError("sing-box experimental.cache_file must be an object")
        cache["enabled"] = True
        cache["path"] = settings.cache_path
    return result
