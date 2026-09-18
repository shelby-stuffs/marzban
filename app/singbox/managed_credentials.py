from __future__ import annotations

import base64
import hashlib
import hmac
import uuid


def _digest(secret: str, username: str, inbound_tag: str, purpose: str) -> bytes:
    message = f"sing-box:{purpose}:{inbound_tag}:{username}".encode("utf-8")
    return hmac.new(secret.encode("utf-8"), message, hashlib.sha256).digest()


def managed_password(secret: str, username: str, inbound_tag: str) -> str:
    """Return a stable per-user/per-inbound password without storing another secret."""
    return base64.urlsafe_b64encode(
        _digest(secret, username, inbound_tag, "password")
    ).decode("ascii").rstrip("=")


def managed_uuid(secret: str, username: str, inbound_tag: str) -> str:
    """Return a stable UUID for protocols that require one."""
    raw = bytearray(_digest(secret, username, inbound_tag, "uuid")[:16])
    raw[6] = (raw[6] & 0x0F) | 0x50
    raw[8] = (raw[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(raw)))