import ast
from pathlib import Path
import runpy
import unittest

ROOT = Path(__file__).resolve().parents[1]
Client = runpy.run_path(str(ROOT / "app/subscription/hysteria2.py"))["Hysteria2Client"]

class Hysteria2CacheRegressionTests(unittest.TestCase):
    def profile(self, settings):
        return Client.from_mapping("edge.example", {
            "protocol":"hysteria", "network":"hysteria", "tls":"tls", "port":443,
            "obfs":"salamander", "obfs_password":"inbound-secret"
        }, settings)

    def test_user_password_can_override_while_mode_is_inherited(self):
        profile=self.profile({"auth":"user-auth", "obfs":"", "obfs_password":"user-secret"})
        self.assertEqual(profile.obfs, "salamander")
        self.assertEqual(profile.obfs_password, "user-secret")
        self.assertIn("user-secret", profile.share_link("node"))
        self.assertEqual(profile.singbox("node")["obfs"]["password"], "user-secret")
        self.assertEqual(profile.clash("node")["obfs-password"], "user-secret")
        self.assertEqual(profile.xray()["streamSettings"]["finalmask"]["udp"][0]["settings"]["password"], "user-secret")

    def test_empty_user_values_inherit_inbound(self):
        profile=self.profile({"auth":"user-auth", "obfs":"", "obfs_password":""})
        self.assertEqual(profile.obfs_password, "inbound-secret")

    def test_explicit_user_none_disables_obfs(self):
        profile=self.profile({"auth":"user-auth", "obfs":"none", "obfs_password":"stale"})
        self.assertEqual((profile.obfs, profile.obfs_password), ("", ""))

    def test_every_host_refresh_invalidates_subscription_cache_afterwards(self):
        files=("system.py","core.py","xhttp_inbound.py","wireguard_outbound.py","node.py")
        for name in files:
            with self.subTest(name=name):
                source=(ROOT/"app/routers"/name).read_text()
                self.assertIn("from app.subscription import cache as subscription_cache", source)
                tree=ast.parse(source)
                refresh=[]; invalidate=[]
                for node in ast.walk(tree):
                    if not isinstance(node, ast.Call): continue
                    text=ast.unparse(node.func)
                    if text == "xray.hosts.update": refresh.append(node.lineno)
                    if text == "subscription_cache.invalidate": invalidate.append(node.lineno)
                self.assertTrue(refresh, name)
                self.assertEqual(len(refresh), len(invalidate), name)
                self.assertTrue(all(r < i for r, i in zip(sorted(refresh), sorted(invalidate))), name)

if __name__ == "__main__": unittest.main()
