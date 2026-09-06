from pathlib import Path
import importlib.util
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("singbox_ip_rulesets_test",ROOT/"app/singbox/rulesets.py"); rules=importlib.util.module_from_spec(spec); sys.modules[spec.name]=rules; spec.loader.exec_module(rules)

class SingBoxIpRuleSetTests(unittest.TestCase):
 def test_plain_ipv4_and_ipv6_are_normalized(self):
  item=rules.RuleSetItem(tag="ips",type="inline",ip_cidr=["1.1.1.1","2001:db8::1","10.2.3.4/8"] )
  self.assertEqual(item.ip_cidr,["1.1.1.1/32","2001:db8::1/128","10.0.0.0/8"])

 def test_invalid_ip_is_rejected(self):
  with self.assertRaisesRegex(ValueError,"invalid IP/CIDR"): rules.RuleSetItem(tag="bad",type="inline",ip_cidr=["999.1.1.1"] )

 def test_empty_inline_set_is_rejected(self):
  with self.assertRaisesRegex(ValueError,"at least one"): rules.RuleSetItem(tag="empty",type="inline")

 def test_inline_definition_and_source_match_route(self):
  item=rules.RuleSetItem(tag="private",type="inline",ip_cidr=["10.0.0.0/8"],outbound="block",ip_cidr_match_source=True)
  result=rules.merge_rule_sets({"route":{"rules":[]}},rules.RuleSetsSettings(cache_enabled=False,items=[item]))
  definition=result["route"]["rule_set"][0]
  self.assertEqual(definition,{"type":"inline","tag":"private","rules":[{"ip_cidr":["10.0.0.0/8"]}]})
  self.assertTrue(result["route"]["rules"][0]["rule_set_ip_cidr_match_source"])

 def test_frontend_exposes_inline_ip_editor(self):
  ui=(ROOT/"app/dashboard/src/pages/SingBoxSettings.tsx").read_text()
  self.assertIn('"remote" | "local" | "inline"',ui); self.assertIn('item.ip_cidr.join("\\n")',ui)
  self.assertIn('addRuleSet("inline")',ui); self.assertIn('ruleSetIpCidrsHelp',ui)

if __name__=="__main__": unittest.main()
