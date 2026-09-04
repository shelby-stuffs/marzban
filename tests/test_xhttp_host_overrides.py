from app.models.xhttp import XHTTPProxyHost
from app.utils.xhttp import xhttp_extra_from_metadata


def test_xhttp_proxy_host_accepts_transport_overrides():
    host = XHTTPProxyHost(
        remark="XHTTP",
        address="cdn.example.com",
        xhttp_settings={
            "mode": "stream-up",
            "noSSEHeader": True,
            "xPaddingObfsMode": True,
            "sessionIDPlacement": "header",
            "sessionIDKey": "X-Session-ID",
            "uplinkChunkSize": "1024-4096",
            "xmux": {"maxConcurrency": "8-16"},
        },
    )

    assert host.xhttp_settings["mode"] == "stream-up"
    assert host.xhttp_settings["noSSEHeader"] is True
    assert xhttp_extra_from_metadata(host.xhttp_settings)["sessionIDKey"] == "X-Session-ID"


def test_xhttp_proxy_host_remains_backward_compatible():
    host = XHTTPProxyHost(remark="Legacy", address="example.com")

    assert host.xhttp_settings is None
