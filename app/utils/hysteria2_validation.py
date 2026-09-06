"""Save-time guards for the panel's native Hysteria2 support.

Pure functions: no writes, no key generation, no implicit config migration.
Xray's binary validation remains mandatory after these schema checks.
"""
from collections.abc import Mapping
from string import Formatter


def _object(value, location):
    if not isinstance(value, Mapping):
        raise ValueError(f"{location} must be an object")
    return value


def _version(value, location):
    if isinstance(value, bool) or not isinstance(value, int) or value != 2:
        raise ValueError(f"{location} must be integer 2")


def validate_hysteria2_config(config: dict) -> None:
    for index, inbound in enumerate(config.get("inbounds", [])):
        if not isinstance(inbound, dict) or inbound.get("protocol") != "hysteria":
            continue
        location = f"Hysteria2 inbound #{index + 1}"
        stream = _object(inbound.get("streamSettings"), f"{location} streamSettings")
        if (stream.get("method") or stream.get("network")) != "hysteria":
            raise ValueError(f"{location} requires the hysteria transport")
        if stream.get("security") != "tls":
            raise ValueError(f"{location} requires TLS")
        _object(stream.get("tlsSettings"), f"{location} tlsSettings")
        settings = _object(inbound.get("settings"), f"{location} settings")
        _version(settings.get("version"), f"{location} settings.version")
        transport = _object(stream.get("hysteriaSettings"), f"{location} hysteriaSettings")
        _version(transport.get("version"), f"{location} hysteriaSettings.version")
        port = inbound.get("port")
        if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
            raise ValueError(f"{location} requires one integer UDP port between 1 and 65535")
        if any(transport.get(key) not in (None, "") for key in ("obfs", "obfsPassword", "obfs-password")):
            raise ValueError(f"{location}: move legacy obfs settings explicitly to finalmask.udp")
        if "auth" in transport and (not isinstance(transport["auth"], str) or not transport["auth"]):
            raise ValueError(f"{location} transport auth must be a non-empty string when supplied")
        # Empty clients are valid before the panel inserts managed DB users.
        if settings.get("clients") and settings.get("users"):
            raise ValueError(f"{location}: do not mix non-empty clients and users arrays")
        for key in ("clients", "users"):
            if key not in settings:
                continue
            users = settings[key]
            if not isinstance(users, list):
                raise ValueError(f"{location} {key} must be an array")
            seen = set()
            for user in users:
                if not isinstance(user, dict) or not isinstance(user.get("auth"), str) or not user["auth"]:
                    raise ValueError(f"{location} {key} entries require non-empty auth")
                if user["auth"] in seen:
                    raise ValueError(f"{location} {key} contains duplicate auth values")
                seen.add(user["auth"])
        if "finalmask" not in stream:
            continue
        mask = _object(stream["finalmask"], f"{location} finalmask")
        udp = mask.get("udp", [])
        if not isinstance(udp, list):
            raise ValueError(f"{location} finalmask.udp must be an array")
        # Reject lossy client export rather than flattening an advanced chain.
        if len(udp) > 1:
            raise ValueError(f"{location}: multiple UDP masks cannot be exported by this panel yet")
        for item in udp:
            item = _object(item, f"{location} UDP mask")
            if item.get("type") != "salamander":
                raise ValueError(f"{location}: only plain Salamander can be exported by this panel")
            options = _object(item.get("settings"), f"{location} Salamander settings")
            if set(options) - {"password"}:
                raise ValueError(f"{location}: extended Salamander/Gecko settings cannot be exported yet")
            if not isinstance(options.get("password"), str) or not options["password"]:
                raise ValueError(f"{location} Salamander requires a non-empty password")


def _value(value):
    return getattr(value, "value", value)


def resolve_hysteria2_host(inbound: Mapping, host: Mapping) -> dict:
    """Match existing empty-as-inherit host semantics, without truthy bool bugs."""
    security = _value(host.get("tls", host.get("security")))
    if security in (None, "inbound_default"):
        security = inbound.get("tls", "tls")
    insecure = host.get("allowinsecure")
    if insecure is None:
        insecure = inbound.get("allowinsecure", inbound.get("ais", False))
    return {
        "tls": security,
        "port": host.get("port") if host.get("port") is not None else inbound.get("port"),
        "alpn": _value(host.get("alpn")) or None,
        "ais": insecure,
        "obfs": host.get("obfs") or inbound.get("obfs", ""),
        "obfs_password": host.get("obfs_password") or inbound.get("obfs_password", ""),
    }


def validate_hysteria2_hosts(modified_hosts: Mapping, inbounds: Mapping, *, client_type) -> None:
    """Preflight the whole request before any per-tag CRUD commit can happen."""
    for tag, hosts in modified_hosts.items():
        inbound = inbounds.get(tag)
        if not inbound or inbound.get("protocol") != "hysteria":
            continue
        for index, value in enumerate(hosts):
            host = value.model_dump() if hasattr(value, "model_dump") else value
            if host.get("is_disabled"):
                continue
            metadata = dict(inbound)
            metadata.update(resolve_hysteria2_host(inbound, host))
            metadata["sni"] = ""  # Certificates/SNI templates are checked at runtime.
            try:
                address = host.get("address")
                if not isinstance(address, str) or not address.strip():
                    raise ValueError("address is required")
                for candidate in address.split(","):
                    candidate = candidate.strip()
                    if "{" in candidate or "}" in candidate:
                        # Check template syntax, but do not pretend runtime variables
                        # can be resolved reliably at save time.
                        list(Formatter().parse(candidate))
                        candidate = "validation.example"
                    client_type.from_mapping(candidate, metadata, {"auth": "validation-only"})
            except ValueError as exc:
                raise ValueError(f"Hysteria2 host #{index + 1} for inbound {tag}: {exc}") from None


def validate_hysteria2_user_proxies(proxies):
    """Used only on user write models; historical response objects stay readable."""
    for protocol, settings in (proxies or {}).items():
        if _value(protocol) != "hysteria":
            continue
        auth = settings.get("auth") if isinstance(settings, Mapping) else getattr(settings, "auth", None)
        if not isinstance(auth, str) or not auth:
            raise ValueError("Hysteria2 auth must be a non-empty string")
    return proxies
