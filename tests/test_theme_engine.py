import ast,pathlib,unittest
ROOT=pathlib.Path(__file__).resolve().parents[1]
class ThemeEngineTests(unittest.TestCase):
 def read(self,path):return (ROOT/path).read_text()
 def test_four_themes_and_account_api_exist(self):
  themes=self.read("app/dashboard/src/theme/themes.ts")
  for theme in ("terminal-green","glamour-pink","cyber-violet","airy-light"):self.assertIn(theme,themes)
  router=self.read("app/routers/admin.py");self.assertIn('/admin/preferences',router);self.assertIn('Admin.get_current',router)
 def test_migration_extends_current_head(self):
  tree=ast.parse(self.read("app/db/migrations/versions/themecomb001_add_admin_preferences.py"));values={}
  for node in tree.body:
   if isinstance(node,ast.Assign):
    for target in node.targets:
     if isinstance(target,ast.Name) and target.id in {"revision","down_revision"}:values[target.id]=ast.literal_eval(node.value)
  self.assertEqual(values,{"revision":"themecomb001","down_revision":"subsys001"})
 def test_theme_is_runtime_and_account_scoped(self):
  context=self.read("app/dashboard/src/contexts/ThemeContext.tsx");self.assertIn('method: "PUT"',context);self.assertIn('document.documentElement.dataset.theme',context);self.assertIn('syncAccountTheme',context)
  css=self.read("app/dashboard/src/theme/palettes.scss");self.assertIn(':root[data-theme="airy-light"]',css);self.assertIn('--theme-background:',css)
 def test_settings_route_and_monaco_variants(self):
  self.assertIn('path: "settings"',self.read("app/dashboard/src/pages/Router.tsx"));editor=self.read("app/dashboard/src/components/JsonEditor/index.tsx");self.assertIn('theme={`marzban-${theme}`}',editor);self.assertIn('"airy-light":',editor)
if __name__=="__main__":unittest.main()
