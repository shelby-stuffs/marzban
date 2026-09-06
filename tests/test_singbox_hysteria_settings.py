from pathlib import Path
import importlib.util
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

config_spec = importlib.util.spec_from_file_location("sb_config", ROOT / "app/singbox/config.py")
sb_config = importlib.util.module_from_spec(config_spec)
config_spec.loader.exec_module(sb_config)
settings_spec = importlib.util.spec_from_file_location("sb_settings", ROOT / "app/singbox/settings.py")
sb_settings = importlib.util.module_from_spec(settings_spec)
sys.modules[settings_spec.name] = sb_settings
settings_spec.loader.exec_module(sb_settings)


def legacy_config():
    return {
        "inbounds": [{
            "tag": "legacy-hy2",
            "protocol": "hysteria",
            "listen": "0.0.0.0",
            "port": 8443,
            "settings": {"up_mbps": 120, "down_mbps": 500},
            "streamSettings": {
                "method": "hysteria",
                "security": "tls",
                "tlsSettings": {
                    "alpn": ["h3"],
                    "certificates": [{
                        "certificateFile": "/certs/fullchain.pem",
                        "keyFile": "/certs/privkey.pem",
                    }],
                },
                "finalmask": {"udp": [{
                    "type": "salamander",
                    "settings": {"password": "server-mask"},
                }]},
            },
        }],
        "outbounds": [{"protocol": "freedom", "tag": "direct"}],
    }


class SingBoxHysteriaSettingsTests(unittest.TestCase):
    def test_autogeneration_reads_legacy_certificate_and_server_values(self):
        generated, source = sb_settings.generate_settings(legacy_config())
        self.assertEqual(source, "legacy_xray_inbound")
        self.assertEqual(generated["tag"], "legacy-hy2")
        self.assertEqual(generated["listen_port"], 8443)
        self.assertEqual(generated["certificate_path"], "/certs/fullchain.pem")
        self.assertEqual(generated["key_path"], "/certs/privkey.pem")
        self.assertEqual(generated["obfs_password"], "server-mask")

    def test_enabled_settings_require_certificate_paths(self):
        with self.assertRaisesRegex(ValueError, "certificate_path"):
            sb_settings.Hysteria2ServerSettings(certificate_path="", key_path="")
        disabled = sb_settings.Hysteria2ServerSettings(
            enabled=False, certificate_path="", key_path=""
        )
        self.assertFalse(disabled.enabled)

    def test_settings_are_saved_atomically_and_loaded(self):
        settings = sb_settings.Hysteria2ServerSettings(
            certificate_path="/cert.pem", key_path="/key.pem"
        )
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / "hysteria2.json")
            sb_settings.save_settings(path, settings)
            loaded = sb_settings.load_settings(path)
            self.assertEqual(loaded, settings)
            self.assertEqual(list(Path(directory).glob("*.tmp")), [])

    def test_runtime_config_uses_dedicated_settings_and_auth_only(self):
        settings = sb_settings.Hysteria2ServerSettings(
            tag="hy2-main",
            listen="::",
            listen_port=443,
            certificate_path="/cert.pem",
            key_path="/key.pem",
            obfs_password="mask",
            masquerade="https://example.com",
        )
        config = sb_config.build_hysteria2_settings_config(
            settings.model_dump(),
            [{"name": "1.alice", "password": "auth", "obfs_password": "leak"}],
        )
        inbound = config["inbounds"][0]
        self.assertEqual(inbound["users"], [{"name": "1.alice", "password": "auth"}])
        self.assertEqual(inbound["tls"]["certificate_path"], "/cert.pem")
        self.assertEqual(inbound["masquerade"], "https://example.com")
        self.assertNotIn("leak", str(config))

    def test_virtual_inbound_has_generic_subscription_metadata(self):
        settings = sb_settings.Hysteria2ServerSettings(
            certificate_path="/cert.pem", key_path="/key.pem"
        )
        inbound = sb_config.settings_to_subscription_inbound(settings.model_dump())
        required = {
            "tag", "protocol", "network", "port", "tls", "sni", "host",
            "path", "header_type", "fp", "pbk", "sid", "alpn",
        }
        self.assertEqual(required - inbound.keys(), set())
        self.assertEqual(inbound["sni"], [])
        self.assertEqual(inbound["host"], [])

    def test_virtual_inbound_replaces_legacy_metadata_only(self):
        class FakeConfig(dict):
            pass
        config = FakeConfig(legacy_config())
        old = {"tag": "legacy-hy2", "protocol": "hysteria"}
        vless = {"tag": "vless", "protocol": "vless"}
        config.inbounds = [old, vless]
        config.inbounds_by_tag = {"legacy-hy2": old, "vless": vless}
        config.inbounds_by_protocol = {"hysteria": [old], "vless": [vless]}
        settings = sb_settings.Hysteria2ServerSettings(
            tag="hy2-main", certificate_path="/cert.pem", key_path="/key.pem"
        )
        sb_config.install_virtual_hysteria_inbound(config, settings.model_dump())
        self.assertEqual(config.inbounds_by_protocol["hysteria"][0]["tag"], "hy2-main")
        self.assertEqual(config["inbounds"][0]["tag"], "legacy-hy2")


if __name__ == "__main__":
    unittest.main()
