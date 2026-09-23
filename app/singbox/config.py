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
    return strip_protocols_from_xray(config, {"hysteria"})


def strip_protocols_from_xray(config: Mapping, protocols: set[str]) -> dict:
    """Return an Xray runtime config without protocols owned by sing-box."""
    result = deepcopy(dict(config))
    tags = {
        inbound.get("tag")
        for inbound in result.get("inbounds", [])
        if isinstance(inbound, Mapping)
        and inbound.get("protocol") in protocols
        and isinstance(inbound.get("tag"), str)
    }
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


def _split_host_port(value: str, default_port: int = 443) -> tuple[str, int]:
    if not isinstance(value, str) or not value:
        return "", default_port
    if value.startswith("[") and "]" in value:
        host, _, port = value[1:].partition("]")
        return host, int(port.lstrip(":") or default_port)
    host, separator, port = value.rpartition(":")
    if separator and port.isdigit():
        return host, int(port)
    return value, default_port


def _vless_transport(stream: Mapping) -> dict | None:
    network = stream.get("network") or "tcp"
    if network in ("tcp", "raw"):
        return None
    if network in ("ws", "websocket"):
        settings = stream.get("wsSettings") or {}
        transport = {"type": "ws"}
        if settings.get("path"):
            transport["path"] = settings["path"]
        headers = settings.get("headers")
        if isinstance(headers, Mapping) and headers:
            transport["headers"] = deepcopy(dict(headers))
        return transport
    if network in ("grpc", "gun"):
        settings = stream.get("grpcSettings") or {}
        transport = {"type": "grpc"}
        if settings.get("serviceName"):
            transport["service_name"] = settings["serviceName"]
        if settings.get("multiMode") is True:
            transport["multi_mode"] = True
        return transport
    if network in ("xhttp", "splithttp"):
        settings = stream.get("xhttpSettings") or stream.get("splithttpSettings") or {}
        transport = {"type": "xhttp"}
        if settings.get("path"):
            transport["path"] = settings["path"]
        if settings.get("host"):
            transport["host"] = settings["host"]
        return transport
    raise ValueError(f"Unsupported VLESS transport for sing-box migration: {network}")


def _vless_tls(stream: Mapping) -> dict | None:
    security = stream.get("security") or "none"
    if security == "none":
        return None
    settings = stream.get("tlsSettings") or {}
    if security == "tls":
        tls = {"enabled": True}
        certificates = settings.get("certificates") or []
        if certificates and isinstance(certificates[0], Mapping):
            certificate = certificates[0]
            if certificate.get("certificateFile") and certificate.get("keyFile"):
                tls["certificate_path"] = certificate["certificateFile"]
                tls["key_path"] = certificate["keyFile"]
            elif certificate.get("certificate") and certificate.get("key"):
                tls["certificate"] = certificate["certificate"]
                tls["key"] = certificate["key"]
        if settings.get("alpn"):
            tls["alpn"] = settings["alpn"]
        return tls
    if security == "reality":
        reality = settings.get("realitySettings") or {}
        tls = {"enabled": True, "reality": {"enabled": True}}
        if reality.get("privateKey"):
            tls["reality"]["private_key"] = reality["privateKey"]
        if reality.get("shortIds"):
            tls["reality"]["short_id"] = reality["shortIds"][0]
        dest_host, dest_port = _split_host_port(reality.get("dest", ""))
        if dest_host:
            tls["reality"]["handshake"] = {
                "server": dest_host,
                "server_port": dest_port,
            }
        return tls
    raise ValueError(f"Unsupported VLESS security for sing-box migration: {security}")


def convert_vless_inbounds_from_xray(config: Mapping, existing_tags: set[str] | None = None) -> list[dict]:
    """Convert legacy Xray VLESS inbounds to native sing-box inbounds.

    The conversion intentionally keeps tags, ports and UUIDs stable. Existing
    advanced sing-box tags win, so an operator can replace one migrated inbound
    with a hand-tuned extended configuration without creating duplicates.
    """
    existing_tags = existing_tags or set()
    converted = []
    for source in config.get("inbounds", []):
        if not isinstance(source, Mapping) or source.get("protocol") != "vless":
            continue
        tag = source.get("tag")
        port = source.get("port")
        if not isinstance(tag, str) or not tag or tag in existing_tags:
            continue
        if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
            continue
        stream = source.get("streamSettings") or {}
        inbound = {
            "type": "vless",
            "tag": tag,
            "listen": source.get("listen") or "::",
            "listen_port": port,
            "users": [],
        }
        for client in (source.get("settings") or {}).get("clients", []):
            if not isinstance(client, Mapping) or not client.get("id"):
                continue
            user = {"uuid": client["id"]}
            if client.get("email"):
                user["name"] = client["email"]
            if client.get("flow"):
                user["flow"] = client["flow"]
            inbound["users"].append(user)
        transport = _vless_transport(stream)
        if transport:
            inbound["transport"] = transport
        tls = _vless_tls(stream)
        if tls:
            inbound["tls"] = tls
        converted.append(inbound)
    return converted


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


def merge_advanced_config(managed: Mapping, advanced: Mapping | None) -> dict:
    """Overlay editable top-level sections, including user-managed inbounds.

    When ``inbounds`` is omitted, the generated Hysteria 2 inbound remains
    active for backwards compatibility.  When it is present, even as an empty
    list, it becomes the source of truth and replaces the generated inbound.
    """
    result = deepcopy(dict(managed))
    for key, value in (advanced or {}).items():
        result[key] = deepcopy(value)
    return result


def subscription_host_from_settings(settings: Mapping) -> dict | None:
    """Build one authoritative public endpoint for all subscription formats."""
    if not settings.get("subscription_enabled", True):
        return None
    address = (settings.get("subscription_address") or "").strip()
    if not address:
        return None
    sni = (settings.get("subscription_sni") or "").strip()
    alpn = settings.get("alpn") or ["h3"]
    return {
        "remark": settings.get("subscription_remark") or "🚀 Marz ({USERNAME}) [Hysteria 2]",
        "address": [address],
        "port": settings.get("subscription_port") or settings["listen_port"],
        "path": None,
        "sni": [sni] if sni else [],
        "host": [],
        "tls": None,
        "alpn": ",".join(alpn) if isinstance(alpn, (list, tuple)) else alpn,
        "fingerprint": "",
        "allowinsecure": bool(settings.get("subscription_insecure", False)),
        "mux_enable": False,
        "fragment_setting": None,
        "noise_setting": None,
        "random_user_agent": False,
        "use_sni_as_host": False,
        # Empty means inherit the server-wide values from virtual inbound metadata.
        "obfs": "",
        "obfs_password": "",
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
        "subscription_host": subscription_host_from_settings(settings),
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
