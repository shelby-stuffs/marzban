from types import SimpleNamespace

import pytest

from app.utils.crypto import generate_wireguard_keypair
from app.wireguard import WireGuardConfig, WireGuardPeerSettings
from app.wireguard import storage


def server_record():
    private_key, _ = generate_wireguard_keypair()
    config = WireGuardConfig(
        {
            "interface_name": "wg0",
            "private_key": private_key,
            "listen_port": 51820,
            "address": ["10.80.0.1/29", "fd42:80::1/124"],
        }
    )
    return SimpleNamespace(config=dict(config))


def test_allocate_wireguard_peer_uses_persisted_occupancy(monkeypatch):
    saved = {}
    monkeypatch.setattr(storage, "get_wireguard_server", lambda db: server_record())
    monkeypatch.setattr(storage, "get_wireguard_peer", lambda db, user_id: None)
    monkeypatch.setattr(
        storage,
        "get_occupied_wireguard_peer_ips",
        lambda db, exclude_user_id=None: ["10.80.0.2/32", "fd42:80::2/128"],
    )

    def save(db, *, user_id, settings):
        saved["user_id"] = user_id
        saved["settings"] = settings
        return SimpleNamespace(settings=settings.model_dump(mode="json"))

    monkeypatch.setattr(storage, "save_wireguard_peer", save)

    record = storage.allocate_wireguard_peer(object(), user_id=42)
    settings = WireGuardPeerSettings.model_validate(record.settings)

    assert saved["user_id"] == 42
    assert settings.private_key
    assert settings.public_key
    assert settings.peer_ips == ["10.80.0.3/32", "fd42:80::3/128"]


def test_allocate_wireguard_peer_preserves_current_addresses_and_keys(monkeypatch):
    private_key, public_key = generate_wireguard_keypair()
    current = WireGuardPeerSettings(
        private_key=private_key,
        public_key=public_key,
        peer_ips=["10.80.0.5/32", "fd42:80::5/128"],
    )
    current_record = SimpleNamespace(settings=current.model_dump(mode="json"))

    monkeypatch.setattr(storage, "get_wireguard_server", lambda db: server_record())
    monkeypatch.setattr(storage, "get_wireguard_peer", lambda db, user_id: current_record)
    monkeypatch.setattr(storage, "get_occupied_wireguard_peer_ips", lambda db, exclude_user_id=None: [])
    monkeypatch.setattr(
        storage,
        "save_wireguard_peer",
        lambda db, *, user_id, settings: SimpleNamespace(settings=settings.model_dump(mode="json")),
    )

    record = storage.allocate_wireguard_peer(object(), user_id=42)
    settings = WireGuardPeerSettings.model_validate(record.settings)

    assert settings.private_key == private_key
    assert settings.public_key == public_key
    assert settings.peer_ips == ["10.80.0.5/32", "fd42:80::5/128"]


def test_allocate_wireguard_peer_requires_server(monkeypatch):
    monkeypatch.setattr(storage, "get_wireguard_server", lambda db: None)

    with pytest.raises(ValueError, match="server is not configured"):
        storage.allocate_wireguard_peer(object(), user_id=42)
