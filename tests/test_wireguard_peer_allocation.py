import pytest

from app.utils.crypto import generate_wireguard_keypair
from app.wireguard import WireGuardPeerSettings, allocate_peer_ips, build_namespaces


def test_peer_settings_generate_and_preserve_matching_keypair():
    settings = WireGuardPeerSettings().ensure_keypair()

    assert settings.private_key
    assert settings.public_key
    assert WireGuardPeerSettings(
        private_key=settings.private_key,
        public_key=settings.public_key,
    ) == settings


def test_peer_settings_reject_mismatched_public_key():
    private_key, _ = generate_wireguard_keypair()
    _, unrelated_public_key = generate_wireguard_keypair()

    with pytest.raises(ValueError, match="does not match"):
        WireGuardPeerSettings(private_key=private_key, public_key=unrelated_public_key)


def test_peer_settings_normalize_and_deduplicate_addresses():
    settings = WireGuardPeerSettings(
        peer_ips=["10.0.0.9/24", "10.0.0.9/32", "fd42::9/64", "fd42::9/128"]
    )

    assert settings.peer_ips == ["10.0.0.0/32", "10.0.0.9/32", "fd42::/128", "fd42::9/128"]


def test_namespaces_reserve_interface_and_boundary_addresses():
    namespaces = build_namespaces(["10.10.0.1/29", "fd42::1/124"])

    assert [str(namespace.subnet) for namespace in namespaces] == ["10.10.0.0/29", "fd42::/124"]
    assert namespaces[0].reserved == frozenset({0, 1, 7})
    assert namespaces[1].reserved == frozenset({0, 1, 15})


def test_allocator_assigns_one_address_per_ipv4_and_ipv6_subnet():
    allocated = allocate_peer_ips(
        ["10.20.0.1/29", "fd42:20::1/124"],
        occupied_peer_ips=["10.20.0.2/32", "fd42:20::2/128"],
    )

    assert allocated == ["10.20.0.3/32", "fd42:20::3/128"]


def test_allocator_preserves_current_addresses_when_available():
    allocated = allocate_peer_ips(
        ["10.30.0.1/29"],
        occupied_peer_ips=["10.30.0.2/32"],
        current_peer_ips=["10.30.0.5/32"],
    )

    assert allocated == ["10.30.0.5/32"]


def test_allocator_reallocates_current_address_owned_by_another_peer():
    allocated = allocate_peer_ips(
        ["10.40.0.1/29"],
        occupied_peer_ips=["10.40.0.5/32"],
        current_peer_ips=["10.40.0.5/32"],
    )

    assert allocated == ["10.40.0.2/32"]


def test_allocator_reports_exhausted_subnet():
    with pytest.raises(ValueError, match="has no free addresses"):
        allocate_peer_ips(
            ["10.50.0.1/30"],
            occupied_peer_ips=["10.50.0.2/32"],
        )
