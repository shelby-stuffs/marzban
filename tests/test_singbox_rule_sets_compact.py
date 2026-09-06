from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class CompactRuleSetsTests(unittest.TestCase):
 def test_rule_set_cards_use_compact_controls(self):
  ui=(ROOT/"app/dashboard/src/pages/SingBoxSettings.tsx").read_text()
  section=ui[ui.index('{ruleSetsLoading ?'):ui.index('</VStack>}',ui.index('{ruleSetsLoading ?'))]
  self.assertIn('<Panel compact label={t("singbox.ruleSetCache")}>',section)
  self.assertIn('<Panel key={index} compact label=',section)
  self.assertGreaterEqual(section.count('size="sm"'),10)
  self.assertIn('spacing="2.5"',section)
  self.assertIn('fontSize="10px"',section)
  self.assertNotIn('key={`${item.tag}-${index}`}',section)

 def test_compact_panel_is_opt_in(self):
  panel=(ROOT/"app/dashboard/src/components/Panel.tsx").read_text()
  self.assertIn('compact?: boolean',panel)
  self.assertIn('compact = false',panel)
  self.assertIn('p={compact ? "3"',panel)
  self.assertIn('py={compact ? "1.5"',panel)

if __name__=="__main__": unittest.main()
