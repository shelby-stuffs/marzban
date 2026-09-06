from pathlib import Path
import json
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SingBoxSubscriptionTabTests(unittest.TestCase):
 def test_subscription_has_dedicated_fourth_section(self):
  ui=(ROOT/"app/dashboard/src/pages/SingBoxSettings.tsx").read_text()
  self.assertEqual(ui.count('<Tab whiteSpace="nowrap">'),4)
  self.assertIn('t("singbox.tabSubscription")',ui)
  inbound=ui.index('t("singbox.tabInbound")'); subscription=ui.index('t("singbox.tabSubscription")'); rules=ui.index('t("singbox.tabRuleSets")')
  self.assertLess(inbound,subscription); self.assertLess(subscription,rules)
  self.assertEqual(ui.count('<Panel label={t("singbox.subscription")}>'),1)

 def test_all_locales_have_subscription_tab_copy(self):
  for lang in ("en","ru","fa","zh"):
   data=json.loads((ROOT/f"app/dashboard/public/statics/locales/{lang}.json").read_text())
   self.assertIn("singbox.tabSubscription",data); self.assertIn("singbox.subscriptionFormatsHelp",data)

if __name__=="__main__": unittest.main()
