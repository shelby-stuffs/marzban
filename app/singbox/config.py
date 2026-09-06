"""Pure conversion between Marzban's legacy Hysteria metadata and sing-box.

The control-plane metadata remains readable from XRayConfig during the first
migration stage, but Hysteria inbounds are removed from the config sent to the
Xray process when SINGBOX_HYSTERIA_ENABLED is set.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Iterable, Mapping


def hysteria_tags(config: Mapping) -> set[str]:
    return {
        inbound.get("tag")
        for inbound in config.get("inbounds", [])
        if isinstance(inbound, Mapping)
        and inbound.get("protocol") == "hysteria"
        and isinstance(inbound.get("tag"), str)
    }


def strip_hysteria_from_xray(config: Mapping) -> dict:
    """Return an Xray runtime config without native Hysteria inbounds/rules."""
    result = deepcopy(dict(config))
    tags = hysteria_tags(result)
    if not tags:
        return result
    result["inbounds"] = [
        inbound for inbound in result.get("inbounds", [])
        if inbound.get("tag") not in tags
    ]
    routing = result.get("routing")
    if isinstance(routing, dict):
        cleaned = []
        for rule in routing.get("rules", []):
            rule = deepcopy(rule)
            inbound_tags = rule.get("inboundTag")
            if isinstance(inbound_tags, list):
                remaining = [tag for tag in inbound_tags if tag not in tags]
                if not remaining:
                    continue
                rule["inboundTag"] = remaining
            cleaned.append(rule)
        routing["rules"] = cleaned
    return result


def _server_obfs(stream: Mapping) -> dict | None:
    finalmask = stream.get("finalmask")
    if isinstance(finalmask, Mapping):
        udp = finalmask.get("udp")
        if not udp:
            return None
        for item in udp if isinstance(udp, list) else []:
            if not isinstance(item, Mapping) or item.get("type") != "salamander":
                continue
            password = item.get("settings", {}).get("password")
            if isinstance(password, str) and password:
                return {"type": "salamander", "password": password}
        raise ValueError("Hysteria2 finalmask must contain one plain Salamander password")
    legacy = stream.get("hysteriaSettings", {})
    if legacy.get("obfs") == "salamander" and legacy.get("obfsPassword"):
        return {"type": "salamander", "password": legacy["obfsPassword"]}
    return None


def _server_tls(stream: Mapping) -> dict:
    if stream.get("security") != "tls":
        raise ValueError("sing-box Hysteria2 requires TLS")
    tls = stream.get("tlsSettings") or {}
    certs = tls.get("certificates") or []
    if not certs or not isinstance(certs[0], Mapping):
        raise ValueError("sing-box Hysteria2 requires a TLS certificate and key")
    cert = certs[0]
    result = {"enabled": True, "alpn": tls.get("alpn") or ["h3"]}
    if cert.get("certificateFile") and cert.get("keyFile"):
        result.update(certificate_path=cert["certificateFile"], key_path=cert["keyFile"])
    elif cert.get("certificate") and cert.get("key"):
        result.update(certificate=cert["certificate"], key=cert["key"])
    else:
        raise ValueError("Hysteria2 TLS certificate must use file paths or inline PEM data")
    return result


def build_hysteria2_server_config(
    xray_config: Mapping,
    users_by_tag: Mapping[str, Iterable[Mapping]],
) -> dict:
    """Build a standalone sing-box server config for all Hysteria2 inbounds."""
    inbounds = []
    for source in xray_config.get("inbounds", []):
        if source.get("protocol") != "hysteria":
            continue
        tag = source.get("tag")
        port = source.get("port")
        if not isinstance(tag, str) or not tag:
            raise ValueError("Hysteria2 inbound requires a tag")
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            raise ValueError(f"Hysteria2 inbound {tag} requires one integer UDP port")
        stream = source.get("streamSettings") or {}
        method = stream.get("method") or stream.get("network")
        if method != "hysteria":
            raise ValueError(f"Hysteria2 inbound {tag} requires hysteria transport")
        users = []
        for user in users_by_tag.get(tag, []):
            name, password = user.get("name"), user.get("password")
            if not isinstance(name, str) or not name or not isinstance(password, str) or not password:
                raise ValueError(f"Hysteria2 inbound {tag} contains an invalid user")
            users.append({"name": name, "password": password})
        inbound = {
            "type": "hysteria2",
            "tag": tag,
            "listen": source.get("listen") or "::",
            "listen_port": port,
            "users": users,
            "tls": _server_tls(stream),
        }
        protocol_settings = source.get("settings") or {}
        for source_key, target_key in (("up_mbps", "up_mbps"), ("down_mbps", "down_mbps")):
            value = protocol_settings.get(source_key)
            if isinstance(value, int) and value > 0:
                inbound[target_key] = value
        obfs = _server_obfs(stream)
        if obfs:
            inbound["obfs"] = obfs
        inbounds.append(inbound)
    return {
        "log": {"level": "info", "timestamp": True},
        "inbounds": inbounds,
        "outbounds": [{"type": "direct", "tag": "direct"}],
        "route": {"final": "direct"},
    }



def build_hysteria2_settings_config(settings: Mapping, users: Iterable[Mapping]) -> dict:
    """Build the native sing-box config from the dedicated settings document."""
    if not settings.get("enabled", True):
        return {"log": {"level": "info", "timestamp": True}, "inbounds": [],
                "outbounds": [{"type": "direct", "tag": "direct"}], "route": {"final": "direct"}}
    inbound = {
        "type": "hysteria2",
        "tag": settings["tag"],
        "listen": settings.get("listen") or "::",
        "listen_port": settings["listen_port"],
        "users": [
            {"name": item["name"], "password": item["password"]}
            for item in users
        ],
        "tls": {
            "enabled": True,
            "certificate_path": settings["certificate_path"],
            "key_path": settings["key_path"],
            "alpn": settings.get("alpn") or ["h3"],
        },
    }
    for key in ("up_mbps", "down_mbps"):
        if settings.get(key):
            inbound[key] = settings[key]
    if settings.get("ignore_client_bandwidth"):
        inbound["ignore_client_bandwidth"] = True
    if settings.get("obfs_type"):
        inbound["obfs"] = {
            "type": settings["obfs_type"],
            "password": settings["obfs_password"],
        }
    if settings.get("masquerade"):
        inbound["masquerade"] = settings["masquerade"]
    return {
        "log": {"level": "info", "timestamp": True},
        "inbounds": [inbound],
        "outbounds": [{"type": "direct", "tag": "direct"}],
        "route": {"final": "direct"},
    }


def settings_to_subscription_inbound(settings: Mapping) -> dict:
    """Expose the separate server as virtual metadata to users/hosts/subscriptions."""
    return {
        "tag": settings["tag"],
        "protocol": "hysteria",
        "network": "hysteria",
        "port": settings["listen_port"],
        "listen": settings.get("listen") or "::",
        "tls": "tls",
        "hysteria_version": 2,
        # The generic subscription renderer indexes these metadata keys
        # directly for every protocol. Keep the virtual sing-box inbound
        # shape compatible with metadata produced by XRayConfig.
        "sni": [],
        "host": [],
        "path": "",
        "header_type": "",
        "fp": "",
        "pbk": "",
        "sid": "",
        "sids": [],
        "alpn": settings.get("alpn") or ["h3"],
        "obfs": settings.get("obfs_type") or "",
        "obfs_password": settings.get("obfs_password") or "",
        "allowinsecure": False,
    }


def install_virtual_hysteria_inbound(config, settings: Mapping) -> None:
    """Replace legacy Hysteria metadata without adding it to Xray's JSON."""
    old_tags = {
        item.get("tag") for item in config.inbounds
        if item.get("protocol") == "hysteria"
    }
    config.inbounds[:] = [item for item in config.inbounds if item.get("protocol") != "hysteria"]
    for tag in old_tags:
        config.inbounds_by_tag.pop(tag, None)
    config.inbounds_by_protocol.pop("hysteria", None)
    if not settings.get("enabled", True):
        return
    inbound = settings_to_subscription_inbound(settings)
    config.inbounds.append(inbound)
    config.inbounds_by_tag[inbound["tag"]] = inbound
    config.inbounds_by_protocol["hysteria"] = [inbound]
