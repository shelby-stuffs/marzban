from app.subscription.linkfilter import HYSTERIA2_SCHEMES, filter_links


def test_filter_links_keeps_only_requested_schemes():
    links = [
        "vless://uuid@example.com:443#node-1",
        "hysteria2://secret@example.com:443#node-2",
        "hy2://secret@example.com:8443#node-3",
        "vmess://base64payload",
    ]

    assert filter_links(links, HYSTERIA2_SCHEMES) == [
        "hysteria2://secret@example.com:443#node-2",
        "hy2://secret@example.com:8443#node-3",
    ]


def test_filter_links_is_case_insensitive_and_skips_blanks():
    links = ["", None, "  HYSTERIA2://secret@example.com:443", "trojan://x@y:443"]

    assert filter_links(links, HYSTERIA2_SCHEMES) == ["  HYSTERIA2://secret@example.com:443"]


def test_filter_links_returns_empty_when_nothing_matches():
    assert filter_links(["vless://a@b:443"], HYSTERIA2_SCHEMES) == []
