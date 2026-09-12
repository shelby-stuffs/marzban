from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class ModernSaasDesignTests(unittest.TestCase):
 def read(self,path):return (ROOT/path).read_text()
 def test_collapsible_sidebar_is_persisted(self):
  layout=self.read("app/dashboard/src/pages/Layout.tsx");sidebar=self.read("app/dashboard/src/components/Sidebar.tsx");self.assertIn("marzban-sidebar-collapsed",layout);self.assertIn('collapsed={collapsed}',layout);self.assertIn('transition="width .22s ease"',sidebar)
 def test_shared_surfaces_use_theme_tokens(self):
  for path in ("app/dashboard/src/components/Panel.tsx","app/dashboard/src/components/Filters.tsx","app/dashboard/src/components/Sidebar.tsx"):
   source=self.read(path);self.assertIn("--theme-",source);self.assertNotIn("#f653ad",source)
 def test_global_redesign_preserves_runtime_themes(self):
  index=self.read("app/dashboard/src/index.tsx");css=self.read("app/dashboard/src/theme/redesign.scss");themes=self.read("app/dashboard/src/theme/themes.ts");self.assertIn('theme/redesign.scss',index);self.assertIn("#users-table",css)
  for theme in ("terminal-green","glamour-pink","cyber-violet","airy-light"):self.assertIn(theme,themes)
 def test_technical_surfaces_remain_separate(self):
  editor=self.read("app/dashboard/src/components/JsonEditor/index.tsx");logs=self.read("app/dashboard/src/components/AnsiLogViewer.tsx");self.assertIn('marzban-${theme}',editor);self.assertIn("AnsiLogViewer",logs)
if __name__=='__main__':unittest.main()
