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


def test_singbox_subscription_does_not_export_custom_vless_inbound():
    config = object.__new__(SingBoxConfiguration)
    config.proxy_remarks = []
    config.config = {"outbounds": []}

    config.add_custom_inbounds(
        {"vless": {"id": "00000000-0000-0000-0000-000000000001"}},
        {"SERVER_IP": "203.0.113.10", "USERNAME": "alice"},
        {
            "inbounds": [{
                "type": "vless",
                "tag": "vless-custom",
                "listen_port": 8443,
                "tls": {"enabled": True, "server_name": "edge.example.com"},
                "transport": {"type": "ws", "path": "/edge"},
            }]
        },
    )

    assert config.config["outbounds"] == []


def test_singbox_custom_inbound_subscription_keeps_client_fields_and_flow():
    config = object.__new__(SingBoxConfiguration)
    config.proxy_remarks = []
    config.config = {"outbounds": []}

    config.add_custom_inbounds(
        {"vless": {
            "id": "00000000-0000-0000-0000-000000000002",
            "flow": "xtls-rprx-vision",
        }},
        {"SERVER_IP": "203.0.113.11", "USERNAME": "bob"},
        {
            "inbounds": [{
                "type": "vless",
                "tag": "reality-in",
                "listen_port": 443,
                "tls": {
                    "enabled": True,
                    "server_name": "edge.example.com",
                    "reality": {
                        "enabled": True,
                        "public_key": "public-key",
                        "short_id": "abcd",
                        "private_key": "must-not-leak",
                    },
                },
            }]
        },
    )

    outbound = config.config["outbounds"][0]
    assert outbound["flow"] == "xtls-rprx-vision"
    assert outbound["tls"]["reality"] == {
        "enabled": True,
        "public_key": "public-key",
        "short_id": "abcd",
    }


def test_singbox_custom_shadowsocks_inbound_uses_server_method():
    config = object.__new__(SingBoxConfiguration)
    config.proxy_remarks = []
    config.config = {"outbounds": []}

    config.add_custom_inbounds(
        {"shadowsocks": {
            "password": "user-password",
            "method": "aes-128-gcm",
        }},
        {"SERVER_IP": "203.0.113.12", "USERNAME": "sam"},
        {
            "inbounds": [{
                "type": "shadowsocks",
                "tag": "ss-in",
                "listen_port": 8388,
                "method": "chacha20-ietf-poly1305",
            }]
        },
    )

    assert config.config["outbounds"][0]["method"] == "chacha20-ietf-poly1305"


def test_singbox_subscription_exports_manual_anytls_client_by_username():
    config = object.__new__(SingBoxConfiguration)
    config.proxy_remarks = []
    config.config = {"outbounds": []}

    config.add_custom_inbounds(
        {},
        {"SERVER_IP": "203.0.113.13", "USERNAME": "alice"},
        {
            "inbounds": [{
                "type": "anytls",
                "tag": "anytls-in",
                "listen_port": 8443,
                "tls": {"enabled": True, "server_name": "edge.example.com"},
                "users": [{"name": "alice", "password": "client-secret"}],
            }]
        },
    )

    assert config.config["outbounds"] == [{
        "type": "anytls",
        "tag": "alice [anytls / anytls-in]",
        "server": "203.0.113.13",
        "server_port": 8443,
        "password": "client-secret",
        "tls": {"enabled": True, "server_name": "edge.example.com"},
    }]


def test_common_link_subscription_exports_custom_vless_xhttp():
    links = V2rayShareLink()
    links.add_singbox_outbounds([{
        "type": "vless",
        "tag": "alice [vless / xhttp-in]",
        "server": "203.0.113.14",
        "server_port": 2023,
        "uuid": "00000000-0000-0000-0000-000000000003",
        "transport": {
            "type": "xhttp",
            "mode": "auto",
            "path": "/lol",
            "headers": {"Host": "edge.example.com"},
            "x_padding_bytes": "100-1000",
            "no_sse_header": False,
        },
        "tls": {
            "enabled": True,
            "server_name": "edge.example.com",
        },
    }])

    parsed = urlsplit(links.links[0])
    query = parse_qs(parsed.query)
    assert parsed.scheme == "vless"
    assert parsed.username == "00000000-0000-0000-0000-000000000003"
    assert query["type"] == ["xhttp"]
    assert query["path"] == ["/lol"]
    assert query["host"] == ["edge.example.com"]
    assert query["mode"] == ["auto"]
    assert json.loads(query["extra"][0]) == {
        "xPaddingBytes": "100-1000",
        "noSSEHeader": False,
    }
