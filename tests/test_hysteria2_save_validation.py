"""Save-time contracts. Route bodies run via AST with explicit I/O spies.

No real DB, HTTP authentication, Xray executable, or restart is used here.
The actual validators and profile are loaded without booting app/__init__.
"""
import ast
import copy
from pathlib import Path
import runpy
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
V = runpy.run_path(str(ROOT / "app/utils/hysteria2_validation.py"))
Client = runpy.run_path(str(ROOT / "app/subscription/hysteria2.py"))["Hysteria2Client"]


def valid_config():
    return {"inbounds": [{"tag": "hy2", "protocol": "hysteria", "port": 443,
             "settings": {"version": 2, "clients": []},
             "streamSettings": {"method": "hysteria", "security": "tls", "tlsSettings": {},
                 "hysteriaSettings": {"version": 2},
                 "finalmask": {"udp": [{"type": "salamander", "settings": {"password": "secret-obfs"}}]}}}],
            "outbounds": [{"tag": "direct", "protocol": "freedom"}]}


def inbound_metadata():
    return {"protocol": "hysteria", "network": "hysteria", "tls": "tls", "port": 443,
            "sni": [], "obfs": "salamander", "obfs_password": "server-secret"}


class HTTPError(Exception):
    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail
        super().__init__(detail)


def load_route(relative, function_name, namespace):
    source = ROOT / relative
    tree = ast.parse(source.read_text())
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == function_name)
    node.decorator_list = []
    node.args.defaults = [ast.Constant(None) for _ in node.args.defaults]
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    module = ast.fix_missing_locations(ast.Module(body=[future, node], type_ignores=[]))
    env = {"HTTPException": HTTPError, "deepcopy": copy.deepcopy, **V, **namespace}
    exec(compile(module, str(source), "exec"), env)
    return env[function_name]


