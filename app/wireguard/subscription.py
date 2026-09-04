from __future__ import annotations

import io
import re
import zipfile
from collections.abc import Iterable

from .config import WireGuardConfig
from .models import WireGuardPeerSettings

_SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _endpoint(address: str, port: int) -> str:
    address = address.strip()
    if ":" in address and not address.startswith("["):
        address = f"[{address}]"
    return f"{address}:{port}"


def _csv(values: Iterable[str]) -> str:
    return ", ".join(str(value).strip() for value in values if str(value).strip())


def render_wireguard_client_config(
    *,
    peer: WireGuardPeerSettings,
    server: WireGuardConfig,
    endpoint_address: str,
    endpoint_port: int | None = None,
    allowed_ips: Iterable[str] = ("0.0.0.0/0", "::/0"),
    dns: Iterable[str] = (),
    mtu: int | None = None,
    persistent_keepalive: int | None = 25,
    reserved: Iterable[int] = (),
) -> str:
    """Render a client configuration accepted by wg-quick and modern clients."""
    peer.ensure_keypair()
    if not peer.peer_ips:
        raise ValueError("WireGuard peer has no allocated addresses")
    if not endpoint_address.strip():
        raise ValueError("WireGuard endpoint address is required")

    port = endpoint_port if endpoint_port is not None else server["listen_port"]
    if not isinstance(port, int) or isinstance(port, bool) or not 1 <= port <= 65535:
        raise ValueError("WireGuard endpoint port must be between 1 and 65535")

    interface = [
        "[Interface]",
        f"PrivateKey = {peer.private_key}",
        f"Address = {_csv(peer.peer_ips)}",
    ]
    if dns_value := _csv(dns):
        interface.append(f"DNS = {dns_value}")
    if mtu is not None:
        if not isinstance(mtu, int) or isinstance(mtu, bool) or mtu <= 0:
            raise ValueError("WireGuard MTU must be a positive integer")
        interface.append(f"MTU = {mtu}")
    if reserved_value := _csv(str(value) for value in reserved):
        interface.append(f"Reserved = {reserved_value}")

    peer_section = [
        "[Peer]",
        f"PublicKey = {server['public_key']}",
        f"AllowedIPs = {_csv(allowed_ips)}",
        f"Endpoint = {_endpoint(endpoint_address, port)}",
    ]
    if pre_shared_key := server.get("pre_shared_key"):
        peer_section.append(f"PresharedKey = {pre_shared_key}")
    if persistent_keepalive is not None:
        if not isinstance(persistent_keepalive, int) or isinstance(persistent_keepalive, bool):
            raise ValueError("WireGuard persistent keepalive must be an integer")
        if not 0 <= persistent_keepalive <= 65535:
            raise ValueError("WireGuard persistent keepalive must be between 0 and 65535")
        if persistent_keepalive:
            peer_section.append(f"PersistentKeepalive = {persistent_keepalive}")

    return "\n".join((*interface, "", *peer_section, ""))


class WireGuardSubscription:
    """Collect WireGuard client configurations and render a ZIP subscription."""

    def __init__(self):
        self.configs: list[tuple[str, str]] = []

    def add(self, remark: str, **config_kwargs) -> str:
        content = render_wireguard_client_config(**config_kwargs)
        filename = _SAFE_FILENAME_RE.sub("_", remark.strip()).strip("._") or "wireguard"
        filename = f"{filename}.conf"

        existing = {name for name, _ in self.configs}
        if filename in existing:
            stem = filename[:-5]
            index = 2
            while f"{stem}_{index}.conf" in existing:
                index += 1
            filename = f"{stem}_{index}.conf"

        self.configs.append((filename, content))
        return content

    def render(self) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for filename, content in self.configs:
                archive.writestr(filename, content)
        return buffer.getvalue()
