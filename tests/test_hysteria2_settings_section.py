from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]

class Hysteria2SettingsSectionTests(unittest.TestCase):
 def test_backend_route_is_registered(self):
  routers=(ROOT/"app/routers/__init__.py").read_text()
  self.assertIn("hysteria2.router",routers)
  source=(ROOT/"app/routers/hysteria2.py").read_text()
  for path in ('@router.get("")','@router.put("")','@router.post("/generate")','@router.get("/runtime-config")'):
   self.assertIn(path,source)

 def test_dashboard_has_dedicated_route_and_sidebar_item(self):
  router=(ROOT/"app/dashboard/src/pages/Router.tsx").read_text()
  sidebar=(ROOT/"app/dashboard/src/components/Sidebar.tsx").read_text()
  self.assertIn('path: "singbox"',router)
  self.assertIn('path: "hysteria2"',router)
  self.assertIn('to="/singbox"',sidebar)

 def test_form_contains_certificate_and_server_fields(self):
  source=(ROOT/"app/dashboard/src/pages/SingBoxSettings.tsx").read_text()
  for field in ("certificate_path","key_path","listen_port","obfs_password","masquerade","ignore_client_bandwidth"):
   self.assertIn(field,source)
  self.assertIn('/singbox/runtime-config',source)

 def test_locales_have_section_copy(self):
  for lang in ("en","ru","fa","zh"):
   data=json.loads((ROOT/f"app/dashboard/public/statics/locales/{lang}.json").read_text())
   for key in ("hysteria.title","hysteria.certificatePath","hysteria.keyPath","hysteria.save"):
    self.assertTrue(data.get(key),(lang,key))

if __name__=="__main__": unittest.main()
