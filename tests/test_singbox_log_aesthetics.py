from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class SingBoxLogAestheticsTests(unittest.TestCase):
 def test_json_editor_is_before_logs(self):
  ui=(ROOT/"app/dashboard/src/pages/SingBoxSettings.tsx").read_text()
  editor=ui.index('<Panel label={t("singbox.advancedEditor")}>')
  logs=ui.index('<Panel label={t("singbox.logs")}>')
  self.assertLess(editor,logs)
  self.assertIn('<AnsiLogViewer',ui)
  self.assertNotIn('logsMeta.logs.join("\\n")',ui)

 def test_viewer_handles_real_and_transport_stripped_ansi(self):
  viewer=(ROOT/"app/dashboard/src/components/AnsiLogViewer.tsx").read_text()
  self.assertIn('(?:\\u001b\\[|\\[)',viewer)
  self.assertIn('codes[index + 1] === 5',viewer)
  self.assertIn('ansi256Color',viewer)
  self.assertIn('INFO:',viewer)
  self.assertIn('ERROR:',viewer)
  self.assertNotIn('dangerouslySetInnerHTML',viewer)

 def test_terminal_chrome_and_line_rows_exist(self):
  viewer=(ROOT/"app/dashboard/src/components/AnsiLogViewer.tsx").read_text()
  self.assertIn('#ff5f57',viewer); self.assertIn('#febc2e',viewer); self.assertIn('#28c840',viewer)
  self.assertIn('borderLeftColor={accentForLine(line)}',viewer)
  self.assertIn('{index + 1}</Text>',viewer)

if __name__=="__main__": unittest.main()
