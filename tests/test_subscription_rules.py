import re

import pytest

from app.subscription import cache
from app.subscription.rules import (
    CONFIG_FORMATS,
    CUSTOM_JSON_FLAGS,
    DEFAULT_RULES,
    ClientRule,
    media_type_for,
    resolve_client,
    resolve_format,
    sorted_rules,
)


@pytest.fixture()
def custom_json_enabled():
    original = dict(CUSTOM_JSON_FLAGS)
    CUSTOM_JSON_FLAGS["default"] = True
    yield
    CUSTOM_JSON_FLAGS.clear()
    CUSTOM_JSON_FLAGS.update(original)


@pytest.fixture()
def custom_json_disabled():
    original = dict(CUSTOM_JSON_FLAGS)
    for key in CUSTOM_JSON_FLAGS:
        CUSTOM_JSON_FLAGS[key] = False
    yield
    CUSTOM_JSON_FLAGS.clear()
    CUSTOM_JSON_FLAGS.update(original)


def test_default_rules_are_valid_regexes_and_formats():
    for rule in DEFAULT_RULES:
        re.compile(rule.pattern)
        assert rule.config_format in CONFIG_FORMATS
        assert media_type_for(rule.config_format)


@pytest.mark.parametrize(
    "user_agent,expected",
    [
        ("clash-verge/1.0", "clash-meta"),
        ("ClashMeta/1.2", "clash-meta"),
        ("mihomo/1.0", "clash-meta"),
        ("Clash/1.0", "clash"),
        ("Stash/2.0", "clash"),
        ("SFI/1.0", "sing-box"),
        ("karing/1.0", "sing-box"),
        ("my-singbox-client", "sing-box"),
        ("Outline/1.0", "outline"),
    ],
)
def test_known_clients_keep_their_format(user_agent, expected):
    assert resolve_client(user_agent).config_format == expected


def test_unknown_client_falls_back_to_base64_links():
    resolved = resolve_client("totally-unknown/1.0")
    assert resolved.config_format == "v2ray"
    assert resolved.as_base64 is True
    assert resolved.source == "fallback"


def test_empty_user_agent_uses_fallback():
    assert resolve_client("").config_format == "v2ray"
    assert resolve_client(None).as_base64 is True


def test_version_gates_respect_minimum(custom_json_enabled):
    assert resolve_client("v2rayN/6.40").config_format == "v2ray-json"
    assert resolve_client("v2rayN/6.39").config_format == "v2ray"


def test_v2rayng_reversal_window(custom_json_enabled):
    modern = resolve_client("v2rayNG/1.8.29")
    assert modern.config_format == "v2ray-json"
    assert modern.reverse is False

    middle = resolve_client("v2rayNG/1.8.20")
    assert middle.config_format == "v2ray-json"
    assert middle.reverse is True

    legacy = resolve_client("v2rayNG/1.8.17")
    assert legacy.config_format == "v2ray"
    assert legacy.as_base64 is True


def test_custom_json_rules_are_skipped_when_flags_are_off(custom_json_disabled):
    assert resolve_client("v2rayN/6.40").config_format == "v2ray"
    assert resolve_client("Happ/1.12.0").config_format == "v2ray"
    assert resolve_client("ktor-client").config_format == "v2ray"


def test_custom_json_rules_apply_when_flags_are_on(custom_json_enabled):
    assert resolve_client("Happ/1.11.0").config_format == "v2ray-json"
    assert resolve_client("Streisand/1.0").config_format == "v2ray-json"
    assert resolve_client("ktor-client").config_format == "v2ray-json"


def test_database_rules_override_defaults():
    rules = [
        ClientRule(
            name="force-clash",
            pattern="^v2rayNG",
            config_format="clash-meta",
            priority=1,
            source="database",
        )
    ]
    resolved = resolve_client("v2rayNG/1.9.0", rules=rules)
    assert resolved.config_format == "clash-meta"
    assert resolved.source == "database"


def test_priority_decides_between_overlapping_rules():
    rules = [
        ClientRule(name="low", pattern="client", config_format="clash", priority=50),
        ClientRule(name="high", pattern="client", config_format="outline", priority=10),
    ]
    assert resolve_client("client/1.0", rules=rules).config_format == "outline"
    assert [rule.name for rule in sorted_rules(rules)] == ["high", "low"]


def test_version_gate_without_capture_group_never_matches():
    rule = ClientRule(
        name="broken", pattern="^app", config_format="clash", min_version="1.0"
    )
    assert rule.matches("app/2.0") is False


def test_resolve_format_for_explicit_requests():
    resolved = resolve_format("clash-meta")
    assert resolved.media_type == "text/yaml"
    assert resolved.as_base64 is False
    assert resolve_format("v2ray").as_base64 is True
    with pytest.raises(ValueError):
        resolve_format("nonsense")


def test_cache_round_trip_and_etag():
    cache.invalidate()
    cache.TTL = 60
    key = cache.build_key("user", "v2ray", True)
    assert cache.get(key) is None

    entry = cache.store(key, "payload")
    assert entry.etag == cache.etag_for("payload")
    assert cache.get(key).content == "payload"

    assert cache.etag_matches(entry.etag, entry.etag) is True
    assert cache.etag_matches(f"W/{entry.etag}", entry.etag) is True
    assert cache.etag_matches('"other", ' + entry.etag, entry.etag) is True
    assert cache.etag_matches("*", entry.etag) is True
    assert cache.etag_matches('"other"', entry.etag) is False
    assert cache.etag_matches(None, entry.etag) is False

    assert cache.invalidate("user") == 1
    assert cache.get(key) is None


def test_cache_disabled_still_returns_etag():
    cache.invalidate()
    cache.TTL = 0
    try:
        entry = cache.store("key", "payload")
        assert entry.etag
        assert cache.get("key") is None
        assert cache.size() == 0
    finally:
        cache.TTL = 60
