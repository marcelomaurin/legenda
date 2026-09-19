"""Telemetria operacional do Legenda v2."""

from __future__ import annotations

import os
import statistics
import threading
import time
from collections import Counter, deque
from dataclasses import dataclass, field
from typing import Any

try:
    import psutil
except ImportError:
    psutil = None


@dataclass
class Telemetry:
    started_at: float = field(default_factory=time.monotonic)
    partial_events: int = 0
    final_events: int = 0
    translation_errors: int = 0
    stt_errors: int = 0
    dropped_partials: int = 0
    dropped_events: int = 0

    def __post_init__(self) -> None:
        self._lock = threading.Lock()
        self._latencies: deque[int] = deque(maxlen=500)
        self._process = psutil.Process(os.getpid()) if psutil is not None else None
        if self._process is not None:
            self._process.cpu_percent(None)

    def record_event(self, final: bool, latency_ms: int) -> None:
        with self._lock:
            if final:
                self.final_events += 1
            else:
                self.partial_events += 1
            self._latencies.append(int(latency_ms))

    def record_stt_error(self) -> None:
        with self._lock:
            self.stt_errors += 1

    def record_translation_error(self) -> None:
        with self._lock:
            self.translation_errors += 1

    def record_dropped_partial(self) -> None:
        with self._lock:
            self.dropped_partials += 1

    def record_dropped_event(self) -> None:
        with self._lock:
            self.dropped_events += 1

    @staticmethod
    def _percentile(values: list[int], q: float) -> int | None:
        if not values:
            return None
        ordered = sorted(values)
        index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
        return int(ordered[index])

    def snapshot(
        self,
        *,
        session_id: str,
        room_id: str,
        room_name: str,
        engine: str,
        event_queue_size: int,
        event_queue_capacity: int,
        stt_queue_size: int,
        stt_queue_capacity: int,
        tcp_clients: int,
        websocket_clients: list[dict[str, str]],
    ) -> dict[str, Any]:
        with self._lock:
            latencies = list(self._latencies)
            partial_events = self.partial_events
            final_events = self.final_events
            translation_errors = self.translation_errors
            stt_errors = self.stt_errors
            dropped_partials = self.dropped_partials
            dropped_events = self.dropped_events

        language_counts = Counter(
            client.get("language", "unknown") for client in websocket_clients
        )
        role_counts = Counter(
            client.get("role", "unknown") for client in websocket_clients
        )

        process: dict[str, Any] = {"cpu_percent": None, "memory_mb": None}
        if self._process is not None:
            try:
                process["cpu_percent"] = round(self._process.cpu_percent(None), 1)
                process["memory_mb"] = round(
                    self._process.memory_info().rss / (1024 * 1024), 1
                )
            except Exception:
                pass

        return {
            "type": "telemetry",
            "timestamp": time.time(),
            "uptime_seconds": int(time.monotonic() - self.started_at),
            "room": room_id,
            "room_name": room_name,
            "session_id": session_id,
            "engine": engine,
            "events": {
                "partial": partial_events,
                "final": final_events,
                "total": partial_events + final_events,
                "dropped": dropped_events,
            },
            "stt": {
                "errors": stt_errors,
                "dropped_partials": dropped_partials,
                "latency_avg_ms": round(statistics.fmean(latencies), 1) if latencies else None,
                "latency_p95_ms": self._percentile(latencies, 0.95),
                "samples": len(latencies),
            },
            "translation": {
                "errors": translation_errors,
            },
            "queues": {
                "events": {
                    "size": event_queue_size,
                    "capacity": event_queue_capacity,
                },
                "stt": {
                    "size": stt_queue_size,
                    "capacity": stt_queue_capacity,
                },
            },
            "clients": {
                "tcp": tcp_clients,
                "websocket": len(websocket_clients),
                "by_language": dict(language_counts),
                "by_role": dict(role_counts),
            },
            "process": process,
        }
