import pytest
from pydantic import ValidationError

from app.models.xhttp import XHTTPHostSettings, XHTTPProxyHost


def test_xhttp_settings_accept_v26_aliases_and_dump_for_xray():
    settings = XHTTPHostSettings.model_validate(
        {
            "mode": "stream-up",
            "noSSEHeader": False,
            "xPaddingBytes": "100-1000",
            "uplinkHTTPMethod": "post",
            "sessionIDLength": 16,
            "headers": {"X-Test": "yes"},
        }
    )

    assert settings.uplink_http_method == "POST"
    assert settings.model_dump(by_alias=True, exclude_none=True) == {
        "mode": "stream-up",
        "headers": {"X-Test": "yes"},
        "noSSEHeader": False,
        "xPaddingBytes": "100-1000",
        "uplinkHTTPMethod": "POST",
        "sessionIDLength": 16,
    }


def test_xhttp_settings_reject_unknown_and_invalid_values():
    with pytest.raises(ValidationError):
        XHTTPHostSettings.model_validate({"mode": "invalid"})
    with pytest.raises(ValidationError):
        XHTTPHostSettings.model_validate({"xPaddingBytes": "1000-100"})
    with pytest.raises(ValidationError):
        XHTTPHostSettings.model_validate({"uplinkHTTPMethod": "DELETE"})
    with pytest.raises(ValidationError):
        XHTTPHostSettings.model_validate({"unknownField": True})


def test_proxy_host_accepts_typed_xhttp_settings():
    host = XHTTPProxyHost(
        remark="XHTTP",
        address="cdn.example.com",
        xhttp_settings={"mode": "packet-up", "scMaxBufferedPosts": 16},
    )

    assert host.xhttp_settings.mode == "packet-up"
    assert host.xhttp_settings.sc_max_buffered_posts == 16
