from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class GlamourPinkThemeTests(unittest.TestCase):
 def test_primary_palette_is_pink(self):
  theme=(ROOT/"app/dashboard/chakra.config.ts").read_text();css=(ROOT/"app/dashboard/src/theme/palettes.scss").read_text();self.assertIn('primary:palette("primary")',theme);self.assertIn("--theme-primary-500:#f653ad",css);self.assertIn('500:"var(--theme-accent-500)"',theme);self.assertIn('Manrope',theme);self.assertIn("--theme-primary-500:#00e08c",css)
 def test_background_has_airy_rose_blooms(self):
  css=(ROOT/"app/dashboard/src/theme/palettes.scss").read_text();self.assertIn("radial-gradient(circle at 12% 8%",css);self.assertIn("rgba(255,114,194",css);self.assertIn("body::before",css)
 def test_shared_panels_use_glass_surface(self):
  panel=(ROOT/"app/dashboard/src/components/Panel.tsx").read_text();self.assertIn('backdropFilter="blur(22px) saturate(135%)"',panel);self.assertIn('borderRadius="20px"',panel)
 def test_navigation_uses_soft_pink_active_state(self):
  sidebar=(ROOT/"app/dashboard/src/components/Sidebar.tsx").read_text();self.assertIn("var(--theme-active-gradient)",sidebar);self.assertIn("rgba(246,83,173,.20)",(ROOT/"app/dashboard/src/theme/palettes.scss").read_text());self.assertIn('borderRadius="14px"',sidebar)
 def test_technical_surfaces_are_preserved(self):
  viewer=(ROOT/"app/dashboard/src/components/AnsiLogViewer.tsx").read_text();editor=(ROOT/"app/dashboard/src/components/JsonEditor/index.tsx").read_text();self.assertIn("AnsiLogViewer",viewer);self.assertIn("<Editor",editor);self.assertIn('theme={`marzban-${theme}`}',editor);self.assertIn('"glamour-pink":',editor)
if __name__=="__main__":unittest.main()
