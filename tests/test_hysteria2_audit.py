import copy
import io
import json
from contextlib import redirect_stdout
from pathlib import Path
import runpy
import tempfile
import unittest
from test_hysteria2_save_validation import valid_config

ROOT = Path(__file__).resolve().parents[1]
A = runpy.run_path(str(ROOT / "tools/audit_hysteria2.py"))

class AuditTests(unittest.TestCase):
    def test_clean_exports_and_no_mutation(self):
        core=valid_config(); hosts={"hy2":[{"address":"edge.example"}]}; users=[{"proxies":{"hysteria":{"auth":"private-auth"}}}]
        before=copy.deepcopy((core,hosts,users))
        report=A["audit"](core,hosts,users)
        self.assertEqual(report["errors"],0)
        self.assertEqual(report["warnings"],0)
        self.assertEqual((core,hosts,users),before)
        self.assertNotIn("private-auth",json.dumps(report))
        self.assertNotIn("secret-obfs",json.dumps(report))

    def test_legacy_and_duplicate_auth_are_reported_without_secrets(self):
        users=[{"proxies":{"hysteria":{"auth":"sensitive","obfs_password":"private-obfs"}}},{"proxies":{"hysteria":{"auth":"sensitive"}}}]
        report=A["audit"](valid_config(),{},users)
        codes={i["code"] for i in report["issues"]}
        self.assertIn("user_obfs_override",codes); self.assertIn("duplicate_user_auth",codes)
        self.assertNotIn("sensitive",json.dumps(report)); self.assertNotIn("private-obfs",json.dumps(report))

    def test_partial_inputs_are_not_claimed_complete(self):
        report=A["audit"](valid_config(),users={"users":[],"total":20})
        self.assertFalse(report["coverage"]["users"]); self.assertFalse(report["coverage"]["hosts"])

    def test_bad_core_and_host_are_errors(self):
        core=valid_config();core["inbounds"][0]["streamSettings"]["security"]="none"
        report=A["audit"](core,{"hy2":[{"address":"bad://address"}]},[])
        self.assertEqual(report["errors"],2)

    def test_none_obfs_is_distinct_from_inherit(self):
        report=A["audit"](valid_config(),{"hy2":[{"address":"edge.example","obfs":"none"}]},[])
        self.assertEqual(report["errors"],0)
        self.assertIn("obfs_differs_from_inbound",{i["code"] for i in report["issues"]})

    def test_cli_reads_without_modifying_files(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"core.json";path.write_text(json.dumps(valid_config()))
            before=path.read_bytes(); output=io.StringIO()
            with redirect_stdout(output): code=A["main"](["--core",str(path)])
            self.assertEqual(code,0);self.assertEqual(path.read_bytes(),before)
            self.assertTrue(json.loads(output.getvalue())["read_only"])

    def test_cli_malformed_json_does_not_echo_input(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"bad.json";path.write_text("private-invalid-content")
            output=io.StringIO()
            with redirect_stdout(output): code=A["main"](["--core",str(path)])
            self.assertEqual(code,2);self.assertNotIn("private-invalid-content",output.getvalue())

if __name__ == "__main__": unittest.main()
