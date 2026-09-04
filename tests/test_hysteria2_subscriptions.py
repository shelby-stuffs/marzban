import json
from urllib.parse import parse_qs, unquote, urlsplit

from app.subscription.clash import ClashMetaConfiguration
from app.subscription.singbox import SingBoxConfiguration
from app.subscription.v2ray import V2rayShareLink


def hysteria_inbound(**overrides):
    inbound = {
        "protocol": "hysteria",
        "network": "hysteria",
        "path": "",
        "port": 443,
        "sni": "edge.example.com",
        "alpn": "h3",
        "ais": False,
        "obfs": "salamander",
        "obfs_password": "obfs-secret",
    }
    inbound.update(overrides)
    return inbound


def test_hysteria2_share_link_contains_tls_and_obfs_options():
    links = V2rayShareLink()
    links.add(
        remark="Hysteria node",
        address="203.0.113.10",
        inbound=hysteria_inbound(),
        settings={"auth": "user-secret"},
    )

    assert len(links.links) == 1
    parsed = urlsplit(links.links[0])
    query = parse_qs(parsed.query)

    assert parsed.scheme == "hysteria2"
    assert parsed.username == "user-secret"
    assert parsed.hostname == "203.0.113.10"
    assert parsed.port == 443
    assert unquote(parsed.fragment) == "Hysteria node"
    assert query["sni"] == ["edge.example.com"]
    assert query["alpn"] == ["h3"]
    assert query["obfs"] == ["salamander"]
    assert query["obfs-password"] == ["obfs-secret"]
    assert json.loads(query["fm"][0]) == {
        "udp": [{"type": "salamander", "settings": {"password": "obfs-secret"}}]
    }


def test_hysteria2_share_link_marks_insecure_tls():
    links = V2rayShareLink()
    links.add(
        remark="insecure",
        address="edge.example.com",
        inbound=hysteria_inbound(ais=True, obfs="", obfs_password=""),
        settings={"auth": "secret"},
    )

    query = parse_qs(urlsplit(links.links[0]).query)
    assert query["insecure"] == ["1"]
    assert "obfs" not in query
    assert "obfs-password" not in query


def test_clash_meta_hysteria2_node_uses_sni_and_obfs():
    config = object.__new__(ClashMetaConfiguration)
    config.data = {"proxies": [], "proxy-groups": [], "rules": []}
    config.proxy_remarks = []

    config.add(
        remark="Hysteria node",
        address="edge.example.com",
        inbound=hysteria_inbound(),
        settings={"auth": "user-secret"},
    )

    assert config.data["proxies"] == [
        {
            "name": "Hysteria node",
            "type": "hysteria2",
            "server": "edge.example.com",
            "port": 443,
            "password": "user-secret",
            "sni": "edge.example.com",
            "alpn": ["h3"],
            "obfs": "salamander",
            "obfs-password": "obfs-secret",
        }
    ]


def test_singbox_hysteria2_outbound_uses_tls_and_obfs():
    config = object.__new__(SingBoxConfiguration)
    config.proxy_remarks = []
    config.config = {"outbounds": []}

    config.add(
        remark="Hysteria node",
        address="edge.example.com",
        inbound=hysteria_inbound(),
        settings={"auth": "user-secret"},
    )

    assert config.config["outbounds"] == [
        {
            "type": "hysteria2",
            "tag": "Hysteria node",
            "server": "edge.example.com",
            "server_port": 443,
            "password": "user-secret",
            "obfs": {"type": "salamander", "password": "obfs-secret"},
            "tls": {
                "enabled": True,
                "server_name": "edge.example.com",
                "alpn": ["h3"],
            },
        }
    ]
