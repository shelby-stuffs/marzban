"""Isolated inbound -> subscription regressions (no app startup or Xray binary).

Run: python -m unittest discover -s tests -p test_hysteria2_inbound.py -v
Run test_hysteria2_xray_json.py separately for the preceding patch's tests.
Real classes/functions are extracted via AST. Templates, enum and runtime
context are minimal fixtures; this is not an API/DB/network integration test.
"""
import ast
import runpy
import base64
import copy
import json
from pathlib import Path, PosixPath
import random
import secrets
from types import SimpleNamespace
from typing import Union
import unittest
import urllib.parse as urlparse
from uuid import UUID
from enum import Enum

ROOT = Path(__file__).resolve().parents[1]


def load_definitions(relative, names, namespace=None):
    source = ROOT / relative
    tree = ast.parse(source.read_text(encoding="utf-8"))
    nodes = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.ClassDef)) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, *nodes], type_ignores=[]))
    env = {"Hysteria2Client": runpy.run_path(str(ROOT / "app/subscription/hysteria2.py"))["Hysteria2Client"], "json": json, "copy": copy, "deepcopy": copy.deepcopy,
           "PosixPath": PosixPath, "Union": Union, "choice": random.choice,
           "urlparse": urlparse, "quote": urlparse.quote, "base64": base64, "UUID": UUID}
    env["resolve_hysteria2_host"] = runpy.run_path(str(ROOT / "app/utils/hysteria2_validation.py"))["resolve_hysteria2_host"]
    env.update(namespace or {})
    exec(compile(module, str(source), "exec"), env)
    return env


class Protocol(str, Enum):
    Hysteria2 = "hysteria"
    VLESS = "vless"


def make_stream(**overrides):
    stream = {
        "method": "hysteria", "security": "tls", "tlsSettings": {},
        "hysteriaSettings": {"version": 2},
        "finalmask": {"udp": [{"type": "salamander", "settings": {"password": "server-secret"}}]},
    }
    stream.update(overrides)
    return stream


def make_config(stream):
    env = load_definitions("app/xray/config.py", ["merge_dicts", "normalize_xray_v26_config", "XRayConfig"], {
        "ProxyTypes": Protocol, "XRAY_EXCLUDE_INBOUND_TAGS": [], "XRAY_FALLBACKS_INBOUND_TAG": "",
    })
    source = {"inbounds": [{"tag": "hy2", "protocol": "hysteria", "port": 443,
                            "settings": {"version": 2}, "streamSettings": stream}],
              "outbounds": [{"tag": "direct", "protocol": "freedom"}]}
    before = copy.deepcopy(source)
    config = env["XRayConfig"](source)
    assert source == before, "XRayConfig mutated caller's data"
    return config


