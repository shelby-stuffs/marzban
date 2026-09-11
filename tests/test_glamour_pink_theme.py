from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class GlamourPinkThemeTests(unittest.TestCase):
    def test_primary_palette_is_pink(self):
        theme = (ROOT / "app/dashboard/chakra.config.ts").read_text()
        self.assertIn('500: "#f653ad"', theme)
        self.assertIn('500: "#bd91ff"', theme)
        self.assertIn('Manrope', theme)
        self.assertNotIn('500: "#00e08c"', theme)

    def test_background_has_airy_rose_blooms(self):
        css = (ROOT / "app/dashboard/src/index.scss").read_text()
        self.assertIn("radial-gradient(circle at 12% 8%", css)
        self.assertIn("rgba(255, 114, 194", css)
        self.assertIn("body::before", css)

    def test_shared_panels_use_glass_surface(self):
        panel = (ROOT / "app/dashboard/src/components/Panel.tsx").read_text()
        self.assertIn('backdropFilter="blur(18px) saturate(130%)"', panel)
        self.assertIn('borderRadius="16px"', panel)

    def test_navigation_uses_soft_pink_active_state(self):
        sidebar = (ROOT / "app/dashboard/src/components/Sidebar.tsx").read_text()
        self.assertIn("rgba(246,83,173,.20)", sidebar)
        self.assertIn('borderRadius="12px"', sidebar)

    def test_technical_surfaces_are_preserved(self):
        viewer = (ROOT / "app/dashboard/src/components/AnsiLogViewer.tsx").read_text()
        editor = (ROOT / "app/dashboard/src/components/JsonEditor/index.tsx").read_text()
        self.assertIn("AnsiLogViewer", viewer)
        self.assertIn("<Editor", editor)
        self.assertIn('theme="marzban-terminal"', editor)


if __name__ == "__main__":
    unittest.main()
