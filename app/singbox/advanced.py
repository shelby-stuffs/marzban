from __future__ import annotations

from copy import deepcopy
import json
import os
import tempfile
from pathlib import Path
from typing import Mapping


RESERVED_TOP_LEVEL_KEYS = {"inbounds"}
ALLOWED_TOP_LEVEL_KEYS = {
    "log",
    "dns",
    "ntp",
    "certificate",
    "endpoints",
    "outbounds",
    "route",
    "services",
    "experimental",
}

DEFAULT_ADVANCED_CONFIG = {
    "outbounds": [{"type": "direct", "tag": "direct"}],
    "route": {"rules": [], "final": "direct"},
}


def validate_advanced_config(value: Mapping) -> dict:
    if not isinstance(value, Mapping):
        raise ValueError("Advanced sing-box config must be a JSON object")
    config = deepcopy(dict(value))
    reserved = RESERVED_TOP_LEVEL_KEYS.intersection(config)
    if reserved:
        raise ValueError(
            "Managed top-level keys cannot be edited here: " + ", ".join(sorted(reserved))
        )
    unsupported = set(config).difference(ALLOWED_TOP_LEVEL_KEYS)
    if unsupported:
        raise ValueError(
            "Unsupported sing-box top-level keys: " + ", ".join(sorted(unsupported))
        )
    typed_sections = {
        "log": dict,
        "dns": dict,
        "ntp": dict,
        "certificate": dict,
        "endpoints": list,
        "outbounds": list,
        "route": dict,
        "services": list,
        "experimental": dict,
    }
    for key, expected in typed_sections.items():
        if key in config and not isinstance(config[key], expected):
            raise ValueError(f"sing-box {key} must be a JSON {expected.__name__}")
    if "outbounds" in config:
        tags = []
        for index, outbound in enumerate(config["outbounds"]):
            if not isinstance(outbound, dict):
                raise ValueError(f"sing-box outbound #{index + 1} must be an object")
            tag = outbound.get("tag")
            if tag is not None:
                if not isinstance(tag, str) or not tag:
                    raise ValueError(f"sing-box outbound #{index + 1} has an invalid tag")
                if tag in tags:
                    raise ValueError(f"Duplicate sing-box outbound tag: {tag}")
                tags.append(tag)
    try:
        json.dumps(config)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Advanced sing-box config is not JSON serializable: {exc}") from exc
    return config


def load_advanced_config(path: str) -> tuple[dict, bool]:
    source = Path(path)
    if not source.exists():
        return deepcopy(DEFAULT_ADVANCED_CONFIG), False
    try:
        value = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Unable to load advanced sing-box config: {exc}") from exc
    return validate_advanced_config(value), True


def save_advanced_config(path: str, config: Mapping) -> None:
    value = validate_advanced_config(config)
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=".marzban-sing-box-advanced-", suffix=".json.tmp", dir=destination.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(value, file, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
