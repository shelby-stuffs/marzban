#!/usr/bin/env python3
"""Read-only offline audit. Reads local JSON exports; never writes or connects.

Output contains field locations and messages, not credentials or input records.
This does not replace Xray run -test, certificate checks or a connection test.
"""
import argparse
import json
from pathlib import Path
import runpy
import sys

ROOT = Path(__file__).resolve().parents[1]
V = runpy.run_path(str(ROOT / "app/utils/hysteria2_validation.py"))
Client = runpy.run_path(str(ROOT / "app/subscription/hysteria2.py"))["Hysteria2Client"]


def audit(core, hosts=None, users=None):
    issues = []
    coverage = {"core": True, "hosts": hosts is not None, "users": users is not None}
    def issue(level, code, location, message):
        issues.append({"level": level, "code": code, "location": location, "message": message})
    if not isinstance(core, dict) or not isinstance(core.get("inbounds"), list):
        raise ValueError("Core export must be an object with an inbounds array")
    metadata = {}
    tags = set()
    for index, inbound in enumerate(core["inbounds"]):
        location = f"core.inbounds[{index}]"
        if not isinstance(inbound, dict):
            issue("error", "invalid_inbound", location, "Inbound must be an object")
            continue
        tag = inbound.get("tag")
        if not isinstance(tag, str) or not tag:
            issue("error", "missing_tag", location, "A non-empty inbound tag is required for panel management")
        elif tag in tags:
            issue("error", "duplicate_tag", location, "Duplicate inbound tag")
        else:
            tags.add(tag)
        if inbound.get("protocol") != "hysteria":
            continue
        try:
            V["validate_hysteria2_config"]({"inbounds": [inbound]})
        except (ValueError, TypeError):
            # Deliberately do not echo arbitrary config values or credentials.
            issue("error", "incompatible_core", location,
                  "Check TLS, both version=2 fields, integer port, clients/auth and plain Salamander finalmask; use the stage-2 checklist")
        stream = inbound.get("streamSettings") or {}
        if not isinstance(stream, dict):
            continue
        transport = stream.get("hysteriaSettings") or {}
        if not isinstance(transport, dict):
            transport = {}
        obfs, password = "", ""
        if "finalmask" in stream:
            mask = stream.get("finalmask")
            masks = mask.get("udp", []) if isinstance(mask, dict) else []
            for mask in masks if isinstance(masks, list) else []:
                if isinstance(mask, dict) and mask.get("type") == "salamander":
                    settings = mask.get("settings")
                    if isinstance(settings, dict) and isinstance(settings.get("password"), str) and settings["password"]:
                        obfs, password = "salamander", settings["password"]
                        break
        else:
            obfs, password = transport.get("obfs", ""), transport.get("obfsPassword", "")
        if isinstance(tag, str) and tag:
            metadata[tag] = {"protocol": "hysteria", "network": stream.get("method") or stream.get("network"),
                             "tls": stream.get("security"), "port": inbound.get("port"),
                             "hysteria_version": transport.get("version", 2),
                             "sni": "", "obfs": obfs, "obfs_password": password}
    if hosts is None:
        issue("warning", "hosts_not_checked", "hosts", "Supply a hosts export to check overrides")
    else:
        if not isinstance(hosts, dict):
            raise ValueError("Hosts export must be an object keyed by inbound tag")
        for entry, (tag, rows) in enumerate(hosts.items()):
            location = f"hosts.entry[{entry}]"
            if not isinstance(rows, list):
                issue("error", "invalid_hosts", location, "Expected an array of hosts")
                continue
            if tag not in tags:
                issue("warning", "orphan_hosts", location, "Inbound is absent from the core export")
                continue
            if tag not in metadata:
                continue
            for index, host in enumerate(rows):
                place = f"{location}.hosts[{index}]"
                if not isinstance(host, dict):
                    issue("error", "invalid_host", place, "Host must be an object")
                    continue
                if host.get("is_disabled"):
                    issue("warning", "disabled_host_not_checked", place, "Check this host again before enabling it")
                    continue
                try:
                    V["validate_hysteria2_hosts"]({"audit": [host]}, {"audit": metadata[tag]}, client_type=Client)
                except (ValueError, TypeError):
                    issue("error", "invalid_host", place, "Effective host profile is invalid; check address, port, TLS and inherited obfs")
                if "{" in str(host.get("address", "")):
                    issue("warning", "dynamic_address", place, "Runtime address substitution still needs testing")
                if host.get("obfs") not in (None, "") or host.get("obfs_password") not in (None, ""):
                    effective = V["resolve_hysteria2_host"](metadata[tag], host)
                    mode = "" if effective["obfs"] == "none" else effective["obfs"]
                    if mode != metadata[tag]["obfs"] or (mode and effective["obfs_password"] != metadata[tag]["obfs_password"]):
                        issue("warning", "obfs_differs_from_inbound", place,
                              "Host export differs from this inbound; confirm it points to a server with matching obfs")
    if users is None:
        issue("warning", "users_not_checked", "users", "Supply a complete users export to check legacy settings")
    else:
        if isinstance(users, dict):
            rows = users.get("users")
            total = users.get("total")
            if isinstance(rows, list) and isinstance(total, int) and total > len(rows):
                coverage["users"] = False
                issue("warning", "partial_users_export", "users", "Export contains only part of the user list; fetch all pages")
        else:
            rows = users
        if not isinstance(rows, list):
            raise ValueError("Users export must be an array or an object with a users array")
        seen = set()
        for index, user in enumerate(rows):
            place = f"users[{index}]"
            if not isinstance(user, dict) or not isinstance(user.get("proxies", {}), dict):
                issue("error", "invalid_user", place, "Invalid user/proxies shape")
                continue
            settings = user.get("proxies", {}).get("hysteria")
            if settings is None:
                continue
            try:
                V["validate_hysteria2_user_proxies"]({"hysteria": settings})
            except ValueError:
                issue("error", "invalid_auth", place, "Hysteria auth is missing or empty")
                continue
            auth = settings.get("auth") if isinstance(settings, dict) else None
            if auth in seen:
                issue("warning", "duplicate_user_auth", place, "Auth is reused by another exported user; review inbound assignments")
            seen.add(auth)
            if isinstance(settings, dict) and (settings.get("obfs") or settings.get("obfs_password")):
                issue("warning", "legacy_user_obfs", place, "Per-user obfs is retained but does not override canonical host/inbound metadata")
    return {"read_only": True, "coverage": coverage,
            "errors": sum(i["level"] == "error" for i in issues),
            "warnings": sum(i["level"] == "warning" for i in issues), "issues": issues}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core", required=True, help="Core config JSON exported locally")
    parser.add_argument("--hosts", help="GET /api/hosts JSON export")
    parser.add_argument("--users", help="Complete GET /api/users export or array of users")
    args = parser.parse_args(argv)
    try:
        def read(path):
            if path is None:
                return None
            # Strict JSON exports, not JSON-with-comments and not a live DB.
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        result = audit(read(args.core), read(args.hosts), read(args.users))
    except (OSError, ValueError, TypeError):
        print(json.dumps({"read_only": True, "error": "Cannot audit inputs. Check access, strict JSON syntax and documented export shapes."}))
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
