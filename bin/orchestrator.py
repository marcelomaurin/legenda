#!/usr/bin/env python3
"""Orquestrador simples de múltiplas instâncias do Legenda v2."""

from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from orchestrator_control import OrchestratorControlServer


@dataclass
class ManagedInstance:
    name: str
    config_path: Path
    process: subprocess.Popen | None = None
    desired_running: bool = True


class Orchestrator:
    def __init__(self, definition_path: Path) -> None:
        self.definition_path = definition_path
        data = json.loads(definition_path.read_text(encoding="utf-8"))
        definition_dir = definition_path.parent.resolve()

        base_config = Path(data.get("base_config", "config.json"))
        if not base_config.is_absolute():
            base_config = definition_dir / base_config
        self.base_config = base_config
        self.control_host = str(data.get("control_host", "127.0.0.1"))
        self.control_port = int(data.get("control_port", 8070))
        self.control_token = str(data.get("control_token", ""))
        self.project_root = Path(__file__).resolve().parent.parent

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

    def get_instance(self, name: str) -> ManagedInstance | None:
        return next((instance for instance in self.instances if instance.name == name), None)

    def instance_status(self, instance: ManagedInstance) -> dict[str, Any]:
        running = bool(instance.process and instance.process.poll() is None)
        returncode = None if running or instance.process is None else instance.process.returncode

        config = json.loads(instance.config_path.read_text(encoding="utf-8"))
        return {
            "name": instance.name,
            "running": running,
            "desired_running": instance.desired_running,
            "pid": instance.process.pid if running and instance.process else None,
            "returncode": returncode,
            "room": config.get("active_room"),
            "room_name": config.get("room_name"),
            "tcp_port": config.get("port"),
            "websocket_port": config.get("websocket_port"),
            "input_device_index": config.get("input_device_index"),
            "engine": config.get("stt_engine"),
            "model": config.get("whisper_model"),
            "config_path": str(instance.config_path),
        }

    def status_snapshot(self) -> dict[str, Any]:
        return {
            "type": "orchestrator_status",
            "timestamp": time.time(),
            "instances": [self.instance_status(instance) for instance in self.instances],
        }

    def start(self, instance: ManagedInstance) -> None:
        instance.desired_running = True
        if instance.process and instance.process.poll() is None:
            print(f"[{instance.name}] já está ativa")
            return

        env = os.environ.copy()
        env["LEGENDA_CONFIG"] = str(instance.config_path)

        instance.process = subprocess.Popen(
            [sys.executable, str(self.project_root / "bin" / "srvouve.py")],
            env=env,
            cwd=str(self.project_root),
        )
        print(f"[{instance.name}] iniciada PID={instance.process.pid}")

    def stop(self, instance: ManagedInstance, disable_restart: bool = True) -> None:
        if disable_restart:
            instance.desired_running = False

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

    def restart(self, instance: ManagedInstance) -> None:
        self.stop(instance, disable_restart=False)
        instance.desired_running = True
        self.start(instance)

    def start_control_server(self) -> None:
        server = OrchestratorControlServer(
            self,
            self.control_host,
            self.control_port,
            self.control_token,
        ).start()
        threading.Thread(
            target=server.serve_forever,
            daemon=True,
            name="orchestrator-control",
        ).start()
        print(
            f"[control] http://{self.control_host}:{self.control_port} "
            f"| auth={'on' if self.control_token else 'off'}"
        )

    def run(self) -> None:
        self.start_control_server()

        for instance in self.instances:
            self.start(instance)

        try:
            while True:
                time.sleep(1)
                for instance in self.instances:
                    if (
                        instance.desired_running
                        and instance.process
                        and instance.process.poll() is not None
                    ):
                        code = instance.process.returncode
                        print(f"[{instance.name}] encerrou código={code}; reiniciando")
                        self.start(instance)
        except KeyboardInterrupt:
            print("\nEncerrando instâncias...")
        finally:
            for instance in reversed(self.instances):
                self.stop(instance, disable_restart=True)


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
