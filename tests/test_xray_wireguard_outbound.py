import pytest

from app.utils.crypto import generate_wireguard_keypair
from app.xray.wireguard_outbound import (
    build_wireguard_outbound,
    remove_wireguard_outbound,
    upsert_wireguard_outbound,
)


def make_outbound(tag="wg-out"):
    secret_key, _ = generate_wireguard_keypair()
    _, peer_public_key = generate_wireguard_keypair()
    return build_wireguard_outbound(
        tag=tag,
        secret_key=secret_key,
        address=["172.16.0.2/32", "2606:4700:110:8765::2/128"],
        peers=[
            {
                "public_key": peer_public_key,
                "endpoint": "engage.cloudflareclient.com:2408",
                "allowed_ips": ["0.0.0.0/0", "::/0"],
                "keep_alive": 25,
            }
        ],
        mtu=1280,
        reserved=[0, 0, 0],
    )


def test_builds_xray_wireguard_outbound_schema():
    outbound = make_outbound()

    assert outbound["protocol"] == "wireguard"
    assert outbound["tag"] == "wg-out"
    assert outbound["settings"]["address"] == [
        "172.16.0.2/32",
        "2606:4700:110:8765::2/128",
    ]
    assert outbound["settings"]["peers"][0]["allowedIPs"] == ["0.0.0.0/0", "::/0"]
    assert outbound["settings"]["peers"][0]["keepAlive"] == 25


def test_upsert_replaces_outbound_and_managed_routing_rule():
    config = {
        "inbounds": [{"tag": "vless-in", "protocol": "vless"}],
        "outbounds": [
            {"tag": "direct", "protocol": "freedom"},
            {"tag": "wg-out", "protocol": "blackhole"},
        ],
        "routing": {
            "rules": [
                {"type": "field", "outboundTag": "wg-out", "inboundTag": ["old-in"]},
                {"type": "field", "outboundTag": "direct", "domain": ["example.com"]},
            ]
        },
    }

    updated = upsert_wireguard_outbound(
        config,
        outbound=make_outbound(),
        route_inbound_tags=["vless-in", "vless-in"],
    )

    assert len([item for item in updated["outbounds"] if item["tag"] == "wg-out"]) == 1
    assert updated["routing"]["rules"][-1] == {
        "type": "field",
        "inboundTag": ["vless-in"],
        "outboundTag": "wg-out",
    }
    assert config["outbounds"][1]["protocol"] == "blackhole"


def test_remove_deletes_outbound_and_its_routing_rules():
    config = upsert_wireguard_outbound(
        {"outbounds": [{"tag": "direct", "protocol": "freedom"}]},
        outbound=make_outbound(),
        route_inbound_tags=["vless-in"],
    )

    updated = remove_wireguard_outbound(config, "wg-out")

    assert updated["outbounds"] == [{"tag": "direct", "protocol": "freedom"}]
    assert updated["routing"]["rules"] == []


def test_rejects_invalid_reserved_bytes():
    with pytest.raises(ValueError, match="exactly three bytes"):
        outbound = make_outbound()
        outbound["settings"]["reserved"] = [0, 1]
        build_wireguard_outbound(
            tag="wg-out",
            secret_key=outbound["settings"]["secretKey"],
            address=outbound["settings"]["address"],
            peers=[
                {
                    "public_key": outbound["settings"]["peers"][0]["publicKey"],
                    "endpoint": "example.com:51820",
                    "allowed_ips": ["0.0.0.0/0"],
                }
            ],
            reserved=[0, 1],
        )
