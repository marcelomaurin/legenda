#!/usr/bin/env python3
"""Verifica prontidão estrutural da branch para uma release do Legenda."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, asdict
from pathlib import Path


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


REQUIRED_FILES = [
    "bin/srvouve.py",
    "bin/orchestrator.py",
    "bin/fleet_server.py",
    "bin/load_test_websocket.py",
    "bin/protocol_soak.py",
    "bin/retention.py",
    "web/index.html",
    "web/admin.html",
    "web/fleet.html",
    "deploy/Caddyfile.example",
    "deploy/nginx-legenda.conf.example",
    "deploy/install_portable_windows.ps1",
    ".github/workflows/tests.yml",
    ".github/workflows/windows-release.yml",
    ".github/workflows/lazarus-build.yml",
    ".github/workflows/lazarus-windows.yml",
    "docs/OPERATIONS.md",
]


def check_repo(root: Path) -> list[Check]:
    checks: list[Check] = []

    for rel in REQUIRED_FILES:
        path = root / rel
        checks.append(Check(f"file:{rel}", path.exists(), "presente" if path.exists() else "ausente"))

    config_path = root / "config.example.json"
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        checks.extend([
            Check(
                "config:room_auth_required",
                config.get("room_auth_required") is True,
                repr(config.get("room_auth_required")),
            ),
            Check(
                "config:websocket_auth_timeout_seconds",
                float(config.get("websocket_auth_timeout_seconds", 0)) > 0,
                repr(config.get("websocket_auth_timeout_seconds")),
            ),
            Check(
                "config:retention_days",
                int(config.get("retention_days", 0)) > 0,
                repr(config.get("retention_days")),
            ),
        ])
    except Exception as exc:
        checks.append(Check("config:parse", False, str(exc)))

    instances_path = root / "instances.example.json"
    try:
        instances = json.loads(instances_path.read_text(encoding="utf-8"))
        token = str(instances.get("control_token", ""))
        host = str(instances.get("control_host", ""))
        checks.extend([
            Check("instances:control_host_loopback", host in {"127.0.0.1", "::1", "localhost"}, host),
            Check("instances:control_token_present", bool(token), "definido" if token else "vazio"),
        ])
    except Exception as exc:
        checks.append(Check("instances:parse", False, str(exc)))

    gitignore = (root / ".gitignore").read_text(encoding="utf-8")
    for secret_file in ("config.json", "instances.json", "nodes.json"):
        checks.append(Check(
            f"gitignore:{secret_file}",
            secret_file in gitignore.splitlines(),
            "ignorado" if secret_file in gitignore.splitlines() else "não ignorado",
        ))

    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    checks = check_repo(Path(args.root).resolve())
    failed = [check for check in checks if not check.ok]

    if args.json:
        print(json.dumps({
            "ok": not failed,
            "checks": [asdict(check) for check in checks],
            "failed": len(failed),
        }, ensure_ascii=False, indent=2))
    else:
        for check in checks:
            status = "OK" if check.ok else "FAIL"
            print(f"[{status}] {check.name}: {check.detail}")
        print(f"\nResultado: {'PRONTO' if not failed else 'NÃO PRONTO'} | falhas={len(failed)}")

    raise SystemExit(0 if not failed else 2)


if __name__ == "__main__":
    main()
