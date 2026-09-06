from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]

class Hysteria2UserPasswordUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "app/dashboard/src/components/UserDialog.tsx").read_text()

    def test_user_password_is_visible_and_editable(self):
        self.assertIn('form.register("proxies.hysteria.auth"', self.source)
        self.assertIn('generateHysteriaPassword()', self.source)
        self.assertIn('shouldDirty: true, shouldValidate: true', self.source)

    def test_user_dialog_keeps_legacy_user_salamander_override(self):
        dialog = self.source[self.source.index('in={(selectedProxies || []).includes("hysteria")}'):]
        dialog = dialog[:dialog.index("</Collapse>")]
        self.assertIn('proxies.hysteria.obfs', dialog)
        self.assertIn('proxies.hysteria.obfs_password', dialog)
        self.assertIn('value="none"', dialog)

    def test_default_new_user_gets_individual_password(self):
        self.assertIn('auth: generateHysteriaPassword()', self.source)

    def test_all_locales_have_password_copy(self):
        for lang in ("en", "ru", "fa", "zh"):
            data = json.loads((ROOT / f"app/dashboard/public/statics/locales/{lang}.json").read_text())
            for key in ("userDialog.hysteriaPassword", "userDialog.generatePassword",
                        "userDialog.hysteriaPasswordRequired", "userDialog.hysteriaPasswordHelp"):
                self.assertTrue(data.get(key), (lang, key))

if __name__ == "__main__": unittest.main()
