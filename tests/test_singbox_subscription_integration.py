from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SingBoxSubscriptionIntegrationTests(unittest.TestCase):
 def test_share_pipeline_uses_managed_hysteria_endpoint(self):
  source=(ROOT/"app/subscription/share.py").read_text()
  self.assertIn('"subscription_host" in inbound', source)
  self.assertIn('subscription_hosts = [managed_host] if managed_host else []', source)

 def test_dashboard_exposes_public_endpoint_fields(self):
  source=(ROOT/"app/dashboard/src/pages/SingBoxSettings.tsx").read_text()
  for field in ("subscription_enabled","subscription_address","subscription_port","subscription_sni","subscription_insecure","subscription_remark"):
   self.assertIn(field,source)

 def test_locales_explain_tls_and_public_endpoint(self):
  for lang in ("en","ru","fa","zh"):
   data=json.loads((ROOT/f"app/dashboard/public/statics/locales/{lang}.json").read_text())
   for key in ("singbox.subscription","singbox.subscriptionAddress","singbox.subscriptionTlsHint"):
    self.assertTrue(data.get(key),(lang,key))

if __name__=="__main__": unittest.main()
