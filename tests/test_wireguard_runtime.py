import stat
from types import SimpleNamespace

import pytest

from app.utils.crypto import generate_wireguard_keypair
from app.wireguard import WireGuardConfig, WireGuardPeerSettings
from app.wireguard.runtime import WireGuardRuntime, render_wireguard_server_config


def make_server():
    private_key, _ = generate_wireguard_keypair()
    return WireGuardConfig(
        {
            "interface_name": "wg0",
            "private_key": private_key,
            "listen_port": 51820,
            "address": ["10.90.0.1/24", "fd42:90::1/64"],
        }
    )


def make_peer():
    private_key, public_key = generate_wireguard_keypair()
    return WireGuardPeerSettings(
        private_key=private_key,
        public_key=public_key,
        peer_ips=["10.90.0.2/32", "fd42:90::2/128"],
    )


def test_render_server_config_contains_peer_routes():
    content = render_wireguard_server_config(make_server(), [make_peer()])

    assert "[Interface]" in content
    assert "ListenPort = 51820" in content
    assert "[Peer]" in content
    assert "AllowedIPs = 10.90.0.2/32, fd42:90::2/128" in content


def test_apply_starts_inactive_interface_and_writes_private_config(tmp_path):
    calls = []

    def runner(args, **kwargs):
        calls.append((args, kwargs))
        stdout = "" if args == ["wg", "show", "interfaces"] else ""
        return SimpleNamespace(stdout=stdout, stderr="")

    runtime = WireGuardRuntime(config_dir=tmp_path, runner=runner)
    result = runtime.apply(make_server(), [make_peer()])
    path = tmp_path / "wg0.conf"

    assert result["action"] == "started"
    assert calls[-1][0] == ["wg-quick", "up", str(path)]
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_apply_synchronizes_active_interface_without_shell(tmp_path):
    calls = []

    def runner(args, **kwargs):
        calls.append((args, kwargs))
        if args == ["wg", "show", "interfaces"]:
            return SimpleNamespace(stdout="wg0\n", stderr="")
        if args[:2] == ["wg-quick", "strip"]:
            return SimpleNamespace(stdout="[Interface]\nListenPort = 51820\n", stderr="")
        return SimpleNamespace(stdout="", stderr="")

    runtime = WireGuardRuntime(config_dir=tmp_path, runner=runner)
    result = runtime.apply(make_server(), [make_peer()])

    assert result["action"] == "synchronized"
    sync_args, sync_kwargs = calls[-1]
    assert sync_args == ["wg", "syncconf", "wg0", "/dev/stdin"]
    assert sync_kwargs["input"] == "[Interface]\nListenPort = 51820\n"
    assert all(kwargs.get("shell") is not True for _, kwargs in calls)


def test_runtime_rejects_unsafe_interface_names(tmp_path):
    runtime = WireGuardRuntime(config_dir=tmp_path)

    with pytest.raises(ValueError, match="Invalid WireGuard interface name"):
        runtime.config_path("wg0;rm -rf /")
