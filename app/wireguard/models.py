from __future__ import annotations

from ipaddress import ip_interface

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.utils.crypto import (
    generate_wireguard_keypair,
    get_wireguard_public_key,
    validate_wireguard_key,
)


class WireGuardPeerSettings(BaseModel):
    """Persistent per-user WireGuard credentials and allocated addresses."""

    private_key: str | None = None
    public_key: str | None = None
    peer_ips: list[str] = Field(default_factory=list)

    model_config = ConfigDict(validate_assignment=True)

    @field_validator("private_key", mode="before")
    @classmethod
    def validate_private_key(cls, value):
        if value in (None, ""):
            return None
        return validate_wireguard_key(value, "wireguard private_key")

    @field_validator("public_key", mode="before")
    @classmethod
    def validate_public_key(cls, value):
        if value in (None, ""):
            return None
        return validate_wireguard_key(value, "wireguard public_key")

    @field_validator("peer_ips", mode="before")
    @classmethod
    def validate_peer_ips(cls, value):
        if value in (None, ""):
            return []
        if isinstance(value, str):
            value = [value]

        normalized = []
        for peer_ip in value:
            if not isinstance(peer_ip, str) or not peer_ip.strip():
                continue
            interface = ip_interface(peer_ip.strip())
            host_prefix = 32 if interface.version == 4 else 128
            canonical = f"{interface.ip}/{host_prefix}"
            if canonical not in normalized:
                normalized.append(canonical)
        return normalized

    @model_validator(mode="after")
    def synchronize_keys(self):
        if self.private_key:
            derived_public_key = get_wireguard_public_key(self.private_key)
            if self.public_key and self.public_key != derived_public_key:
                raise ValueError("wireguard public_key does not match private_key")
            self.public_key = derived_public_key
        return self

    def ensure_keypair(self) -> WireGuardPeerSettings:
        if not self.private_key:
            self.private_key, self.public_key = generate_wireguard_keypair()
        return self
