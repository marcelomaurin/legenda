#!/usr/bin/env python3
"""Agregador multi-no para instalacoes Legenda v2."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class Fleet:
    def __init__(self, config_path: Path) -> None:
        self.config_path = config_path
        self.data = json.loads(config_path.read_text(encoding="utf-8"))
        self.nodes = list(self.data.get("nodes", []))
        self.api_token = str(self.data.get("fleet_token", ""))
        self.timeout = float(self.data.get("timeout_seconds", 3))

    def _request(self, node: dict[str, Any], path: str, method: str = "GET") -> Any:
        base = str(node["url"]).rstrip("/")
        req = urllib.request.Request(base + path, method=method)
        token = str(node.get("token", ""))
        if token:
            req.add_header("Authorization", f"Bearer {token}")
        req.add_header("Accept", "application/json")
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    def status(self) -> dict[str, Any]:
        nodes = []
        for node in self.nodes:
            started = time.monotonic()
            item = {
                "id": str(node["id"]),
                "name": str(node.get("name", node["id"])),
                "url": str(node["url"]),
                "online": False,
                "latency_ms": None,
                "instances": [],
                "error": None,
            }
            try:
                status = self._request(node, "/api/status")
                item["online"] = True
                item["instances"] = status.get("instances", [])
                item["latency_ms"] = round((time.monotonic() - started) * 1000, 1)
            except Exception as exc:
                item["error"] = str(exc)
            nodes.append(item)

        return {
            "type": "fleet_status",
            "timestamp": time.time(),
            "nodes": nodes,
        }

    def get_node(self, node_id: str) -> dict[str, Any] | None:
        return next((node for node in self.nodes if str(node.get("id")) == node_id), None)

    def control(self, node_id: str, action: str, instance: str) -> Any:
        node = self.get_node(node_id)
        if node is None:
            raise ValueError("no inexistente")
        if action not in {"start", "stop", "restart"}:
            raise ValueError("acao invalida")
        encoded = urllib.parse.quote(instance, safe="")
        return self._request(node, f"/api/{action}/{encoded}", method="POST")


def make_handler(fleet: Fleet):
    class Handler(BaseHTTPRequestHandler):
        server_version = "LegendaFleet/1.0"

        def log_message(self, fmt: str, *args: Any) -> None:
            print("[fleet]", fmt % args)

        def _authorized(self) -> bool:
            if not fleet.api_token:
                return True
            return self.headers.get("Authorization", "") == f"Bearer {fleet.api_token}"

        def _json(self, status: int, payload: Any) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.end_headers()
            self.wfile.write(body)

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
            if path == "/api/health":
                self._json(200, {"status": "ok"})
                return
            if path == "/api/fleet":
                self._json(200, fleet.status())
                return
            self._json(404, {"error": "not_found"})

        def do_POST(self) -> None:
            if not self._authorized():
                self._json(401, {"error": "unauthorized"})
                return

            parts = [p for p in urlparse(self.path).path.split("/") if p]
            if len(parts) != 5 or parts[:2] != ["api", "node"]:
                self._json(404, {"error": "not_found"})
                return

            node_id, action, instance = parts[2], parts[3], parts[4]
            try:
                result = fleet.control(node_id, action, instance)
                self._json(200, result)
            except ValueError as exc:
                self._json(400, {"error": "invalid_request", "message": str(exc)})
            except urllib.error.HTTPError as exc:
                self._json(exc.code, {"error": "node_http_error", "message": str(exc)})
            except Exception as exc:
                self._json(502, {"error": "node_unavailable", "message": str(exc)})

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("config", nargs="?", default="nodes.json")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8050)
    args = parser.parse_args()

    fleet = Fleet(Path(args.config))
    server = ThreadingHTTPServer((args.host, args.port), make_handler(fleet))
    print(f"Fleet: http://{args.host}:{args.port} | nos={len(fleet.nodes)}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
