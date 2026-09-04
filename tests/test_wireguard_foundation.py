import base64

import pytest

from app.utils.crypto import (
    generate_wireguard_keypair,
    get_wireguard_public_key,
    validate_wireguard_key,
)
from app.wireguard import WireGuardConfig


def test_generate_wireguard_keypair_returns_matching_32_byte_keys():
    private_key, public_key = generate_wireguard_keypair()

    assert len(base64.b64decode(private_key, validate=True)) == 32
    assert len(base64.b64decode(public_key, validate=True)) == 32
    assert get_wireguard_public_key(private_key) == public_key


def test_validate_wireguard_key_normalizes_padding():
    private_key, _ = generate_wireguard_keypair()
    assert validate_wireguard_key(private_key.rstrip("=")) == private_key


@pytest.mark.parametrize("value", ["", "not-base64", base64.b64encode(b"short").decode()])
def test_validate_wireguard_key_rejects_invalid_values(value):
    with pytest.raises(ValueError, match="Invalid private_key"):
        validate_wireguard_key(value, "private_key")


def test_wireguard_config_validates_and_resolves_inbound_metadata():
    private_key, public_key = generate_wireguard_keypair()
    config = WireGuardConfig(
        {
            "interface_name": "wg-marzban.0",
            "private_key": private_key,
            "listen_port": 51820,
            "address": ["10.20.0.1/24", "fd42::1/64"],
        }
    )

    assert config["public_key"] == public_key
    assert config["address"] == ["10.20.0.1/24", "fd42::1/64"]
    assert config.inbounds == ["wg-marzban.0"]
    assert config.inbounds_by_tag["wg-marzban.0"] == {
        "tag": "wg-marzban.0",
        "protocol": "wireguard",
        "network": "udp",
        "tls": "none",
        "interface_name": "wg-marzban.0",
        "listen_port": 51820,
        "address": ["10.20.0.1/24", "fd42::1/64"],
        "public_key": public_key,
        "private_key": private_key,
        "pre_shared_key": "",
    }


def test_wireguard_config_round_trip_preserves_resolved_metadata():
    private_key, _ = generate_wireguard_keypair()
    original = WireGuardConfig(
        {
            "interface_name": "wg0",
            "private_key": private_key,
            "listen_port": 51820,
            "address": ["10.30.0.1/24"],
        }
    )

    restored = WireGuardConfig.from_json(original.to_json())
    assert restored == original
    assert restored.inbounds == original.inbounds
    assert restored.inbounds_by_tag == original.inbounds_by_tag


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("interface_name", "bad interface", "interface_name must"),
        ("listen_port", 0, "listen_port must"),
        ("listen_port", 65536, "listen_port must"),
        ("address", [], "address must"),
        ("address", ["not-a-cidr"], "does not appear"),
    ],
)
def test_wireguard_config_rejects_invalid_interface_settings(field, value, message):
    private_key, _ = generate_wireguard_keypair()
    data = {
        "interface_name": "wg0",
        "private_key": private_key,
        "listen_port": 51820,
        "address": ["10.40.0.1/24"],
    }
    data[field] = value

    with pytest.raises((TypeError, ValueError), match=message):
        WireGuardConfig(data)