class HysteriaInboundTests(unittest.TestCase):
    def metadata(self, stream):
        return make_config(stream).inbounds_by_tag["hy2"]

    def test_reads_salamander_from_finalmask(self):
        meta = self.metadata(make_stream())
        self.assertEqual((meta["obfs"], meta["obfs_password"]), ("salamander", "server-secret"))
        self.assertEqual(meta["network"], "hysteria")
        self.assertEqual(meta["tls"], "tls")

    def test_network_alias_still_works(self):
        stream = make_stream()
        stream["network"] = stream.pop("method")
        self.assertEqual(self.metadata(stream)["obfs_password"], "server-secret")

    def test_finalmask_overrides_legacy_password(self):
        meta = self.metadata(make_stream(hysteriaSettings={"version": 2, "obfs": "salamander", "obfsPassword": "stale"}))
        self.assertEqual(meta["obfs_password"], "server-secret")

    def test_explicit_empty_finalmask_does_not_revive_legacy_obfs(self):
        meta = self.metadata(make_stream(finalmask={"udp": []}, hysteriaSettings={"version": 2, "obfs": "salamander", "obfsPassword": "stale"}))
        self.assertEqual((meta["obfs"], meta["obfs_password"]), ("", ""))

    def test_legacy_fields_work_only_without_finalmask(self):
        stream = make_stream(hysteriaSettings={"version": 2, "obfs": "salamander", "obfsPassword": "legacy"})
        del stream["finalmask"]
        meta = self.metadata(stream)
        self.assertEqual((meta["obfs"], meta["obfs_password"]), ("salamander", "legacy"))

    def test_absent_obfs_stays_empty(self):
        stream = make_stream()
        del stream["finalmask"]
        meta = self.metadata(stream)
        self.assertEqual((meta["obfs"], meta["obfs_password"]), ("", ""))

    def test_tcp_masks_are_not_mistaken_for_udp(self):
        meta = self.metadata(make_stream(finalmask={"tcp": [{"type": "salamander", "settings": {"password": "tcp-secret"}}]}))
        self.assertEqual(meta["obfs_password"], "")

    def test_unrelated_udp_mask_is_not_exported_as_salamander(self):
        meta = self.metadata(make_stream(finalmask={"udp": [{"type": "header-custom", "settings": {}}]}))
        self.assertEqual(meta["obfs"], "")

    def test_malformed_values_do_not_crash_metadata_extraction(self):
        cases = [None, [], "invalid", {"udp": None}, {"udp": {}}, {"udp": [None, 1]},
                 {"udp": [{"type": "salamander", "settings": None}]},
                 {"udp": [{"type": "salamander", "settings": {"password": 123}}]}]
        for finalmask in cases:
            with self.subTest(finalmask=finalmask):
                meta = self.metadata(make_stream(finalmask=finalmask))
                self.assertEqual((meta["obfs"], meta["obfs_password"]), ("", ""))

    def test_does_not_mutate_finalmask(self):
        stream = make_stream()
        before = copy.deepcopy(stream)
        config = make_config(stream)
        self.assertEqual(stream, before)
        self.assertEqual(config.get_inbound("hy2")["streamSettings"]["finalmask"], before["finalmask"])

    def subscription(self, conf, host_overrides=None):
        config = make_config(make_stream())
        host = {
            "sni": ["edge.example.com"], "host": [], "address": ["203.0.113.10"],
            "path": None, "port": None, "tls": None, "alpn": "h3", "fingerprint": None,
            "allowinsecure": False, "mux_enable": False, "fragment_setting": "",
            "noise_setting": "", "random_user_agent": False, "remark": "Hysteria node",
        }
        host.update(host_overrides or {})
        env = load_definitions("app/subscription/share.py", ["process_inbounds_and_tags"], {
            "xray": SimpleNamespace(config=config, hosts={"hy2": [host]}),
            "random": random, "secrets": secrets,
        })
        env["process_inbounds_and_tags"](
            proxies={Protocol.Hysteria2: SimpleNamespace(model_dump=lambda: {"auth": "user-secret"})},
            inbounds={Protocol.Hysteria2: ["hy2"]}, format_variables={}, conf=conf,
        )
        return conf

    def link_generator(self):
        cls = load_definitions("app/subscription/v2ray.py", ["V2rayShareLink"], {"EXTERNAL_CONFIG": ""})["V2rayShareLink"]
        return cls()

    def test_full_metadata_host_merge_to_share_link(self):
        conf = self.subscription(self.link_generator())
        parsed = urlparse.urlsplit(conf.links[0])
        query = urlparse.parse_qs(parsed.query)
        self.assertEqual(parsed.username, "user-secret")
        self.assertEqual(query["obfs"], ["salamander"])
        self.assertEqual(query["obfs-password"], ["server-secret"])
        self.assertEqual(json.loads(query["fm"][0])["udp"][0]["settings"]["password"], "server-secret")

    def test_host_password_override_retains_precedence(self):
        conf = self.subscription(self.link_generator(), {"obfs_password": "host-secret"})
        query = urlparse.parse_qs(urlparse.urlsplit(conf.links[0]).query)
        self.assertEqual(query["obfs-password"], ["host-secret"])

    def test_metadata_to_xray_json(self):
        cls = load_definitions("app/subscription/v2ray.py", ["V2rayJsonConfig"], {"UUIDEncoder": json.JSONEncoder})["V2rayJsonConfig"]
        conf = str.__new__(cls)
        conf.config, conf.settings = [], {}
        conf.template, conf.mux_template = '{"outbounds": []}', '{"v2ray": {}}'
        self.subscription(conf)
        stream = conf.config[0]["outbounds"][0]["streamSettings"]
        self.assertEqual(stream["finalmask"]["udp"][0]["settings"]["password"], "server-secret")
        self.assertEqual(stream["hysteriaSettings"]["auth"], "user-secret")

    def test_metadata_to_singbox(self):
        cls = load_definitions("app/subscription/singbox.py", ["SingBoxConfiguration"], {"UUIDEncoder": json.JSONEncoder})["SingBoxConfiguration"]
        conf = str.__new__(cls)
        conf.config, conf.proxy_remarks = {"outbounds": []}, []
        self.subscription(conf)
        self.assertEqual(conf.config["outbounds"][0]["obfs"], {"type": "salamander", "password": "server-secret"})


if __name__ == "__main__":
    unittest.main()
