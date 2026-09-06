"""Managed sing-box V2Ray Stats API configuration for Marzban accounting."""
from __future__ import annotations

from copy import deepcopy
from typing import Iterable, Mapping


def api_listen(host: str, port: int) -> str:
    """Format a host/port pair for sing-box, including IPv6 literals."""
    clean_host = host.strip()
    if not clean_host:
        raise ValueError("sing-box traffic API host cannot be empty")
    if not 1 <= port <= 65535:
        raise ValueError("sing-box traffic API port must be between 1 and 65535")
    if ":" in clean_host and not clean_host.startswith("["):
        clean_host = f"[{clean_host}]"
    return f"{clean_host}:{port}"


def install_traffic_api(
    config: Mapping,
    *,
    host: str,
    port: int,
    inbound_tag: str,
    users: Iterable[str],
) -> dict:
    """Install the protected per-user V2Ray Stats API in a merged config."""
    result = deepcopy(dict(config))
    experimental = result.get("experimental")
    if experimental is None:
        experimental = {}
    elif not isinstance(experimental, Mapping):
        raise ValueError("sing-box experimental must be a JSON object")
    else:
        experimental = deepcopy(dict(experimental))

    tracked_users = list(dict.fromkeys(
        user for user in users if isinstance(user, str) and user
    ))
    experimental["v2ray_api"] = {
        "listen": api_listen(host, port),
        "stats": {
            "enabled": True,
            "inbounds": [inbound_tag],
            "users": tracked_users,
        },
    }
    result["experimental"] = experimental
    return result
