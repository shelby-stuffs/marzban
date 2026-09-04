from app.wireguard.runtime import WireGuardRuntime, parse_wireguard_dump


def test_parse_wireguard_dump_exposes_peer_health_metrics():
    output = (
        "server-private\tserver-public\t51820\toff\n"
        "peer-public\t(none)\t198.51.100.10:51820\t10.0.0.2/32,fd42::2/128"
        "\t1728000000\t1024\t2048\t25\n"
    )

    assert parse_wireguard_dump(output) == [
        {
            "public_key": "peer-public",
            "endpoint": "198.51.100.10:51820",
            "allowed_ips": ["10.0.0.2/32", "fd42::2/128"],
            "latest_handshake": 1728000000,
            "transfer_rx": 1024,
            "transfer_tx": 2048,
            "persistent_keepalive": 25,
        }
    ]


def test_desired_state_marker_controls_startup_restore(tmp_path):
    runtime = WireGuardRuntime(config_dir=tmp_path)

    assert runtime.should_restore("wg0") is False

    runtime.set_desired_state("wg0", True)
    marker = tmp_path / ".wg0.marzban-enabled"

    assert runtime.should_restore("wg0") is True
    assert marker.exists()

    runtime.set_desired_state("wg0", False)

    assert runtime.should_restore("wg0") is False
    assert not marker.exists()


def test_parse_wireguard_dump_ignores_incomplete_rows():
    output = "server-private\tserver-public\t51820\toff\ninvalid-peer-row\n"

    assert parse_wireguard_dump(output) == []
