from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class DashboardTerminalPolishTests(unittest.TestCase):
    def test_status_filter_is_visible_and_uses_status_value(self):
        source=(ROOT/"app/dashboard/src/components/UsersTable.tsx").read_text()
        self.assertIn('value={filters.status || ""}', source)
        self.assertNotIn('left={"-40px"}', source)
        self.assertNotIn('value={filters.sort}', source)
        self.assertIn('overflowX="auto"', source)

    def test_charts_have_bounded_height(self):
        nodes=(ROOT/"app/dashboard/src/components/NodesUsage.tsx").read_text()
        user=(ROOT/"app/dashboard/src/components/UserDialog.tsx").read_text()
        self.assertIn('height={320}', nodes)
        self.assertNotIn('height="500px"', nodes)
        self.assertIn('height={280}', user)

    def test_subscription_templates_share_dashboard_font(self):
        for name in ("index.html", "index_modern.html"):
            source=(ROOT/"app/templates/subscription"/name).read_text()
            self.assertIn('JetBrains+Mono', source)
            self.assertIn('"JetBrains Mono", "SFMono-Regular", Menlo, Consolas', source)

if __name__ == "__main__": unittest.main()
