from app.subscription.clash_xhttp import make_mihomo_xhttp_opts


def test_mihomo_xhttp_opts_include_v26_fields():
    opts = make_mihomo_xhttp_opts(
        {
            "path": "/xhttp",
            "host": ["cdn.example.com"],
            "mode": "stream-up",
            "headers": {"Host": "ignored.example.com", "X-Test": "yes"},
            "noGRPCHeader": False,
            "noSSEHeader": True,
            "xPaddingBytes": "100-1000",
            "xPaddingObfsMode": True,
            "uplinkHTTPMethod": "POST",
            "sessionIDPlacement": "header",
            "sessionIDKey": "X-Session-ID",
            "seqPlacement": "query",
            "seqKey": "seq",
            "uplinkDataPlacement": "body",
            "uplinkChunkSize": "1024-4096",
            "serverMaxHeaderBytes": 8192,
            "xmux": {
                "maxConcurrency": "16-32",
                "hKeepAlivePeriod": 30,
            },
        }
    )

    assert opts["path"] == "/xhttp"
    assert opts["host"] == "cdn.example.com"
    assert opts["headers"] == {"X-Test": "yes"}
    assert opts["no-grpc-header"] is False
    assert opts["no-sse-header"] is True
    assert opts["x-padding-obfs-mode"] is True
    assert opts["session-key"] == "X-Session-ID"
    assert opts["uplink-chunk-size"] == "1024-4096"
    assert opts["server-max-header-bytes"] == 8192
    assert opts["reuse-settings"] == {
        "max-concurrency": "16-32",
        "h-keep-alive-period": 30,
    }


def test_mihomo_xhttp_opts_convert_download_settings():
    opts = make_mihomo_xhttp_opts(
        {
            "path": "/upload",
            "downloadSettings": {
                "address": "download.example.com",
                "port": 443,
                "streamSettings": {
                    "security": "reality",
                    "xhttpSettings": {"path": "/download", "host": "cdn.example.com"},
                    "realitySettings": {
                        "serverName": "reality.example.com",
                        "fingerprint": "chrome",
                        "publicKey": "public-key",
                        "shortId": "abcd",
                    },
                },
            },
        }
    )

    download = opts["download-settings"]
    assert download["server"] == "download.example.com"
    assert download["port"] == 443
    assert download["path"] == "/download"
    assert download["tls"] is True
    assert download["servername"] == "reality.example.com"
    assert download["reality-opts"] == {
        "public-key": "public-key",
        "short-id": "abcd",
    }
