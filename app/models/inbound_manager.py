"""Pydantic models for dynamic inbound management."""

from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class InboundCreate(BaseModel):
    """A new inbound to append to the Xray config, 3x-ui style."""

    tag: str = Field(max_length=256, description="Unique inbound tag")
    protocol: str = Field(max_length=64, description="vmess, vless, trojan, shadowsocks, dokodemo-door, socks, http, wireguard")
    listen: Optional[str] = Field(default=None, max_length=256, description="Listen address, e.g. 0.0.0.0")
    port: Optional[int] = Field(default=None, ge=1, le=65535, description="Listen port")
    settings: Optional[Dict[str, Any]] = Field(default=None, description="Protocol-specific settings (clients, decryption, etc.)")
    streamSettings: Optional[Dict[str, Any]] = Field(default=None, description="Transport settings (network, security, tls/reality, ws, grpc, ...)")
    sniffing: Optional[Dict[str, Any]] = Field(default=None, description="Sniffing settings (enabled, destOverride)")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "tag": "VLESS_WS_INBOUND",
            "protocol": "vless",
            "listen": "0.0.0.0",
            "port": 443,
            "settings": {"clients": [], "decryption": "none"},
            "streamSettings": {
                "network": "ws",
                "security": "none",
                "wsSettings": {"path": "/ws"},
            },
            "sniffing": {"enabled": True, "destOverride": ["http", "tls"]},
        }
    })


class InboundModify(BaseModel):
    """Partial update of an existing inbound. Tag is immutable."""

    protocol: Optional[str] = Field(default=None, max_length=64)
    listen: Optional[str] = Field(default=None, max_length=256)
    port: Optional[int] = Field(default=None, ge=1, le=65535)
    settings: Optional[Dict[str, Any]] = None
    streamSettings: Optional[Dict[str, Any]] = None
    sniffing: Optional[Dict[str, Any]] = None
