#!/usr/bin/env python3
"""Teste de carga WebSocket para o Legenda v2."""

from __future__ import annotations

import argparse
import json
import statistics
import threading
import time
from dataclasses import dataclass

from websockets.sync.client import connect


@dataclass
class ClientResult:
    ok: bool
    connect_ms: float
    messages: int
    error: str = ""


def run_client(url: str, room: str, token: str, language: str, seconds: float) -> ClientResult:
    started = time.monotonic()
    messages = 0
    try:
        with connect(url, open_timeout=10, close_timeout=3) as ws:
            ws.send(json.dumps({
                "type": "auth",
                "room": room,
                "token": token,
                "language": language,
            }))
            welcome = json.loads(ws.recv(timeout=10))
            if welcome.get("type") != "welcome":
                raise RuntimeError(f"welcome inválido: {welcome}")
            connect_ms = (time.monotonic() - started) * 1000
            deadline = time.monotonic() + seconds
            while time.monotonic() < deadline:
                try:
                    ws.recv(timeout=min(1.0, max(0.05, deadline - time.monotonic())))
                    messages += 1
                except TimeoutError:
                    pass
            return ClientResult(True, connect_ms, messages)
    except Exception as exc:
        return ClientResult(False, (time.monotonic() - started) * 1000, messages, str(exc))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="ws://127.0.0.1:8098")
    parser.add_argument("--room", default="principal")
    parser.add_argument("--token", default="")
    parser.add_argument("--language", default="pt-BR")
    parser.add_argument("--clients", type=int, default=25)
    parser.add_argument("--seconds", type=float, default=30)
    args = parser.parse_args()

    results: list[ClientResult | None] = [None] * args.clients
    threads = []

    def worker(index: int) -> None:
        results[index] = run_client(
            args.url, args.room, args.token, args.language, args.seconds
        )

    for index in range(args.clients):
        thread = threading.Thread(target=worker, args=(index,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()

    final = [r for r in results if r is not None]
    success = [r for r in final if r.ok]
    failed = [r for r in final if not r.ok]
    latencies = [r.connect_ms for r in success]

    report = {
        "clients": args.clients,
        "success": len(success),
        "failed": len(failed),
        "success_rate": round(len(success) / max(1, args.clients), 4),
        "connect_avg_ms": round(statistics.fmean(latencies), 2) if latencies else None,
        "connect_p95_ms": round(sorted(latencies)[max(0, int(len(latencies) * .95) - 1)], 2) if latencies else None,
        "messages_received": sum(r.messages for r in success),
        "errors": [r.error for r in failed[:10]],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not failed else 2)


if __name__ == "__main__":
    main()
