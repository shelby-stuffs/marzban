from __future__ import annotations

import json
import re
from copy import deepcopy
from ipaddress import ip_interface
from pathlib import PosixPath

import commentjson

from app.utils.crypto import get_wireguard_public_key, validate_wireguard_key

_WIREGUARD_INTERFACE_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class WireGuardConfig(dict):
    """Validated WireGuard interface configuration.

    The shape intentionally mirrors PasarGuard's WireGuard core configuration
    while remaining independent of its newer core registry architecture.
    """

    def __init__(self, config: dict | str | PosixPath | None = None, *, skip_validation: bool = False):
        if config is None:
            config = {}
        elif isinstance(config, PosixPath):
            config = commentjson.loads(config.read_text())
        elif isinstance(config, str):
            config = commentjson.loads(config)
        elif isinstance(config, dict):
            config = deepcopy(config)
        else:
            raise TypeError("WireGuard config must be a dict, JSON string, or PosixPath")

        super().__init__(config)
        self._inbounds: list[str] = []
        self._inbounds_by_tag: dict[str, dict] = {}

        if not skip_validation:
            self._validate()
            self._resolve_inbounds()

    def _validate(self):
        interface_name = str(self.get("interface_name") or "").strip()
        if not interface_name:
            raise ValueError("interface_name is required")
        if not _WIREGUARD_INTERFACE_NAME_RE.fullmatch(interface_name):
            raise ValueError(
                "interface_name must start with a letter or digit and contain only letters, digits, '_', '.', or '-'"
            )
        self["interface_name"] = interface_name

        private_key = str(self.get("private_key") or "").strip()
        if not private_key:
            raise ValueError("private_key is required")
        self["private_key"] = validate_wireguard_key(private_key, "private_key")
        self["public_key"] = get_wireguard_public_key(self["private_key"])

        pre_shared_key = str(self.get("pre_shared_key") or "").strip()
        if pre_shared_key:
            self["pre_shared_key"] = validate_wireguard_key(pre_shared_key, "pre_shared_key")
        else:
            self.pop("pre_shared_key", None)

        listen_port = self.get("listen_port")
        if not isinstance(listen_port, int) or isinstance(listen_port, bool) or not 1 <= listen_port <= 65535:
            raise ValueError("listen_port must be an integer between 1 and 65535")

        addresses = self.get("address")
        if not isinstance(addresses, list) or not addresses:
            raise TypeError("address must be a non-empty list")

        normalized_addresses = []
        for cidr in addresses:
            if not isinstance(cidr, str) or not cidr.strip():
                raise ValueError("address entries must be valid CIDR strings")
            normalized_addresses.append(str(ip_interface(cidr.strip())))
        self["address"] = normalized_addresses

    def _resolve_inbounds(self):
        interface_name = self["interface_name"]
        metadata = {
            "tag": interface_name,
            "protocol": "wireguard",
            "network": "udp",
            "tls": "none",
            "interface_name": interface_name,
            "listen_port": self["listen_port"],
            "address": list(self["address"]),
            "public_key": self["public_key"],
            "private_key": self["private_key"],
            "pre_shared_key": self.get("pre_shared_key", ""),
        }
        self._inbounds = [interface_name]
        self._inbounds_by_tag = {interface_name: metadata}

    @property
    def inbounds(self) -> list[str]:
        return self._inbounds

    @property
    def inbounds_by_tag(self) -> dict[str, dict]:
        return self._inbounds_by_tag

    def to_json(self) -> dict:
        return {
            "type": "wireguard",
            "config": dict(self),
            "inbounds": list(self.inbounds),
            "inbounds_by_tag": deepcopy(self.inbounds_by_tag),
        }

    def to_str(self, **json_kwargs) -> str:
        return json.dumps(self, **json_kwargs)

    @classmethod
    def from_json(cls, data: dict) -> WireGuardConfig:
        instance = cls(config=data.get("config", {}), skip_validation=True)
        instance._inbounds = list(data.get("inbounds", []))
        instance._inbounds_by_tag = deepcopy(data.get("inbounds_by_tag", {}))
        return instance

    def copy(self):
        return deepcopy(self)