class SaveValidationTests(unittest.TestCase):
    def test_config_is_not_mutated(self):
        payload = valid_config(); before = copy.deepcopy(payload)
        V["validate_hysteria2_config"](payload)
        self.assertEqual(payload, before)

    def test_other_protocols_are_not_restricted(self):
        V["validate_hysteria2_config"]({"inbounds": [{"protocol": "vless", "streamSettings": {"method": "hysteria"}}]})

    def test_empty_managed_clients_allowed(self):
        V["validate_hysteria2_config"](valid_config())

    def test_requires_tls_and_hysteria_transport(self):
        for key, value in (("security", "none"), ("security", "reality"), ("method", "raw")):
            p = valid_config(); p["inbounds"][0]["streamSettings"][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                V["validate_hysteria2_config"](p)

    def test_versions_and_ports_are_checked(self):
        for version in (None, 1, True, "2", 2.0):
            p = valid_config(); p["inbounds"][0]["settings"]["version"] = version
            with self.subTest(version=version), self.assertRaises(ValueError):
                V["validate_hysteria2_config"](p)
        for port in (0, 65536, "443-8443", True):
            p = valid_config(); p["inbounds"][0]["port"] = port
            with self.subTest(port=port), self.assertRaises(ValueError):
                V["validate_hysteria2_config"](p)

    def test_legacy_obfs_is_not_silently_migrated(self):
        p = valid_config(); p["inbounds"][0]["streamSettings"]["hysteriaSettings"]["obfs"] = "salamander"
        before = copy.deepcopy(p)
        with self.assertRaisesRegex(ValueError, "move legacy"):
            V["validate_hysteria2_config"](p)
        self.assertEqual(p, before)

    def test_advanced_masks_are_not_silently_flattened(self):
        base = {"type": "salamander", "settings": {"password": "secret"}}
        for masks in ([base, base], [{"type": "sudoku", "settings": {}}],
                      [{"type": "salamander", "settings": {"password": "secret", "packetSize": "512-1200"}}]):
            p = valid_config(); p["inbounds"][0]["streamSettings"]["finalmask"]["udp"] = masks
            with self.subTest(masks=masks), self.assertRaises(ValueError):
                V["validate_hysteria2_config"](p)

    def test_malformed_masks_are_rejected(self):
        for value in (None, [], {"udp": None}, {"udp": [None]}, {"udp": [{"type": "salamander", "settings": {}}]}):
            p = valid_config(); p["inbounds"][0]["streamSettings"]["finalmask"] = value
            with self.subTest(value=value), self.assertRaises(ValueError):
                V["validate_hysteria2_config"](p)

    def test_duplicate_and_empty_auth_are_rejected_without_secret_echo(self):
        for users in ([{"auth": ""}], [{"auth": "private-token"}, {"auth": "private-token"}]):
            p = valid_config(); p["inbounds"][0]["settings"]["clients"] = users
            with self.assertRaises(ValueError) as caught:
                V["validate_hysteria2_config"](p)
            self.assertNotIn("private-token", str(caught.exception))

    def test_conflicting_users_clients_are_rejected(self):
        p = valid_config(); p["inbounds"][0]["settings"].update(clients=[{"auth": "a"}], users=[{"auth": "b"}])
        with self.assertRaisesRegex(ValueError, "do not mix"):
            V["validate_hysteria2_config"](p)

    def test_empty_host_settings_inherit(self):
        result = V["resolve_hysteria2_host"](inbound_metadata(), {"security": "inbound_default", "obfs": "", "obfs_password": ""})
        self.assertEqual(result["obfs_password"], "server-secret")
        self.assertEqual(result["tls"], "tls")

    def test_explicit_false_host_insecure_wins(self):
        inbound = dict(inbound_metadata(), allowinsecure=True)
        self.assertIs(V["resolve_hysteria2_host"](inbound, {"allowinsecure": False})["ais"], False)
        self.assertIs(V["resolve_hysteria2_host"](inbound, {"allowinsecure": None})["ais"], True)

    def test_host_pool_and_templates_pass_without_rewriting(self):
        hosts = {"hy2": [{"address": "edge.example.com,[2001:db8::1],{SERVER_IP}", "security": "tls"}]}
        before = copy.deepcopy(hosts)
        V["validate_hysteria2_hosts"](hosts, {"hy2": inbound_metadata()}, client_type=Client)
        self.assertEqual(hosts, before)

    def test_invalid_active_host_is_rejected(self):
        for host in ({"address": "edge.example", "security": "none"}, {"address": "https://bad.example"},
                     {"address": "edge.example", "port": 0}, {"address": "edge.example", "obfs": "sudoku"}):
            with self.subTest(host=host), self.assertRaises(ValueError):
                V["validate_hysteria2_hosts"]({"hy2": [host]}, {"hy2": inbound_metadata()}, client_type=Client)

    def test_disabled_host_can_be_retained(self):
        V["validate_hysteria2_hosts"]({"hy2": [{"address": "", "is_disabled": True}]}, {"hy2": inbound_metadata()}, client_type=Client)

    def host_route(self):
        calls = []
        inbounds = {"first": inbound_metadata(), "second": inbound_metadata()}
        crud = SimpleNamespace(update_hosts=lambda *a: calls.append("write"), get_hosts=lambda *a: [])
        xray = SimpleNamespace(config=SimpleNamespace(inbounds_by_tag=inbounds), hosts=SimpleNamespace(update=lambda: calls.append("refresh")))
        subscription_cache = SimpleNamespace(invalidate=lambda: calls.append("invalidate"))
        route = load_route("app/routers/system.py", "modify_hosts", {"xray": xray, "crud": crud, "Hysteria2Client": Client, "subscription_cache": subscription_cache})
        return route, calls

    def test_all_hosts_validated_before_first_crud_write(self):
        route, calls = self.host_route()
        with self.assertRaises(HTTPError) as caught:
            route({"first": [{"address": "valid.example"}], "second": [{"address": "invalid://host"}]}, db=None, admin=None)
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(calls, [])

    def test_valid_host_request_reaches_existing_write_path(self):
        route, calls = self.host_route()
        route({"first": [{"address": "valid.example"}]}, db=None, admin=None)
        self.assertEqual(calls, ["write", "refresh", "invalidate"])

    def core_route(self, relative, name):
        calls = []
        class Config(dict):
            def __init__(self, payload, **kwargs): super().__init__(payload)
            def include_db_users(self): return self
        xray = SimpleNamespace(config=SimpleNamespace(api_port=8080), nodes={},
            core=SimpleNamespace(validate_config=lambda *a: calls.append("binary-test"), restart=lambda *a: calls.append("restart")),
            hosts=SimpleNamespace(update=lambda: calls.append("refresh")))
        ns = {"XRayConfig": Config, "xray": xray, "XRAY_JSON": "unused.json",
              "normalize_xray_v26_config": lambda p: p,
              "_atomic_write_json": lambda *a: calls.append("write"), "atomic_write_json": lambda *a: calls.append("write"),
              "subscription_cache": SimpleNamespace(invalidate=lambda: calls.append("invalidate"))}
        return load_route(relative, name, ns), calls

    def test_all_core_save_paths_reject_before_write_or_restart(self):
        routes = [("app/routers/core.py", "modify_core_config"), ("app/routers/xhttp_inbound.py", "_validate_and_apply"),
                  ("app/routers/wireguard_outbound.py", "_validate_and_apply")]
        for relative, name in routes:
            with self.subTest(route=relative):
                route, calls = self.core_route(relative, name)
                payload = valid_config(); payload["inbounds"][0]["streamSettings"]["security"] = "none"
                with self.assertRaises(HTTPError) as caught: route(payload)
                self.assertEqual(caught.exception.status_code, 400)
                self.assertEqual(calls, [])

    def test_valid_core_still_gets_binary_test_before_persistence(self):
        route, calls = self.core_route("app/routers/core.py", "modify_core_config")
        route(valid_config())
        self.assertEqual(calls, ["binary-test", "write", "restart", "refresh", "invalidate"])

    def test_user_auth_guard_only_affects_hysteria(self):
        for auth in (None, "", 123):
            with self.assertRaises(ValueError): V["validate_hysteria2_user_proxies"]({"hysteria": {"auth": auth}})
        self.assertEqual(V["validate_hysteria2_user_proxies"]({"vless": {}}), {"vless": {}})
        V["validate_hysteria2_user_proxies"]({"hysteria": {"auth": "opaque:secret"}})

    def test_user_write_guards_are_attached_to_create_and_modify_only(self):
        # Execute the actual validator method from each write model using real
        # Pydantic, with a minimal base model to avoid DB imports.
        from pydantic import BaseModel, field_validator, ValidationError
        tree = ast.parse((ROOT / "app/models/user.py").read_text())
        for name in ("UserCreate", "UserModify"):
            model = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)
            method = next(n for n in model.body if isinstance(n, ast.FunctionDef) and n.name == "validate_hysteria2_auth_on_write")
            body = ast.ClassDef(name="WriteModel", bases=[ast.Name(id="ReadModel", ctx=ast.Load())], keywords=[], body=[method], decorator_list=[])
            class ReadModel(BaseModel): proxies: dict = {}
            env = {"ReadModel": ReadModel, "field_validator": field_validator, **V}
            exec(compile(ast.fix_missing_locations(ast.Module(body=[body], type_ignores=[])), "write-model-test", "exec"), env)
            with self.assertRaises(ValidationError): env["WriteModel"](proxies={"hysteria": {"auth": ""}})
            ReadModel(proxies={"hysteria": {"auth": ""}})


if __name__ == "__main__": unittest.main()
