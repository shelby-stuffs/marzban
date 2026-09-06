from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path); module=importlib.util.module_from_spec(spec); sys.modules[name]=module; spec.loader.exec_module(module); return module

rules=load("singbox_rulesets_test","app/singbox/rulesets.py")

class SingBoxRuleSetTests(unittest.TestCase):
 def test_remote_ruleset_is_merged_before_custom_rules(self):
  settings=rules.RuleSetsSettings(items=[rules.RuleSetItem(tag="private",url="https://example.com/private.srs",outbound="block")])
  result=rules.merge_rule_sets({"route":{"rules":[{"action":"route","outbound":"direct"}]}},settings)
  self.assertEqual(result["route"]["rule_set"][0]["tag"],"private")
  self.assertEqual(result["route"]["rules"][0]["rule_set"],["private"])
  self.assertEqual(result["route"]["rules"][0]["action"],"route")
  self.assertTrue(result["experimental"]["cache_file"]["enabled"])

 def test_local_rule_set_requires_path(self):
  with self.assertRaises(ValueError): rules.RuleSetItem(tag="local",type="local")

 def test_remote_rule_set_requires_http_url(self):
  with self.assertRaises(ValueError): rules.RuleSetItem(tag="bad",url="file:///tmp/a.srs")

 def test_duplicate_tags_are_rejected(self):
  with self.assertRaises(ValueError): rules.RuleSetsSettings(items=[rules.RuleSetItem(tag="x",url="https://a.example/x.srs"),rules.RuleSetItem(tag="x",url="https://b.example/x.srs")])

 def test_advanced_json_tag_collision_is_rejected(self):
  settings=rules.RuleSetsSettings(items=[rules.RuleSetItem(tag="x",url="https://a.example/x.srs")])
  with self.assertRaisesRegex(ValueError,"advanced JSON"): rules.merge_rule_sets({"route":{"rule_set":[{"tag":"x","type":"local","path":"x.srs"}]}},settings)

 def test_atomic_round_trip(self):
  with tempfile.TemporaryDirectory() as directory:
   path=str(Path(directory)/"rules.json"); value=rules.RuleSetsSettings(items=[rules.RuleSetItem(tag="x",url="https://a.example/x.srs")])
   rules.save_rule_sets(path,value); loaded,persisted=rules.load_rule_sets(path)
   self.assertTrue(persisted); self.assertEqual(loaded,value)

 def test_tabs_and_api_are_wired(self):
  ui=(ROOT/"app/dashboard/src/pages/SingBoxSettings.tsx").read_text(); router=(ROOT/"app/routers/hysteria2.py").read_text(); runtime=(ROOT/"app/singbox/runtime.py").read_text()
  self.assertEqual(ui.count('<Tab whiteSpace="nowrap">'),4); self.assertIn('/singbox/rule-sets/reload',ui)
  self.assertIn('@singbox_router.put("/rule-sets")',router); self.assertIn('@singbox_router.post("/rule-sets/reload")',router)
  self.assertIn('merge_rule_sets(combined, rule_sets)',runtime)

if __name__=="__main__": unittest.main()
