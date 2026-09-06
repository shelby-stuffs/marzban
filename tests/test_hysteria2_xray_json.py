"""Isolated generator regressions, runnable without starting the Marzban app.

Run: python -m unittest discover -s tests -p test_hysteria2_xray_json.py -v
The real generator class is compiled from its AST to avoid app/__init__.py
starting database/router/scheduler imports. This does NOT validate application
imports, template loading, or acceptance by the Xray binary.
"""
import ast
import copy
import json
from pathlib import Path
from random import choice
import unittest
from typing import Union


def load_generator():
    source = Path(__file__).resolve().parents[1] / "app/subscription/v2ray.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "V2rayJsonConfig")
    namespace = {"copy": copy, "json": json, "choice": choice, "Union": Union}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(source), "exec"), namespace)
    return namespace["V2rayJsonConfig"]


class HysteriaXrayJsonTests(unittest.TestCase):
    def setUp(self):
        cls = load_generator()
        self.config = str.__new__(cls)
        self.config.config = []
        self.config.settings = {}
        self.config.template = '{"outbounds": []}'
        self.config.mux_template = '{"v2ray": {"enabled": false}}'
        self.config.user_agent_list = []
        self.inbound = {
            "protocol": "hysteria", "network": "hysteria", "port": 443,
            "tls": "tls", "sni": "edge.example.com", "alpn": "h3",
            "ais": False, "host": "", "path": "", "header_type": "",
            "fragment_setting": "", "noise_setting": "",
            "obfs": "salamander", "obfs_password": "obfs-secret",
        }

    def generate(self, auth="user-secret", **overrides):
        inbound = dict(self.inbound, **overrides)
        self.config.add("Hysteria node", "203.0.113.10", inbound, {"auth": auth})
        return self.config.config[-1]["outbounds"][0]

    def test_protocol_settings_use_xray_shape(self):
        outbound = self.generate()
        self.assertEqual(outbound["protocol"], "hysteria")
        self.assertEqual(outbound["settings"], {"version": 2, "address": "203.0.113.10", "port": 443})

    def test_transport_contains_user_auth(self):
        stream = self.generate()["streamSettings"]
        self.assertEqual(stream["method"], "hysteria")
        self.assertEqual(stream["hysteriaSettings"]["version"], 2)
        self.assertEqual(stream["hysteriaSettings"]["auth"], "user-secret")

    def test_tls_sni_alpn_and_secure_default(self):
        stream = self.generate()["streamSettings"]
        self.assertEqual(stream["security"], "tls")
        self.assertEqual(stream["tlsSettings"]["serverName"], "edge.example.com")
        self.assertEqual(stream["tlsSettings"]["alpn"], ["h3"])
        self.assertIs(stream["tlsSettings"]["allowInsecure"], False)

    def test_explicit_insecure_setting_is_preserved(self):
        self.assertIs(self.generate(ais=True)["streamSettings"]["tlsSettings"]["allowInsecure"], True)

    def test_salamander_is_a_udp_finalmask(self):
        outbound = self.generate()
        self.assertEqual(outbound["streamSettings"]["finalmask"], {
            "udp": [{"type": "salamander", "settings": {"password": "obfs-secret"}}]
        })
        self.assertNotIn("obfs", outbound["settings"])
        self.assertNotIn("obfs-password", outbound["settings"])

    def test_no_obfs_omits_finalmask(self):
        self.assertNotIn("finalmask", self.generate(obfs="", obfs_password="")["streamSettings"])

    def test_template_auth_is_overridden_without_mutation(self):
        self.config.settings = {"hysteriaSettings": {"auth": "stale", "udpIdleTimeout": 90}}
        before = copy.deepcopy(self.config.settings)
        first = self.generate(auth="first")["streamSettings"]["hysteriaSettings"]
        second = self.generate(auth="second")["streamSettings"]["hysteriaSettings"]
        self.assertEqual(first["auth"], "first")
        self.assertEqual(second["auth"], "second")
        self.assertEqual(second["udpIdleTimeout"], 90)
        self.assertEqual(self.config.settings, before)

    def test_comma_separated_alpn(self):
        self.assertEqual(self.generate(alpn="h3,h2")["streamSettings"]["tlsSettings"]["alpn"], ["h3", "h2"])

    def test_ipv6_address_and_string_port(self):
        inbound = dict(self.inbound, port="8443")
        self.config.add("IPv6", "2001:db8::1", inbound, {"auth": "secret"})
        settings = self.config.config[-1]["outbounds"][0]["settings"]
        self.assertEqual(settings, {"version": 2, "address": "2001:db8::1", "port": 8443})

    def test_vless_raw_tls_remains_unchanged(self):
        inbound = dict(self.inbound, protocol="vless", network="raw")
        self.config.add("VLESS", "203.0.113.10", inbound, {"id": "test-id"})
        outbound = self.config.config[-1]["outbounds"][0]
        self.assertEqual(outbound["settings"]["vnext"][0]["users"][0]["id"], "test-id")
        self.assertEqual(outbound["streamSettings"]["method"], "raw")
        self.assertEqual(outbound["streamSettings"]["security"], "tls")
        self.assertNotIn("hysteriaSettings", outbound["streamSettings"])
        self.assertNotIn("finalmask", outbound["streamSettings"])

    def test_hysteria_does_not_emit_generic_mux(self):
        outbound = self.generate(mux_enable=True)
        self.assertNotIn("mux", outbound)

    def test_hysteria_fragment_does_not_add_unused_dialer(self):
        self.generate(fragment_setting="10-20,1-2,tlshello")
        self.assertEqual(len(self.config.config[-1]["outbounds"]), 1)

    def test_hysteria_noise_does_not_add_unused_dialer(self):
        self.generate(noise_setting="str:hello,1-2")
        self.assertEqual(len(self.config.config[-1]["outbounds"]), 1)

    def test_hysteria_does_not_parse_inapplicable_fragment(self):
        self.generate(fragment_setting="malformed-legacy-value")
        self.assertEqual(len(self.config.config[-1]["outbounds"]), 1)

    def test_hysteria_does_not_parse_inapplicable_noise(self):
        # Metadata fixtures bypass API validation deliberately: unused options
        # must not be processed by this protocol's exporter at all.
        self.generate(noise_setting=123)
        self.assertEqual(len(self.config.config[-1]["outbounds"]), 1)

    def test_hysteria_does_not_parse_generic_mux_template(self):
        self.config.mux_template = "not-json"
        self.assertNotIn("mux", self.generate(mux_enable=True))

    def test_hysteria_options_do_not_change_tls_auth_or_salamander(self):
        baseline = copy.deepcopy(self.generate())
        result = self.generate(mux_enable=True, fragment_setting="10-20,1-2,tlshello",
                               noise_setting="str:hello,1-2")
        self.assertEqual(result, baseline)
        self.assertEqual(len(self.config.config[-1]["outbounds"]), 1)
        self.assertNotIn("sockopt", result["streamSettings"])

    def test_vless_still_emits_generic_mux(self):
        inbound = dict(self.inbound, protocol="vless", network="raw", mux_enable=True)
        self.config.add("VLESS", "203.0.113.10", inbound, {"id": "test-id"})
        self.assertIs(self.config.config[-1]["outbounds"][0]["mux"]["enabled"], True)

    def test_vless_still_uses_fragment_noise_dialer(self):
        inbound = dict(self.inbound, protocol="vless", network="raw",
                       fragment_setting="10-20,1-2,tlshello", noise_setting="str:hello,1-2")
        self.config.add("VLESS", "203.0.113.10", inbound, {"id": "test-id"})
        outbounds = self.config.config[-1]["outbounds"]
        self.assertEqual(len(outbounds), 2)
        self.assertEqual(outbounds[0]["streamSettings"]["sockopt"]["dialerProxy"], "dialer")
        self.assertEqual(outbounds[1], {
            "tag": "dialer", "protocol": "freedom", "settings": {
                "fragment": {"length": "10-20", "interval": "1-2", "packets": "tlshello"},
                "noises": [{"type": "str", "packet": "hello", "delay": "1-2"}],
            },
        })


if __name__ == "__main__":
    unittest.main()
