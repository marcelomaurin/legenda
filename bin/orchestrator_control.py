"""API HTTP de controle do orquestrador Legenda v2."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse

try:
    from .security_utils import bearer_matches, require_token_for_remote_bind
except ImportError:
    from security_utils import bearer_matches, require_token_for_remote_bind


class OrchestratorControlServer:
    def __init__(self, orchestrator: Any, host: str, port: int, token: str) -> None:
        self.orchestrator = orchestrator
        self.host = host
        self.port = port
        self.token = token
        self.httpd: ThreadingHTTPServer | None = None
        require_token_for_remote_bind(host, token, "orchestrator-control")

    def start(self) -> ThreadingHTTPServer:
        orchestrator = self.orchestrator
        expected_token = self.token

        class Handler(BaseHTTPRequestHandler):
            server_version = "LegendaOrchestrator/1.0"

            def log_message(self, fmt: str, *args: Any) -> None:
                print("[control]", fmt % args)

            def _authorized(self) -> bool:
                if not expected_token:
                    return True
                auth = self.headers.get("Authorization", "")
                return bearer_matches(auth, expected_token)

            def _json(self, status: int, payload: Any) -> None:
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.end_headers()
                self.wfile.write(data)

            def do_OPTIONS(self) -> None:
                self.send_response(204)
                self.send_header("Access-Control-Allow-Origin", "*")
                self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
                self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                self.end_headers()

            def do_GET(self) -> None:
                if not self._authorized():
                    self._json(401, {"error": "unauthorized"})
                    return

                path = urlparse(self.path).path
                if path == "/api/status":
                    self._json(200, orchestrator.status_snapshot())
                    return

                if path == "/api/health":
                    self._json(200, {"status": "ok"})
                    return

                self._json(404, {"error": "not_found"})

            def do_POST(self) -> None:
                if not self._authorized():
                    self._json(401, {"error": "unauthorized"})
                    return

                parts = [p for p in urlparse(self.path).path.split("/") if p]
                if len(parts) != 3 or parts[0] != "api":
                    self._json(404, {"error": "not_found"})
                    return

                action, name = parts[1], parts[2]
                instance = orchestrator.get_instance(name)
                if instance is None:
                    self._json(404, {"error": "instance_not_found", "name": name})
                    return

                try:
                    if action == "start":
                        orchestrator.start(instance)
                    elif action == "stop":
                        orchestrator.stop(instance, disable_restart=True)
                    elif action == "restart":
                        orchestrator.restart(instance)
                    else:
                        self._json(404, {"error": "action_not_found"})
                        return
                    self._json(200, orchestrator.instance_status(instance))
                except Exception as exc:
                    self._json(500, {"error": "control_failed", "message": str(exc)})

        self.httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        return self.httpd
