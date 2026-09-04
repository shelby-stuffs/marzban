from __future__ import annotations

import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Callable, Iterable

from .config import WireGuardConfig
from .models import WireGuardPeerSettings

_INTERFACE_RE = re.compile(r"^[A-Za-z0-9_=+.-]{1,15}$")


class WireGuardRuntimeError(RuntimeError):
    pass


def render_wireguard_server_config(
    server: WireGuardConfig,
    peers: Iterable[WireGuardPeerSettings],
) -> str:
    lines = [
        "[Interface]",
        f"PrivateKey = {server['private_key']}",
        f"Address = {', '.join(server['address'])}",
        f"ListenPort = {server['listen_port']}",
    ]

    public_keys = set()
    for peer in peers:
        peer.ensure_keypair()
        if not peer.peer_ips:
            continue
        if peer.public_key in public_keys:
            raise ValueError("Duplicate WireGuard peer public key")
        public_keys.add(peer.public_key)

        lines.extend(["", "[Peer]", f"PublicKey = {peer.public_key}"])
        if peer.pre_shared_key:
            lines.append(f"PresharedKey = {peer.pre_shared_key}")
        lines.append(f"AllowedIPs = {', '.join(peer.peer_ips)}")

    return "\n".join(lines) + "\n"


def parse_wireguard_dump(output: str) -> list[dict]:
    lines = [line for line in output.splitlines() if line]
    if not lines:
        return []

    peers = []
    for line in lines[1:]:
        fields = line.split("\t")
        if len(fields) < 8:
            continue
        peers.append(
            {
                "public_key": fields[0],
                "endpoint": None if fields[2] == "(none)" else fields[2],
                "allowed_ips": [] if fields[3] == "(none)" else fields[3].split(","),
                "latest_handshake": int(fields[4]),
                "transfer_rx": int(fields[5]),
                "transfer_tx": int(fields[6]),
                "persistent_keepalive": int(fields[7]),
            }
        )
    return peers


class WireGuardRuntime:
    def __init__(
        self,
        *,
        config_dir: str | Path = "/etc/wireguard",
        runner: Callable = subprocess.run,
        timeout: float = 10,
    ):
        self.config_dir = Path(config_dir)
        self.runner = runner
        self.timeout = timeout

    @staticmethod
    def validate_interface_name(interface_name: str) -> str:
        if not _INTERFACE_RE.fullmatch(interface_name):
            raise ValueError("Invalid WireGuard interface name")
        return interface_name

    def config_path(self, interface_name: str) -> Path:
        interface_name = self.validate_interface_name(interface_name)
        return self.config_dir / f"{interface_name}.conf"

    def desired_state_path(self, interface_name: str) -> Path:
        interface_name = self.validate_interface_name(interface_name)
        return self.config_dir / f".{interface_name}.marzban-enabled"

    def _run(self, args: list[str], *, input_text: str | None = None):
        try:
            return self.runner(
                args,
                input=input_text,
                text=True,
                capture_output=True,
                check=True,
                timeout=self.timeout,
            )
        except FileNotFoundError as exc:
            raise WireGuardRuntimeError(f"WireGuard command is not installed: {args[0]}") from exc
        except subprocess.TimeoutExpired as exc:
            raise WireGuardRuntimeError(f"WireGuard command timed out: {args[0]}") from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or exc.stdout or str(exc)).strip()
            raise WireGuardRuntimeError(detail) from exc

    def write_config(self, interface_name: str, content: str) -> Path:
        path = self.config_path(interface_name)
        self.config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        handle = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.config_dir,
            prefix=f".{interface_name}.",
            suffix=".tmp",
            delete=False,
        )
        temporary_path = Path(handle.name)
        try:
            with handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.chmod(temporary_path, 0o600)
            os.replace(temporary_path, path)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()
        return path

    def set_desired_state(self, interface_name: str, enabled: bool) -> None:
        marker = self.desired_state_path(interface_name)
        if enabled:
            self.config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            marker.touch(mode=0o600, exist_ok=True)
            os.chmod(marker, 0o600)
        elif marker.exists():
            marker.unlink()

    def should_restore(self, interface_name: str) -> bool:
        return self.desired_state_path(interface_name).exists()

    def active_interfaces(self) -> list[str]:
        result = self._run(["wg", "show", "interfaces"])
        return result.stdout.split()

    def is_active(self, interface_name: str) -> bool:
        interface_name = self.validate_interface_name(interface_name)
        return interface_name in self.active_interfaces()

    def apply(self, server: WireGuardConfig, peers: Iterable[WireGuardPeerSettings]) -> dict:
        interface_name = self.validate_interface_name(server["interface_name"])
        content = render_wireguard_server_config(server, peers)
        path = self.write_config(interface_name, content)

        if self.is_active(interface_name):
            stripped = self._run(["wg-quick", "strip", str(path)])
            self._run(["wg", "syncconf", interface_name, "/dev/stdin"], input_text=stripped.stdout)
            action = "synchronized"
        else:
            self._run(["wg-quick", "up", str(path)])
            action = "started"

        self.set_desired_state(interface_name, True)
        return {"interface_name": interface_name, "active": True, "desired": True, "action": action}

    def stop(self, interface_name: str) -> dict:
        interface_name = self.validate_interface_name(interface_name)
        path = self.config_path(interface_name)
        if self.is_active(interface_name):
            self._run(["wg-quick", "down", str(path)])
            action = "stopped"
        else:
            action = "already_stopped"
        self.set_desired_state(interface_name, False)
        return {"interface_name": interface_name, "active": False, "desired": False, "action": action}

    def peer_telemetry(self, interface_name: str) -> list[dict]:
        interface_name = self.validate_interface_name(interface_name)
        result = self._run(["wg", "show", interface_name, "dump"])
        return parse_wireguard_dump(result.stdout)

    def status(self, interface_name: str) -> dict:
        interface_name = self.validate_interface_name(interface_name)
        active = self.is_active(interface_name)
        return {
            "interface_name": interface_name,
            "active": active,
            "desired": self.should_restore(interface_name),
            "config_path": str(self.config_path(interface_name)),
        }
