import pytest

from app.xray.xhttp_inbound import list_xhttp_inbounds, update_xhttp_inbound


def _config():
    return {
        "inbounds": [
            {
                "tag": "vless-xhttp",
                "listen": "0.0.0.0",
                "port": 443,
                "protocol": "vless",
                "streamSettings": {
                    "network": "splithttp",
                    "splithttpSettings": {"path": "/old", "mode": "auto"},
                },
            },
            {
                "tag": "vless-raw",
                "protocol": "vless",
                "streamSettings": {"network": "raw"},
            },
        ]
    }


def test_list_xhttp_inbounds_supports_legacy_settings():
    result = list_xhttp_inbounds(_config())

    assert result == [
        {
            "tag": "vless-xhttp",
            "protocol": "vless",
            "listen": "0.0.0.0",
            "port": 443,
            "settings": {"path": "/old", "mode": "auto"},
        }
    ]


def test_update_xhttp_inbound_canonicalizes_transport():
    updated = update_xhttp_inbound(
        _config(),
        "vless-xhttp",
        {"path": "/new", "mode": "stream-up", "noSSEHeader": True},
    )
    stream = updated["inbounds"][0]["streamSettings"]

    assert stream["network"] == "xhttp"
    assert "splithttpSettings" not in stream
    assert stream["xhttpSettings"] == {
        "path": "/new",
        "mode": "stream-up",
        "noSSEHeader": True,
    }


def test_update_rejects_missing_or_non_xhttp_inbound():
    with pytest.raises(ValueError, match="does not exist"):
        update_xhttp_inbound(_config(), "missing", {})
    with pytest.raises(ValueError, match="not an XHTTP"):
        update_xhttp_inbound(_config(), "vless-raw", {})
