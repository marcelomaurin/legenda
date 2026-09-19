#!/usr/bin/env python3
"""Soak test sintético do protocolo TCP/JSONL do Legenda."""

from __future__ import annotations

import argparse
import json
import socket
import threading
import time

from mock_caption_server import caption_event


def run_soak(events: int, payload_size: int = 0) -> dict:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]

    send_error: list[str] = []
    session_id = "soak-session"
    filler = "x" * max(0, payload_size)

    def producer() -> None:
        try:
            client, _ = server.accept()
            with client:
                for seq in range(1, events + 1):
                    event = caption_event(seq, f"evento {seq} {filler}", session_id)
                    client.sendall(
                        (json.dumps(event, ensure_ascii=False) + "\n").encode("utf-8")
                    )
        except Exception as exc:
            send_error.append(str(exc))
        finally:
            server.close()

    thread = threading.Thread(target=producer)
    thread.start()

    started = time.monotonic()
    buffer = b""
    received = 0
    last_sequence = 0
    malformed = 0

    with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
        client.settimeout(5)
        while received < events:
            chunk = client.recv(65536)
            if not chunk:
                break
            buffer += chunk
            while b"\n" in buffer:
                line, buffer = buffer.split(b"\n", 1)
                if not line:
                    continue
                try:
                    event = json.loads(line.decode("utf-8"))
                    if event.get("version") != 2 or event.get("type") != "caption":
                        malformed += 1
                    sequence = int(event.get("sequence", 0))
                    if sequence != last_sequence + 1:
                        malformed += 1
                    last_sequence = sequence
                except Exception:
                    malformed += 1
                received += 1

    thread.join(timeout=10)
    elapsed = time.monotonic() - started

    return {
        "sent": events,
        "received": received,
        "lost": max(0, events - received),
        "malformed": malformed,
        "send_errors": send_error,
        "elapsed_seconds": round(elapsed, 3),
        "events_per_second": round(received / elapsed, 2) if elapsed > 0 else None,
        "last_sequence": last_sequence,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--events", type=int, default=10000)
    parser.add_argument("--payload-size", type=int, default=0)
    args = parser.parse_args()

    result = run_soak(max(1, args.events), max(0, args.payload_size))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    ok = (
        result["received"] == result["sent"]
        and result["lost"] == 0
        and result["malformed"] == 0
        and not result["send_errors"]
    )
    raise SystemExit(0 if ok else 2)


if __name__ == "__main__":
    main()
