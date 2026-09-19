#!/usr/bin/env python3
"""Executa uma matriz de benchmarks STT e gera o relatório consolidado."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


def load_suite(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_commands(
    suite: dict[str, Any],
    *,
    python_exe: str,
    project_root: Path,
) -> list[list[str]]:
    manifest = str(suite["manifest"])
    output_dir = str(suite.get("output_dir", "benchmark_results"))
    config = str(suite.get("config", "config.json"))

    commands: list[list[str]] = []
    for run in suite.get("runs", []):
        if run.get("enabled", True) is False:
            continue
        cmd = [
            python_exe,
            str(project_root / "bin" / "benchmark_stt.py"),
            manifest,
            "--config",
            config,
            "--output-dir",
            output_dir,
        ]
        for key, flag in (
            ("engine", "--engine"),
            ("model", "--model"),
            ("device", "--device"),
            ("compute_type", "--compute-type"),
        ):
            value = run.get(key)
            if value is not None:
                cmd.extend([flag, str(value)])
        commands.append(cmd)

    return commands


def run_suite(path: Path, continue_on_error: bool = False) -> int:
    suite = load_suite(path)
    project_root = Path(__file__).resolve().parent.parent
    commands = build_commands(
        suite,
        python_exe=sys.executable,
        project_root=project_root,
    )

    failures = 0
    for index, cmd in enumerate(commands, start=1):
        print(f"\n=== Benchmark {index}/{len(commands)} ===")
        print(" ".join(cmd))
        result = subprocess.run(cmd, cwd=project_root)
        if result.returncode != 0:
            failures += 1
            if not continue_on_error:
                return result.returncode

    output_dir = Path(str(suite.get("output_dir", "benchmark_results")))
    report = str(suite.get("report", output_dir / "report.html"))
    report_cmd = [
        sys.executable,
        str(project_root / "bin" / "quality_report.py"),
        "--input-dir",
        str(output_dir),
        "--output",
        report,
    ]
    print("\n=== Relatório consolidado ===")
    print(" ".join(report_cmd))
    result = subprocess.run(report_cmd, cwd=project_root)
    if result.returncode != 0:
        return result.returncode

    return 0 if failures == 0 else 2


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "suite",
        nargs="?",
        default="benchmark_suite.example.json",
    )
    parser.add_argument("--continue-on-error", action="store_true")
    args = parser.parse_args()
    raise SystemExit(
        run_suite(Path(args.suite), continue_on_error=args.continue_on_error)
    )


if __name__ == "__main__":
    main()
