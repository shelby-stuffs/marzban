from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class SingBoxHotReloadTests(unittest.TestCase):
 def test_core_uses_sighup_instead_of_stop_start(self):
  source=(ROOT/"app/singbox/core.py").read_text();body=source[source.index("    def apply("):source.index("    def reload(")];self.assertIn("self._signal_reload()",body);self.assertNotIn("self.stop()",body);self.assertIn("signal.SIGHUP",source);self.assertIn("restoring last working config",source)
 def test_identical_config_is_a_noop(self):
  self.assertIn("digest == self._digest and self.started and not force_reload",(ROOT/"app/singbox/core.py").read_text())
 def test_user_order_is_stable_and_crud_is_debounced(self):
  source=(ROOT/"app/singbox/runtime.py").read_text();self.assertIn('result.sort(key=lambda item: item["name"])',source);self.assertIn("self._run_scheduled_reload",source);self.assertIn("delay: float = 1.25",source)
if __name__=="__main__":unittest.main()
