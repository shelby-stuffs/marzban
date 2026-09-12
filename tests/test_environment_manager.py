import tempfile,unittest,importlib.util
from pathlib import Path
SPEC=importlib.util.spec_from_file_location("env_manager",Path(__file__).resolve().parents[1]/"app/env_manager.py");MODULE=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(MODULE)
read_environment,update_environment=MODULE.read_environment,MODULE.update_environment
class EnvironmentManagerTests(unittest.TestCase):
 def test_atomic_update_preserves_comments_and_masks_secrets(self):
  with tempfile.TemporaryDirectory() as d:
   path=Path(d)/".env";path.write_text('# keep\nSINGBOX_HYSTERIA_ENABLED=false\nSUDO_PASSWORD=old-secret\n');update_environment(str(path),[{"key":"SINGBOX_HYSTERIA_ENABLED","value":"true"},{"key":"SUDO_PASSWORD","value":"new-secret"}]);text=path.read_text();self.assertIn('# keep',text);self.assertIn('SINGBOX_HYSTERIA_ENABLED="true"',text);self.assertTrue(Path(str(path)+'.bak').exists());entries={x['key']:x for x in read_environment(str(path))['entries']};self.assertIsNone(entries['SUDO_PASSWORD']['value']);self.assertTrue(entries['SUDO_PASSWORD']['configured'])
 def test_rejects_unknown_and_multiline_values(self):
  with tempfile.TemporaryDirectory() as d:
   path=str(Path(d)/'.env')
   with self.assertRaises(ValueError):update_environment(path,[{"key":"LD_PRELOAD","value":"evil"}])
   with self.assertRaises(ValueError):update_environment(path,[{"key":"SUB_PROFILE_TITLE","value":"a\nb"}])
 def test_frontend_is_sudo_only_and_registered(self):
  root=Path(__file__).resolve().parents[1];router=(root/'app/routers/environment.py').read_text();self.assertIn('Admin.check_sudo_admin',router);self.assertIn('environment.router',(root/'app/routers/__init__.py').read_text());self.assertIn('path: "environment"',(root/'app/dashboard/src/pages/Router.tsx').read_text())
if __name__=='__main__':unittest.main()
