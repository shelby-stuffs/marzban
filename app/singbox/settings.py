from __future__ import annotations

import json
import os
import secrets
import tempfile
from pathlib import Path
from typing import Literal, Mapping

from pydantic import BaseModel, Field, field_validator, model_validator


class Hysteria2ServerSettings(BaseModel):
    enabled: bool = True
    tag: str = Field(default="HYSTERIA2", min_length=1, max_length=128)
    listen: str = Field(default="::", min_length=1)
    listen_port: int = Field(default=443, ge=1, le=65535)
    up_mbps: int | None = Field(default=None, gt=0)
    down_mbps: int | None = Field(default=None, gt=0)
    ignore_client_bandwidth: bool = False
    obfs_type: Literal["", "salamander"] = "salamander"
    obfs_password: str = Field(default_factory=lambda: secrets.token_hex(16))
    certificate_path: str = ""
    key_path: str = ""
    alpn: list[str] = Field(default_factory=lambda: ["h3"])
    masquerade: str = ""

    @field_validator("tag", "listen", "certificate_path", "key_path", "masquerade", mode="before")
    @classmethod
    def strip_strings(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("alpn", mode="before")
    @classmethod
    def normalize_alpn(cls, value):
        if isinstance(value, str):
            value = [item.strip() for item in value.split(",") if item.strip()]
        return value or ["h3"]

    @model_validator(mode="after")
    def validate_runtime_requirements(self):
        if self.enabled and (not self.certificate_path or not self.key_path):
            raise ValueError("certificate_path and key_path are required when Hysteria2 is enabled")
        if self.obfs_type == "salamander" and not self.obfs_password:
            raise ValueError("Salamander requires obfs_password")
        if self.ignore_client_bandwidth and (self.up_mbps or self.down_mbps):
            raise ValueError("ignore_client_bandwidth conflicts with up_mbps/down_mbps")
        return self


def load_settings(path: str) -> Hysteria2ServerSettings | None:
    file = Path(path)
    if not file.exists():
        return None
    return Hysteria2ServerSettings.model_validate_json(file.read_text(encoding="utf-8"))


def save_settings(path: str, settings: Hysteria2ServerSettings) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(
        prefix=".marzban-hysteria2-settings-", suffix=".json.tmp", dir=destination.parent
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


def generate_settings(
    xray_config: Mapping,
    *,
    fallback_certificate_path: str = "",
    fallback_key_path: str = "",
) -> tuple[dict, str]:
    """Generate editable settings from one legacy inbound or safe defaults."""
    for inbound in xray_config.get("inbounds", []):
        if inbound.get("protocol") != "hysteria":
            continue
        stream = inbound.get("streamSettings") or {}
        tls = stream.get("tlsSettings") or {}
        certs = tls.get("certificates") or []
        cert = certs[0] if certs and isinstance(certs[0], Mapping) else {}
        finalmask = stream.get("finalmask") or {}
        obfs_type, obfs_password = "", ""
        for item in finalmask.get("udp", []) if isinstance(finalmask, Mapping) else []:
            if isinstance(item, Mapping) and item.get("type") == "salamander":
                obfs_type = "salamander"
                obfs_password = (item.get("settings") or {}).get("password", "")
                break
        legacy = stream.get("hysteriaSettings") or {}
        if not obfs_type and legacy.get("obfs") == "salamander":
            obfs_type, obfs_password = "salamander", legacy.get("obfsPassword", "")
        protocol = inbound.get("settings") or {}
        generated = {
            "enabled": True,
            "tag": inbound.get("tag") or "HYSTERIA2",
            "listen": inbound.get("listen") or "::",
            "listen_port": inbound.get("port") or 443,
            "up_mbps": protocol.get("up_mbps"),
            "down_mbps": protocol.get("down_mbps"),
            "ignore_client_bandwidth": False,
            "obfs_type": obfs_type or "salamander",
            "obfs_password": obfs_password or secrets.token_hex(16),
            "certificate_path": cert.get("certificateFile") or fallback_certificate_path,
            "key_path": cert.get("keyFile") or fallback_key_path,
            "alpn": tls.get("alpn") or ["h3"],
            "masquerade": protocol.get("masquerade") or "",
        }
        return generated, "legacy_xray_inbound"
    return {
        "enabled": True,
        "tag": "HYSTERIA2",
        "listen": "::",
        "listen_port": 443,
        "up_mbps": None,
        "down_mbps": None,
        "ignore_client_bandwidth": False,
        "obfs_type": "salamander",
        "obfs_password": secrets.token_hex(16),
        "certificate_path": fallback_certificate_path,
        "key_path": fallback_key_path,
        "alpn": ["h3"],
        "masquerade": "",
    }, "defaults"
