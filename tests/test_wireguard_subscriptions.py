import io
import zipfile

import pytest

from app.utils.crypto import generate_wireguard_keypair
from app.wireguard import (
    WireGuardConfig,
    WireGuardPeerSettings,
    WireGuardSubscription,
    render_wireguard_client_config,
)


def make_server(**overrides):
    private_key, _ = generate_wireguard_keypair()
    data = {
        "interface_name": "wg0",
        "private_key": private_key,
        "listen_port": 51820,
        "address": ["10.60.0.1/24", "fd42:60::1/64"],
    }
    data.update(overrides)
    return WireGuardConfig(data)


def make_peer():
    return WireGuardPeerSettings(peer_ips=["10.60.0.2/32", "fd42:60::2/128"]).ensure_keypair()


def test_render_wireguard_client_config():
    pre_shared_key, _ = generate_wireguard_keypair()
    server = make_server(pre_shared_key=pre_shared_key)
    peer = make_peer()

    config = render_wireguard_client_config(
        peer=peer,
        server=server,
        endpoint_address="2001:db8::10",
        allowed_ips=["0.0.0.0/0", "::/0"],
        dns=["1.1.1.1", "2606:4700:4700::1111"],
        mtu=1380,
        persistent_keepalive=25,
        reserved=[1, 2, 3],
    )

    assert f"PrivateKey = {peer.private_key}" in config
    assert "Address = 10.60.0.2/32, fd42:60::2/128" in config
    assert "DNS = 1.1.1.1, 2606:4700:4700::1111" in config
    assert "MTU = 1380" in config
    assert "Reserved = 1, 2, 3" in config
    assert f"PublicKey = {server['public_key']}" in config
    assert f"PresharedKey = {server['pre_shared_key']}" in config
    assert "AllowedIPs = 0.0.0.0/0, ::/0" in config
    assert "Endpoint = [2001:db8::10]:51820" in config
    assert "PersistentKeepalive = 25" in config


def test_subscription_zip_uses_safe_unique_filenames():
    server = make_server()
    subscription = WireGuardSubscription()

    kwargs = {
        "peer": make_peer(),
        "server": server,
        "endpoint_address": "vpn.example.com",
    }
    subscription.add("Main / WireGuard", **kwargs)
    subscription.add("Main / WireGuard", **kwargs)

    with zipfile.ZipFile(io.BytesIO(subscription.render())) as archive:
        assert archive.namelist() == [
            "Main_WireGuard.conf",
            "Main_WireGuard_2.conf",
        ]
        first_config = archive.read("Main_WireGuard.conf").decode()

    assert "Endpoint = vpn.example.com:51820" in first_config
    assert first_config.startswith("[Interface]\n")
    assert "\n[Peer]\n" in first_config


def test_render_requires_allocated_peer_address():
    with pytest.raises(ValueError, match="no allocated addresses"):
        render_wireguard_client_config(
            peer=WireGuardPeerSettings().ensure_keypair(),
            server=make_server(),
            endpoint_address="vpn.example.com",
        )


@pytest.mark.parametrize("port", [0, 65536, True])
def test_render_rejects_invalid_endpoint_port(port):
    with pytest.raises(ValueError, match="endpoint port"):
        render_wireguard_client_config(
            peer=make_peer(),
            server=make_server(),
            endpoint_address="vpn.example.com",
            endpoint_port=port,
        )
