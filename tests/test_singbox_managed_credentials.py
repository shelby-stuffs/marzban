import unittest
import importlib.util
from pathlib import Path
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("singbox_managed_credentials", ROOT / "app/singbox/managed_credentials.py")
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)
managed_password = MODULE.managed_password
managed_uuid = MODULE.managed_uuid


class SingBoxManagedCredentialTests(unittest.TestCase):
    def test_password_is_stable_per_user_and_inbound(self):
        first = managed_password("workspace-secret", "alice", "socks5")
        second = managed_password("workspace-secret", "alice", "socks5")
        other_inbound = managed_password("workspace-secret", "alice", "hysteria2")

        self.assertEqual(first, second)
        self.assertNotEqual(first, other_inbound)
        self.assertGreaterEqual(len(first), 32)

    def test_uuid_is_stable_and_valid(self):
        value = managed_uuid("workspace-secret", "alice", "tuic")

        self.assertEqual(value, managed_uuid("workspace-secret", "alice", "tuic"))
        self.assertNotEqual(value, managed_uuid("workspace-secret", "bob", "tuic"))
        self.assertEqual(UUID(value).version, 5)


if __name__ == "__main__":
    unittest.main()