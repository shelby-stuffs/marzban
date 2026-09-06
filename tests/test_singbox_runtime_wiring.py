from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SingBoxRuntimeWiringTests(unittest.TestCase):
 def test_docker_builds_stats_capable_singbox_from_upstream(self):
  source=(ROOT/"Dockerfile").read_text()
  self.assertIn("github.com/SagerNet/sing-box.git",source)
  self.assertIn("with_quic with_grpc with_v2ray_api",source)
  self.assertNotIn("SagerNet/sing-box/releases/download",source)
  self.assertNotIn("{{https://",source)

 def test_xray_runtime_skips_hysteria_users_and_inbounds(self):
  source=(ROOT/"app/xray/config.py").read_text()
  self.assertIn('proxy_type == "hysteria"',source)
  self.assertIn("strip_hysteria_from_xray(config)",source)

 def test_xray_grpc_skips_hysteria_accounts(self):
  source=(ROOT/"app/xray/operations.py").read_text()
  self.assertEqual(source.count('getattr(proxy_type, "value", proxy_type) == "hysteria"'),2)
  self.assertIn("_schedule_singbox_reload()",source)

 def test_feature_is_opt_in(self):
  source=(ROOT/"config.py").read_text()
  self.assertIn('SINGBOX_HYSTERIA_ENABLED = config("SINGBOX_HYSTERIA_ENABLED", cast=bool, default=False)',source)

if __name__=="__main__": unittest.main()
