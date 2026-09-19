#!/usr/bin/env python3
"""Orquestrador simples de múltiplas instâncias do Legenda v2."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class ManagedInstance:
    name: str
    config_path: Path
    process: subprocess.Popen | None = None


class Orchestrator:
    def __init__(self, definition_path: Path) -> None:
        self.definition_path = definition_path
        data = json.loads(definition_path.read_text(encoding="utf-8"))
        definition_dir = definition_path.parent.resolve()

        base_config = Path(data.get("base_config", "config.json"))
        if not base_config.is_absolute():
            base_config = definition_dir / base_config
        self.base_config = base_config

        self.instances: list[ManagedInstance] = []

        runtime_dir = Path(data.get("runtime_dir", ".runtime/instances"))
        if not runtime_dir.is_absolute():
            runtime_dir = definition_dir / runtime_dir
        runtime_dir.mkdir(parents=True, exist_ok=True)
        self.runtime_dir = runtime_dir

        for item in data.get("instances", []):
            name = str(item["name"])
            config_path = runtime_dir / f"{name}.json"
            self._build_instance_config(item, config_path)
            self.instances.append(ManagedInstance(name=name, config_path=config_path))

    def _build_instance_config(self, item: dict[str, Any], output: Path) -> None:
        base: dict[str, Any] = {}
        if self.base_config.exists():
            base = json.loads(self.base_config.read_text(encoding="utf-8"))

        overrides = dict(item.get("overrides", {}))
        base.update(overrides)
        output.write_text(
            json.dumps(base, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def start(self, instance: ManagedInstance) -> None:
        if instance.process and instance.process.poll() is None:
            print(f"[{instance.name}] já está ativa")
            return

        env = os.environ.copy()
        env["LEGENDA_CONFIG"] = str(instance.config_path)

        instance.process = subprocess.Popen(
            [sys.executable, "bin/srvouve.py"],
            env=env,
        )
        print(f"[{instance.name}] iniciada PID={instance.process.pid}")

    def stop(self, instance: ManagedInstance) -> None:
        if not instance.process or instance.process.poll() is not None:
            return

        instance.process.send_signal(signal.SIGINT)
        try:
            instance.process.wait(timeout=8)
        except subprocess.TimeoutExpired:
            instance.process.terminate()
            try:
                instance.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                instance.process.kill()

        print(f"[{instance.name}] encerrada")

    def run(self) -> None:
        for instance in self.instances:
            self.start(instance)

        try:
            while True:
                time.sleep(1)
                for instance in self.instances:
                    if instance.process and instance.process.poll() is not None:
                        code = instance.process.returncode
                        print(f"[{instance.name}] encerrou código={code}; reiniciando")
                        self.start(instance)
        except KeyboardInterrupt:
            print("\nEncerrando instâncias...")
        finally:
            for instance in reversed(self.instances):
                self.stop(instance)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "definition",
        nargs="?",
        default="instances.json",
        help="Arquivo JSON de definição das instâncias",
    )
    args = parser.parse_args()

    Orchestrator(Path(args.definition)).run()


if __name__ == "__main__":
    main()
