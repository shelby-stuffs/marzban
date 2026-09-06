"""Native Hysteria 2 client profile, independent of app/database startup.

Xray separates endpoint, transport auth, TLS and UDP obfuscation. Other
clients serialize them differently; all exporters must use this profile.
Server/host obfs metadata is authoritative. Per-user obfs is retained only
as a legacy fallback when neither canonical metadata key is present.
This module does not edit server configuration or migrate stored users.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from ipaddress import ip_address
import json
from random import choice
from typing import Mapping
from urllib.parse import quote, urlencode


def _text(value: object, name: str, *, required: bool = False) -> str:
    if value is None and not required:
        return ""
    if not isinstance(value, str) or (required and not value):
        raise ValueError(f"Hysteria2 {name} must be {'a non-empty' if required else 'a'} string")
    return value


def _boolean(value: object) -> bool:
    if value is None or value == "":
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("true", "1"):
            return True
        if normalized in ("false", "0"):
            return False
    raise ValueError("Hysteria2 allowInsecure must be a boolean")


def _alpn(value: object) -> tuple[str, ...]:
    if value is None or value == "":
        return ()
    parts = value.split(",") if isinstance(value, str) else value
    if not isinstance(parts, (list, tuple)) or any(not isinstance(p, str) for p in parts):
        raise ValueError("Hysteria2 ALPN must be a string or a list of strings")
    return tuple(dict.fromkeys(p.strip() for p in parts if p.strip()))


def _port(value: object) -> int:
    # Preserve the panel's existing comma-separated port-pool behavior.
    # This selects one endpoint, not native Hysteria port hopping.
    parts = value.split(",") if isinstance(value, str) else [value]
    ports = []
    for item in parts:
        if isinstance(item, bool):
            raise ValueError("Hysteria2 port must be between 1 and 65535")
        if isinstance(item, str):
            item = item.strip()
            if not item.isascii() or not item.isdecimal():
                raise ValueError("Hysteria2 port must contain integer port numbers")
            item = int(item)
        if not isinstance(item, int) or not 1 <= item <= 65535:
            raise ValueError("Hysteria2 port must be between 1 and 65535")
        ports.append(item)
    if not ports:
        raise ValueError("Hysteria2 port is required")
    return choice(ports)


def _address(value: object) -> str:
    address = _text(value, "address", required=True).strip()
    if address.startswith("[") and address.endswith("]"):
        address = address[1:-1]
    if not address or any(c.isspace() for c in address) or any(c in address for c in "/?#@[]"):
        raise ValueError("Hysteria2 address must be a hostname or an IP address, without a URL scheme")
    if ":" in address:
        try:
            if ip_address(address).version != 6:
                raise ValueError
        except ValueError:
            raise ValueError("Hysteria2 colon-containing addresses must be IPv6 literals") from None
    return address


@dataclass(frozen=True)
class Hysteria2Client:
    address: str
    port: int
    auth: str = field(repr=False)
    sni: str = ""
    alpn: tuple[str, ...] = ()
    insecure: bool = False
    obfs: str = ""
    obfs_password: str = field(default="", repr=False)

    @classmethod
    def from_mapping(cls, address: str, inbound: Mapping, settings: Mapping) -> Hysteria2Client:
        if inbound.get("protocol", "hysteria") != "hysteria":
            raise ValueError("Hysteria2 profile requires protocol=hysteria")
        if inbound.get("network", "hysteria") != "hysteria":
            raise ValueError("Native Hysteria2 requires the hysteria transport")
        if inbound.get("tls", "tls") != "tls":
            raise ValueError("Native Hysteria2 requires TLS; none/REALITY are not supported")
        version = inbound.get("hysteria_version", 2)
        if isinstance(version, bool) or version not in (2, "2"):
            raise ValueError("Only Hysteria version 2 is supported")

        # Compatibility: user-level values are an overlay, not a replacement.
        # This matters for existing installations where every user stores the
        # effective Salamander password while inheriting the mode from inbound.
        user_obfs = _text(settings.get("obfs"), "user obfs").strip().lower()
        inbound_obfs = _text(inbound.get("obfs"), "inbound obfs").strip().lower()
        if user_obfs == "none":
            obfs = ""
            obfs_password = ""
        else:
            obfs = user_obfs or inbound_obfs
            if obfs == "none":
                obfs = ""
            user_password = _text(settings.get("obfs_password"), "user obfs password")
            inbound_password = _text(inbound.get("obfs_password"), "inbound obfs password")
            obfs_password = (user_password or inbound_password) if obfs else ""
        if obfs not in ("", "salamander"):
            raise ValueError("Hysteria2 subscriptions support only Salamander obfuscation")
        if obfs and not obfs_password:
            raise ValueError("Hysteria2 Salamander requires an obfuscation password")

        return cls(
            address=_address(address), port=_port(inbound.get("port")),
            auth=_text(settings.get("auth"), "auth", required=True),
            sni=_text(inbound.get("sni"), "SNI"), alpn=_alpn(inbound.get("alpn")),
            insecure=_boolean(inbound.get("ais")), obfs=obfs, obfs_password=obfs_password,
        )

    def finalmask(self) -> dict:
        return {"udp": [{"type": self.obfs, "settings": {"password": self.obfs_password}}]} if self.obfs else {}

    def share_link(self, remark: str) -> str:
        query = {}
        if self.sni:
            query["sni"] = self.sni
        if self.alpn:
            query["alpn"] = ",".join(self.alpn)
        if self.insecure:
            query["insecure"] = "1"
        if self.obfs:
            query["obfs"] = self.obfs
            query["obfs-password"] = self.obfs_password
            query["fm"] = json.dumps(self.finalmask(), separators=(",", ":"))
        host = f"[{self.address}]" if ":" in self.address else self.address
        suffix = "?" + urlencode(query) if query else ""
        # Encode ':' too: auth is one opaque credential, not URI user:password.
        return f"hysteria2://{quote(self.auth, safe='')}@{host}:{self.port}{suffix}#{quote(remark, safe='')}"

    def xray(self, transport_template: Mapping | None = None) -> dict:
        transport = deepcopy(dict(transport_template or {}))
        # Old templates may contain fields which belong in finalmask instead.
        for key in ("obfs", "obfsPassword", "obfs-password"):
            transport.pop(key, None)
        transport.update(version=2, auth=self.auth)
        tls = {"serverName": self.sni, "allowInsecure": self.insecure, "show": False}
        if self.alpn:
            tls["alpn"] = list(self.alpn)
        stream = {"method": "hysteria", "security": "tls", "hysteriaSettings": transport, "tlsSettings": tls}
        if self.obfs:
            stream["finalmask"] = self.finalmask()
        return {
            "tag": "proxy", "protocol": "hysteria",
            "settings": {"version": 2, "address": self.address, "port": self.port},
            "streamSettings": stream,
        }

    def singbox(self, remark: str) -> dict:
        tls = {"enabled": True, "server_name": self.sni}
        if self.alpn:
            tls["alpn"] = list(self.alpn)
        if self.insecure:
            tls["insecure"] = True
        node = {"type": "hysteria2", "tag": remark, "server": self.address,
                "server_port": self.port, "password": self.auth, "tls": tls}
        if self.obfs:
            node["obfs"] = {"type": self.obfs, "password": self.obfs_password}
        return node

    def clash(self, remark: str) -> dict:
        node = {"name": remark, "type": "hysteria2", "server": self.address,
                "port": self.port, "password": self.auth}
        if self.sni:
            node["sni"] = self.sni
        if self.alpn:
            node["alpn"] = list(self.alpn)
        if self.insecure:
            node["skip-cert-verify"] = True
        if self.obfs:
            node.update({"obfs": self.obfs, "obfs-password": self.obfs_password})
        return node
