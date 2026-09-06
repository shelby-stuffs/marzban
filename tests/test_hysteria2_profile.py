"""Contract tests for the real, dependency-free Hysteria2 client profile."""
import copy
from pathlib import Path
import runpy
import unittest
from urllib.parse import parse_qs, unquote, urlsplit

MODULE = runpy.run_path(str(Path(__file__).resolve().parents[1] / "app/subscription/hysteria2.py"))
Client = MODULE["Hysteria2Client"]


class Hysteria2ProfileTests(unittest.TestCase):
    def profile(self, address="edge.example.com", settings=None, **changes):
        inbound = {"protocol": "hysteria", "network": "hysteria", "tls": "tls", "port": 443,
                   "sni": "edge.example.com", "alpn": "h3", "obfs": "salamander", "obfs_password": "server-secret"}
        inbound.update(changes)
        return Client.from_mapping(address, inbound, settings or {"auth": "user-secret"})

    def test_all_formats_share_auth_obfs_and_endpoint(self):
        p = self.profile()
        link = urlsplit(p.share_link("node")); query = parse_qs(link.query)
        xray, singbox, clash = p.xray(), p.singbox("node"), p.clash("node")
        self.assertEqual(unquote(link.username), xray["streamSettings"]["hysteriaSettings"]["auth"])
        self.assertEqual(singbox["password"], clash["password"])
        self.assertEqual(clash["password"], unquote(link.username))
        self.assertEqual(query["obfs-password"][0], singbox["obfs"]["password"])
        self.assertEqual(singbox["obfs"]["password"], clash["obfs-password"])
        self.assertEqual(clash["obfs-password"], xray["streamSettings"]["finalmask"]["udp"][0]["settings"]["password"])
        self.assertEqual(link.hostname, singbox["server"])
        self.assertEqual(link.port, clash["port"])
        self.assertEqual(clash["port"], xray["settings"]["port"])

    def test_special_characters_in_auth_and_remark_round_trip(self):
        auth = "имя:p@ss/?#% +"
        p = self.profile(settings={"auth": auth})
        link = urlsplit(p.share_link("Москва #1 / test"))
        self.assertEqual(unquote(link.username), auth)
        self.assertIsNone(link.password)
        self.assertEqual(unquote(link.fragment), "Москва #1 / test")
        self.assertEqual(p.clash("node")["password"], auth)

    def test_ipv6_is_bracketed_only_in_uri(self):
        for address in ("2001:db8::1", "[2001:db8::1]"):
            p = self.profile(address=address)
            self.assertEqual(urlsplit(p.share_link("node")).hostname, "2001:db8::1")
            self.assertEqual(p.xray()["settings"]["address"], "2001:db8::1")

    def test_false_string_never_disables_certificate_verification(self):
        for value in (False, "false", "False", "0", 0, None, ""):
            with self.subTest(value=value):
                p = self.profile(ais=value)
                self.assertFalse(p.insecure)
                self.assertNotIn("insecure", parse_qs(urlsplit(p.share_link("node")).query))
                self.assertNotIn("skip-cert-verify", p.clash("node"))
                self.assertFalse(p.xray()["streamSettings"]["tlsSettings"]["allowInsecure"])

    def test_true_is_explicit_and_consistent(self):
        for value in (True, "true", "1", 1):
            p = self.profile(ais=value)
            self.assertTrue(p.singbox("node")["tls"]["insecure"])
            self.assertTrue(p.clash("node")["skip-cert-verify"])

    def test_alpn_normalizes_lists_strings_and_duplicates(self):
        for value in ("h3, h2,h3,", ["h3", "h2", "h3", ""]):
            p = self.profile(alpn=value)
            self.assertEqual(p.alpn, ("h3", "h2"))
            self.assertEqual(p.singbox("node")["tls"]["alpn"], ["h3", "h2"])
            self.assertEqual(p.clash("node")["alpn"], ["h3", "h2"])

    def test_invalid_ports_are_rejected(self):
        for value in (0, 65536, -1, True, 443.5, "443,", "443-8443", "443,70000", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.profile(port=value)

    def test_port_pool_selects_one_valid_endpoint(self):
        for _ in range(10):
            p = self.profile(port="443, 8443")
            self.assertIn(p.port, (443, 8443))
            self.assertEqual(urlsplit(p.share_link("node")).port, p.xray()["settings"]["port"])

    def test_invalid_auth_is_rejected_without_echoing_secret(self):
        for auth in (None, "", 123, {}):
            with self.subTest(auth=auth), self.assertRaises(ValueError):
                self.profile(settings={"auth": auth})

    def test_invalid_tls_network_and_version_are_rejected(self):
        for fields in ({"tls": "none"}, {"tls": "reality"}, {"network": "raw"},
                       {"hysteria_version": 1}, {"hysteria_version": True}, {"protocol": "vless"}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.profile(**fields)

    def test_invalid_obfs_is_rejected(self):
        for fields in ({"obfs": "sudoku"}, {"obfs_password": ""}, {"obfs_password": 123}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                self.profile(**fields)

    def test_user_password_override_is_preserved_for_compatibility(self):
        p = self.profile(settings={"auth": "user-secret", "obfs": "salamander", "obfs_password": "user-secret-obfs"})
        self.assertEqual(p.obfs_password, "user-secret-obfs")

    def test_explicit_user_none_suppresses_inherited_obfs(self):
        p = self.profile(settings={"auth": "user-secret", "obfs": "none", "obfs_password": "stale"})
        self.assertNotIn("finalmask", p.xray()["streamSettings"])
        self.assertNotIn("obfs", p.clash("node"))
        self.assertNotIn("obfs", p.singbox("node"))
        self.assertNotIn("obfs", parse_qs(urlsplit(p.share_link("node")).query))

    def test_legacy_obfs_fallback_only_without_canonical_keys(self):
        p = Client.from_mapping("edge.example.com", {"port": 443},
                               {"auth": "secret", "obfs": "salamander", "obfs_password": "legacy"})
        self.assertEqual(p.obfs_password, "legacy")

    def test_templates_and_input_are_not_mutated(self):
        template = {"auth": "stale", "obfs": "old", "obfsPassword": "old", "udpIdleTimeout": 90}
        before = copy.deepcopy(template)
        output = self.profile().xray(template)
        self.assertEqual(template, before)
        transport = output["streamSettings"]["hysteriaSettings"]
        self.assertEqual(transport["auth"], "user-secret")
        self.assertEqual(transport["udpIdleTimeout"], 90)
        self.assertNotIn("obfs", transport)
        self.assertNotIn("obfsPassword", transport)

    def test_credentials_are_not_in_profile_repr(self):
        result = repr(self.profile())
        self.assertNotIn("user-secret", result)
        self.assertNotIn("server-secret", result)

    def test_url_in_place_of_address_is_rejected(self):
        for address in ("https://example.com", "a@b", "bad host", "example.com:443", ""):
            with self.subTest(address=address), self.assertRaises(ValueError):
                self.profile(address=address)


if __name__ == "__main__":
    unittest.main()
