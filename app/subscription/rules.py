"""Client detection rules for subscription delivery.

The legacy implementation hard-coded an ``if re.match(user_agent)`` chain inside
the subscription router. This module turns every branch of that chain into a
declarative rule so the same logic can be stored in the database and edited from
the dashboard, while the built-in defaults keep the historical behaviour intact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from distutils.version import LooseVersion
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Tuple

from config import (
    USE_CUSTOM_JSON_DEFAULT,
    USE_CUSTOM_JSON_FOR_HAPP,
    USE_CUSTOM_JSON_FOR_NPVTUNNEL,
    USE_CUSTOM_JSON_FOR_STREISAND,
    USE_CUSTOM_JSON_FOR_V2RAYN,
    USE_CUSTOM_JSON_FOR_V2RAYNG,
)

#: Every output format the subscription pipeline can render.
CONFIG_FORMATS: Tuple[str, ...] = (
    "v2ray",
    "v2ray-json",
    "clash",
    "clash-meta",
    "sing-box",
    "outline",
    "hysteria2",
    "happ",
)

MEDIA_TYPES: Dict[str, str] = {
    "v2ray": "text/plain",
    "v2ray-json": "application/json",
    "clash": "text/yaml",
    "clash-meta": "text/yaml",
    "sing-box": "application/json",
    "outline": "application/json",
    "hysteria2": "text/plain",
    "happ": "application/json",
}

#: Mutable so tests and runtime reloads can flip the custom-JSON switches
#: without re-importing the module.
CUSTOM_JSON_FLAGS: Dict[str, bool] = {
    "default": USE_CUSTOM_JSON_DEFAULT,
    "v2rayn": USE_CUSTOM_JSON_FOR_V2RAYN,
    "v2rayng": USE_CUSTOM_JSON_FOR_V2RAYNG,
    "streisand": USE_CUSTOM_JSON_FOR_STREISAND,
    "happ": USE_CUSTOM_JSON_FOR_HAPP,
    "npvtunnel": USE_CUSTOM_JSON_FOR_NPVTUNNEL,
}


def media_type_for(config_format: str) -> str:
    """Return the HTTP media type used for a rendered format."""
    try:
        return MEDIA_TYPES[config_format]
    except KeyError:
        raise ValueError(f'Unsupported format "{config_format}"')


@lru_cache(maxsize=512)
def _compile(pattern: str, ignore_case: bool) -> re.Pattern:
    return re.compile(pattern, re.IGNORECASE if ignore_case else 0)


def _as_version(value: str) -> Optional[LooseVersion]:
    try:
        return LooseVersion(value)
    except Exception:
        return None


@dataclass(frozen=True)
class ResolvedClient:
    """The delivery decision for a single subscription request."""

    name: str
    config_format: str
    as_base64: bool
    reverse: bool
    source: str = "builtin"

    @property
    def media_type(self) -> str:
        return media_type_for(self.config_format)


@dataclass(frozen=True)
class ClientRule:
    """A declarative User-Agent rule.

    ``min_version`` / ``max_version`` compare the first capture group of the
    pattern, which is how the legacy chain gated v2rayN, v2rayNG and Happ.
    """

    name: str
    pattern: str
    config_format: str
    as_base64: bool = False
    reverse: bool = False
    priority: int = 100
    ignore_case: bool = False
    min_version: Optional[str] = None
    max_version: Optional[str] = None
    custom_json_flag: Optional[str] = None
    source: str = "builtin"

    @property
    def enabled(self) -> bool:
        if self.custom_json_flag is None:
            return True
        return bool(
            CUSTOM_JSON_FLAGS.get("default") or CUSTOM_JSON_FLAGS.get(self.custom_json_flag)
        )

    def matches(self, user_agent: str) -> bool:
        if not self.enabled:
            return False

        match = _compile(self.pattern, self.ignore_case).search(user_agent or "")
        if not match:
            return False

        if self.min_version is None and self.max_version is None:
            return True

        # Version gates need a capture group holding the client version.
        if match.re.groups < 1:
            return False
        raw_version = match.group(1)
        if not raw_version:
            return False

        version = _as_version(raw_version)
        if version is None:
            return False

        if self.min_version is not None:
            minimum = _as_version(self.min_version)
            if minimum is None or version < minimum:
                return False
        if self.max_version is not None:
            maximum = _as_version(self.max_version)
            if maximum is None or version > maximum:
                return False
        return True

    def resolved(self) -> ResolvedClient:
        return ResolvedClient(
            name=self.name,
            config_format=self.config_format,
            as_base64=self.as_base64,
            reverse=self.reverse,
            source=self.source,
        )


#: Anything that does not match a rule keeps receiving base64 share links, which
#: is what the legacy ``else`` branch did.
FALLBACK_CLIENT = ResolvedClient(
    name="v2ray-base64",
    config_format="v2ray",
    as_base64=True,
    reverse=False,
    source="fallback",
)

DEFAULT_RULES: Tuple[ClientRule, ...] = (
    ClientRule(
        name="clash-meta",
        pattern=r"^([Cc]lash-verge|[Cc]lash[-\.]?[Mm]eta|[Ff][Ll][Cc]lash|[Mm]ihomo)",
        config_format="clash-meta",
        priority=10,
    ),
    ClientRule(
        name="clash",
        pattern=r"^([Cc]lash|[Ss]tash)",
        config_format="clash",
        priority=20,
    ),
    # Native Hysteria clients only understand hysteria2:// links, so they get a
    # filtered link list instead of the mixed one.
    ClientRule(
        name="hysteria",
        pattern=r"^[Hh]ysteria",
        config_format="hysteria2",
        priority=25,
    ),
    ClientRule(
        name="sing-box",
        pattern=r"^(SFA|SFI|SFM|SFT|[Kk]aring|[Hh]iddify[Nn]ext)|.*sing[-b]?ox.*",
        config_format="sing-box",
        priority=30,
        ignore_case=True,
    ),
    ClientRule(
        name="outline",
        pattern=r"^(SS|SSR|SSD|SSS|Outline|Shadowsocks|SSconf)",
        config_format="outline",
        priority=40,
    ),
    ClientRule(
        name="v2rayn-json",
        pattern=r"^v2rayN/(\d+\.\d+)",
        config_format="v2ray-json",
        priority=50,
        min_version="6.40",
        custom_json_flag="v2rayn",
    ),
    ClientRule(
        name="v2rayng-json",
        pattern=r"^v2rayNG/(\d+\.\d+\.\d+)",
        config_format="v2ray-json",
        priority=60,
        min_version="1.8.29",
        custom_json_flag="v2rayng",
    ),
    ClientRule(
        name="v2rayng-json-reversed",
        pattern=r"^v2rayNG/(\d+\.\d+\.\d+)",
        config_format="v2ray-json",
        priority=61,
        reverse=True,
        min_version="1.8.18",
        custom_json_flag="v2rayng",
    ),
    ClientRule(
        name="streisand-json",
        pattern=r"^[Ss]treisand",
        config_format="v2ray-json",
        priority=70,
        custom_json_flag="streisand",
    ),
    ClientRule(
        name="happ-json",
        pattern=r"^Happ/(\d+\.\d+\.\d+)",
        config_format="v2ray-json",
        priority=80,
        min_version="1.11.0",
        custom_json_flag="happ",
    ),
    ClientRule(
        name="npv-tunnel-json",
        pattern=r"ktor-client",
        config_format="v2ray-json",
        priority=90,
        custom_json_flag="npvtunnel",
    ),
)


def sorted_rules(rules: Iterable[ClientRule]) -> List[ClientRule]:
    """Rules are evaluated by ascending priority, then by name for stability."""
    return sorted(rules, key=lambda rule: (rule.priority, rule.name))


def resolve_client(
    user_agent: str,
    rules: Optional[Iterable[ClientRule]] = None,
) -> ResolvedClient:
    """Pick the delivery format for a User-Agent.

    Passing ``rules`` overrides the built-in defaults, which is how database
    rules take over at runtime.
    """
    candidates = DEFAULT_RULES if rules is None else rules
    for rule in sorted_rules(candidates):
        if rule.matches(user_agent or ""):
            return rule.resolved()
    return FALLBACK_CLIENT


def resolve_format(config_format: str) -> ResolvedClient:
    """Build a decision for an explicitly requested format."""
    if config_format not in CONFIG_FORMATS:
        raise ValueError(f'Unsupported format "{config_format}"')
    return ResolvedClient(
        name=config_format,
        config_format=config_format,
        as_base64=config_format == "v2ray",
        reverse=False,
        source="explicit",
    )
