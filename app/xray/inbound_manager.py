"""Dynamic inbound management like 3x-ui: create, update, delete inbounds in the Xray config."""

from __future__ import annotations

from copy import deepcopy
from typing import Optional

RESERVED_TAGS = {"API_INBOUND"}

SUPPORTED_PROTOCOLS = (
    "vmess",
    "vless",
    "trojan",
    "shadowsocks",
    "dokodemo-door",
    "socks",
    "http",
    "wireguard",
)

SUPPORTED_NETWORKS = (
    "tcp",
    "ws",
    "grpc",
    "kcp",
    "httpupgrade",
    "xhttp",
    "http2",
    "quic",
)

SUPPORTED_SECURITY = (
    "none",
    "tls",
    "reality",
)


def _stream_settings(inbound: dict) -> dict:
    stream = inbound.get("streamSettings")
    return stream if isinstance(stream, dict) else {}


def _validate_payload(payload: dict, existing_inbounds: list[dict], current_tag: Optional[str] = None) -> None:
    """Validate inbound payload against the rest of the config."""
    tag = payload.get("tag")
    if not tag:
        raise ValueError("Inbound tag is required")
    if tag in RESERVED_TAGS:
        raise ValueError(f"Tag {tag} is reserved")

    protocol = payload.get("protocol")
    if protocol not in SUPPORTED_PROTOCOLS:
        raise ValueError(f"Unsupported protocol: {protocol}")

    port = payload.get("port")
    if port is not None:
        try:
            port = int(port)
        except (TypeError, ValueError):
            raise ValueError("Port must be an integer")
        if not 0 < port < 65536:
            raise ValueError("Port must be between 1 and 65535")
        payload["port"] = port

    stream = payload.get("streamSettings") or {}
    network = stream.get("network")
    if network is not None and network not in SUPPORTED_NETWORKS:
        raise ValueError(f"Unsupported network: {network}")

    security = stream.get("security")
    if security is not None and security not in SUPPORTED_SECURITY:
        raise ValueError(f"Unsupported security: {security}")

    # Reality requires serverNames and privateKey
    if security == "reality":
        reality = stream.get("realitySettings") or {}
        if not reality.get("serverNames"):
            raise ValueError("realitySettings.serverNames is required for reality")
        if not reality.get("privateKey"):
            raise ValueError("realitySettings.privateKey is required for reality")

    # TLS requires certificates or relies on hosts
    if security == "tls":
        tls = stream.get("tlsSettings") or {}
        if not tls.get("certificates") and not tls.get("serverName"):
            raise ValueError("tlsSettings.certificates or tlsSettings.serverName is required for tls")

    # Tag uniqueness
    for inbound in existing_inbounds:
        if inbound.get("tag") == tag and inbound.get("tag") != current_tag:
            raise ValueError(f"Inbound tag {tag} already exists")


def list_inbounds(config: dict, include_reserved: bool = False) -> list[dict]:
    result = []
    for inbound in config.get("inbounds", []):
        tag = inbound.get("tag", "")
        if not include_reserved and tag in RESERVED_TAGS:
            continue
        if tag == XRAY_FALLBACK_TAG:
            continue
        result.append(
            {
                "tag": tag,
                "protocol": inbound.get("protocol", ""),
                "listen": inbound.get("listen"),
                "port": inbound.get("port"),
                "settings": deepcopy(inbound.get("settings")) if isinstance(inbound.get("settings"), dict) else {},
                "streamSettings": deepcopy(_stream_settings(inbound)),
                "sniffing": deepcopy(inbound.get("sniffing")) if isinstance(inbound.get("sniffing"), dict) else {},
            }
        )
    return result


XRAY_FALLBACK_TAG = "FALLBACK_INBOUND"


def create_inbound(config: dict, payload: dict) -> dict:
    inbounds = config.get("inbounds", [])
    _validate_payload(payload, inbounds)

    inbound = {
        "tag": payload["tag"],
        "protocol": payload["protocol"],
    }
    if payload.get("listen"):
        inbound["listen"] = payload["listen"]
    if payload.get("port") is not None:
        inbound["port"] = payload["port"]
    if isinstance(payload.get("settings"), dict):
        inbound["settings"] = deepcopy(payload["settings"])
    stream = payload.get("streamSettings")
    if isinstance(stream, dict) and stream:
        inbound["streamSettings"] = deepcopy(stream)
    sniffing = payload.get("sniffing")
    if isinstance(sniffing, dict) and sniffing:
        inbound["sniffing"] = deepcopy(sniffing)

    updated = deepcopy(config)
    updated.setdefault("inbounds", [])
    updated["inbounds"].append(inbound)
    return updated


def update_inbound(config: dict, tag: str, payload: dict) -> dict:
    inbounds = config.get("inbounds", [])
    target = next((i for i in inbounds if i.get("tag") == tag), None)
    if target is None:
        raise ValueError(f"Inbound {tag} does not exist")
    if tag in RESERVED_TAGS:
        raise ValueError(f"Tag {tag} is reserved")

    merged = deepcopy(target)
    for key in ("protocol", "listen", "port", "settings", "streamSettings", "sniffing"):
        if key in payload and payload[key] is not None:
            merged[key] = deepcopy(payload[key])
    merged["tag"] = tag

    _validate_payload(merged, inbounds, current_tag=tag)

    updated = deepcopy(config)
    for index, inbound in enumerate(updated.get("inbounds", [])):
        if inbound.get("tag") == tag:
            updated["inbounds"][index] = merged
            return updated
    raise ValueError(f"Inbound {tag} does not exist")


def delete_inbound(config: dict, tag: str) -> dict:
    if tag in RESERVED_TAGS:
        raise ValueError(f"Tag {tag} is reserved")

    inbounds = config.get("inbounds", [])
    if not any(i.get("tag") == tag for i in inbounds):
        raise ValueError(f"Inbound {tag} does not exist")

    updated = deepcopy(config)
    updated["inbounds"] = [i for i in updated.get("inbounds", []) if i.get("tag") != tag]
    return updated


def generate_reality_keys() -> dict:
    """Generate an x25519 key pair for reality via the xray binary."""
    import subprocess

    from config import XRAY_EXECUTABLE_PATH

    try:
        output = subprocess.run(
            [XRAY_EXECUTABLE_PATH, "x25519"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"Failed to run xray x25519: {exc}") from exc

    private_key = None
    public_key = None
    for line in (output.stdout or "").splitlines():
        line = line.strip()
        if line.lower().startswith("private key"):
            private_key = line.split(":", 1)[1].strip()
        elif line.lower().startswith("public key"):
            public_key = line.split(":", 1)[1].strip()

    if not private_key or not public_key:
        raise RuntimeError("xray x25519 did not return keys")

    return {"private_key": private_key, "public_key": public_key}
