from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]

class SingBoxDashboardLogsTests(unittest.TestCase):
 def test_new_and_legacy_api_routes_are_registered(self):
  source=(ROOT/"app/routers/hysteria2.py").read_text()
  self.assertIn('prefix="/api/singbox"', source)
  self.assertIn('@singbox_router.get("/logs")', source)
  self.assertIn('@singbox_router.delete("/logs")', source)
  routers=(ROOT/"app/routers/__init__.py").read_text()
  self.assertIn('hysteria2.singbox_router', routers)

 def test_dashboard_uses_singbox_route_and_keeps_redirect(self):
  router=(ROOT/"app/dashboard/src/pages/Router.tsx").read_text()
  sidebar=(ROOT/"app/dashboard/src/components/Sidebar.tsx").read_text()
  self.assertIn('path: "singbox"', router)
  self.assertIn('Navigate to="/singbox"', router)
  self.assertIn('to="/singbox"', sidebar)
  self.assertIn('singbox.title', sidebar)

 def test_logs_are_rendered_and_refreshed(self):
  source=(ROOT/"app/dashboard/src/pages/SingBoxSettings.tsx").read_text()
  self.assertIn('/singbox/logs?limit=500', source)
  self.assertIn('window.setInterval', source)
  self.assertIn('<AnsiLogViewer', source)
  self.assertIn('logs={logsMeta?.logs || []}', source)
  self.assertIn('method: "DELETE"', source)

 def test_locales_contain_singbox_copy(self):
  for lang in ("en","ru","fa","zh"):
   data=json.loads((ROOT/f"app/dashboard/public/statics/locales/{lang}.json").read_text())
   for key in ("singbox.title","singbox.logs","singbox.hysteriaInbound","singbox.clearLogs"):
    self.assertTrue(data.get(key), (lang,key))

if __name__ == "__main__": unittest.main()
