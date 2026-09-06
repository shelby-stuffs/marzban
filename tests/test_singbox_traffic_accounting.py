import ast
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load_traffic():
    spec = importlib.util.spec_from_file_location("singbox_traffic_under_test", ROOT / "app/singbox/traffic.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SingBoxTrafficAccountingTests(unittest.TestCase):
    def test_installs_native_v2ray_user_stats_without_losing_cache(self):
        traffic = load_traffic()
        config = traffic.install_traffic_api(
            {"experimental": {"cache_file": {"enabled": True}}},
            host="127.0.0.1",
            port=10085,
            inbound_tag="hysteria-in",
            users=["7.alice", "8.bob", "7.alice"],
        )
        self.assertTrue(config["experimental"]["cache_file"]["enabled"])
        api = config["experimental"]["v2ray_api"]
        self.assertEqual(api["listen"], "127.0.0.1:10085")
        self.assertEqual(api["stats"], {
            "enabled": True,
            "inbounds": ["hysteria-in"],
            "users": ["7.alice", "8.bob"],
        })

    def test_formats_ipv6_api_listener(self):
        self.assertEqual(load_traffic().api_listen("::1", 10085), "[::1]:10085")

    def test_advanced_editor_rejects_managed_stats_api(self):
        source = (ROOT / "app/singbox/advanced.py").read_text()
        self.assertIn('"v2ray_api" in experimental', source)
        self.assertIn("managed by Marzban traffic accounting", source)

    def test_runtime_registers_exact_managed_user_names(self):
        source = (ROOT / "app/singbox/runtime.py").read_text()
        self.assertIn('users=(item["name"] for item in users)', source)
        self.assertIn("install_traffic_api", source)
        self.assertIn("self.traffic_api", source)

    def test_usage_job_merges_singbox_into_main_server_batch(self):
        source = (ROOT / "app/jobs/record_usages.py").read_text()
        self.assertIn("api_params[None].extend(get_users_stats(runtime.traffic_api))", source)
        self.assertIn("runtime.core.started", source)
        ast.parse(source)

    def test_docker_build_includes_required_tags(self):
        dockerfile = (ROOT / "Dockerfile").read_text()
        self.assertIn("with_quic with_grpc with_v2ray_api", dockerfile)
        self.assertIn("FROM golang:1.25-bookworm AS singbox-build", dockerfile)
        self.assertNotIn("SagerNet/sing-box/releases/download", dockerfile)

    def test_compose_does_not_publish_stats_port(self):
        compose = (ROOT / "compose.singbox-hysteria.yml").read_text()
        self.assertIn("SINGBOX_TRAFFIC_API_HOST: 127.0.0.1", compose)
        self.assertNotIn('10085:10085', compose)


if __name__ == "__main__":
    unittest.main()
