import json
from urllib.parse import parse_qs, urlsplit

from app.subscription.xhttp import enrich_xhttp_share_link
from app.xray.xhttp import enrich_xhttp_inbound_metadata, get_xhttp_settings


class FakeConfig(dict):
    def __init__(self, *args, inbounds_by_tag, **kwargs):
        super().__init__(*args, **kwargs)
        self.inbounds_by_tag = inbounds_by_tag


def test_get_xhttp_settings_accepts_legacy_splithttp():
    settings = {"mode": "stream-up", "path": "/legacy"}
    stream = {"network": "splithttp", "splithttpSettings": settings}

    assert get_xhttp_settings(stream) == settings


def test_enrich_xhttp_metadata_exposes_v26_fields():
    settings = {
        "path": "/xhttp",
        "host": "cdn.example.com",
        "mode": "packet-up",
        "noSSEHeader": True,
        "scMaxBufferedPosts": 32,
        "xPaddingObfsMode": True,
        "xPaddingKey": "padding",
        "sessionIDPlacement": "header",
        "sessionIDKey": "X-Session-ID",
        "seqPlacement": "query",
        "seqKey": "seq",
        "uplinkDataPlacement": "body",
        "uplinkChunkSize": "1024-4096",
        "serverMaxHeaderBytes": 8192,
        "downloadSettings": {"address": "download.example.com", "port": 443},
    }
    config = FakeConfig(
        {
            "inbounds": [
                {
                    "tag": "xhttp-in",
                    "streamSettings": {"network": "xhttp", "xhttpSettings": settings},
                }
            ]
        },
        inbounds_by_tag={"xhttp-in": {"network": "xhttp"}},
    )

    enrich_xhttp_inbound_metadata(config)

    metadata = config.inbounds_by_tag["xhttp-in"]
    assert metadata["host"] == ["cdn.example.com"]
    assert metadata["noSSEHeader"] is True
    assert metadata["scMaxBufferedPosts"] == 32
    assert metadata["xPaddingObfsMode"] is True
    assert metadata["sessionIDKey"] == "X-Session-ID"
    assert metadata["uplinkChunkSize"] == "1024-4096"
    assert metadata["downloadSettings"]["port"] == 443


def test_vless_share_link_contains_advanced_xhttp_extra():
    link = "vless://user@example.com:443?security=tls&type=xhttp&mode=auto#example"
    inbound = {
        "network": "xhttp",
        "mode": "stream-up",
        "xPaddingObfsMode": True,
        "uplinkHTTPMethod": "POST",
        "sessionIDPlacement": "header",
        "sessionIDKey": "X-Session-ID",
        "serverMaxHeaderBytes": 8192,
    }

    enriched = enrich_xhttp_share_link(link, inbound)
    query = parse_qs(urlsplit(enriched).query)
    extra = json.loads(query["extra"][0])

    assert query["mode"] == ["stream-up"]
    assert extra["xPaddingObfsMode"] is True
    assert extra["uplinkHTTPMethod"] == "POST"
    assert extra["sessionIDKey"] == "X-Session-ID"
    assert extra["serverMaxHeaderBytes"] == 8192
