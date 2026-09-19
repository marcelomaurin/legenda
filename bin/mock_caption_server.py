#!/usr/bin/env python3
"""Servidor mock TCP para validar o cliente Lazarus do Legenda v2."""

from __future__ import annotations

import argparse
import json
import socket
import time
import uuid
from datetime import datetime


def caption_event(sequence: int, text: str, session_id: str) -> dict:
    return {
        "version": 2,
        "type": "caption",
        "session_id": session_id,
        "utterance_id": uuid.uuid4().hex[:12],
        "sequence": sequence,
        "timestamp": datetime.now().astimezone().isoformat(timespec="milliseconds"),
        "language": "pt-BR",
        "text": text,
        "final": True,
        "start_ms": sequence * 1000,
        "end_ms": sequence * 1000 + 900,
        "latency_ms": 10,
        "engine": "mock",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8097)
    parser.add_argument("--interval", type=float, default=1.0)
    parser.add_argument("--count", type=int, default=5)
    args = parser.parse_args()

    phrases = [
        "Teste de conexão do Legenda.",
        "O protocolo JSONL está funcionando.",
        "O cliente Lazarus recebeu uma legenda final.",
        "Esta execução não utiliza microfone nem reconhecimento de voz.",
        "Teste concluído.",
    ]

    session_id = "mock-" + uuid.uuid4().hex[:8]

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((args.host, args.port))
        server.listen(1)
        print(f"Mock Legenda aguardando cliente em {args.host}:{args.port}")

        client, address = server.accept()
        with client:
            print(f"Cliente conectado: {address[0]}:{address[1]}")
            for i in range(max(1, args.count)):
                text = phrases[i % len(phrases)]
                event = caption_event(i + 1, text, session_id)
                client.sendall((json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8"))
                print(text)
                time.sleep(max(0.05, args.interval))


if __name__ == "__main__":
    main()
