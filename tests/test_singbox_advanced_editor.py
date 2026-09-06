from pathlib import Path
import importlib.util
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

def load(name,path):
 spec=importlib.util.spec_from_file_location(name,ROOT/path); module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

advanced=load("singbox_advanced","app/singbox/advanced.py")
config=load("singbox_config_advanced","app/singbox/config.py")

class SingBoxAdvancedEditorTests(unittest.TestCase):
 def test_default_has_direct_outbound_and_route(self):
  value,persisted=advanced.load_advanced_config("/definitely/missing/config.json")
  self.assertFalse(persisted); self.assertEqual(value["route"]["final"],"direct")

 def test_managed_inbounds_are_reserved(self):
  with self.assertRaisesRegex(ValueError,"inbounds"):
   advanced.validate_advanced_config({"inbounds":[]})

 def test_duplicate_outbound_tags_are_rejected(self):
  with self.assertRaisesRegex(ValueError,"Duplicate"):
   advanced.validate_advanced_config({"outbounds":[{"type":"direct","tag":"x"},{"type":"block","tag":"x"}]})

 def test_merge_replaces_outbounds_and_route_but_preserves_inbounds(self):
  managed={"inbounds":[{"type":"hysteria2","tag":"hy2"}],"outbounds":[{"type":"direct","tag":"direct"}],"route":{"final":"direct"}}
  custom={"outbounds":[{"type":"block","tag":"blocked"}],"route":{"rules":[{"outbound":"blocked"}],"final":"blocked"}}
  result=config.merge_advanced_config(managed,custom)
  self.assertEqual(result["inbounds"],managed["inbounds"]); self.assertEqual(result["outbounds"],custom["outbounds"]); self.assertEqual(result["route"],custom["route"])

 def test_atomic_save_and_load(self):
  with tempfile.TemporaryDirectory() as directory:
   path=str(Path(directory)/"advanced.json"); value={"dns":{"servers":[]},"outbounds":[{"type":"direct","tag":"direct"}]}
   advanced.save_advanced_config(path,value); loaded,persisted=advanced.load_advanced_config(path)
   self.assertTrue(persisted); self.assertEqual(loaded,value); self.assertEqual(list(Path(directory).glob("*.tmp")),[])

 def test_api_and_dashboard_wiring(self):
  router=(ROOT/"app/routers/hysteria2.py").read_text(); runtime=(ROOT/"app/singbox/runtime.py").read_text(); ui=(ROOT/"app/dashboard/src/pages/SingBoxSettings.tsx").read_text()
  self.assertIn('@singbox_router.put("/advanced-config")',router); self.assertIn('@singbox_router.post("/advanced-config/check")',router)
  self.assertIn('current_advanced_config',runtime); self.assertIn('<JsonEditor',ui); self.assertIn('/singbox/advanced-config/check',ui)

if __name__=="__main__": unittest.main()
