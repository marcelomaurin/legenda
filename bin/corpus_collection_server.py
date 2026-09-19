#!/usr/bin/env python3
"""Servidor HTTP para coleta assistida do corpus Legenda v2."""

from __future__ import annotations

import argparse
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    from .security_utils import bearer_matches, require_token_for_remote_bind
except ImportError:
    from security_utils import bearer_matches, require_token_for_remote_bind

try:
    from .prepare_corpus_manifest import load_references
except ImportError:
    from prepare_corpus_manifest import load_references


SAFE_ID = re.compile(r"^[A-Za-z0-9._-]+$")


class CorpusCollectionApp:
    def __init__(self, corpus_dir: Path, token: str = "") -> None:
        self.corpus_dir = corpus_dir.resolve()
        self.reference_dir = self.corpus_dir / "references"
        self.audio_dir = self.corpus_dir / "audio"
        self.token = token
        self.references = self._load_reference_index()

    def _load_reference_index(self) -> dict[tuple[str, str], dict[str, Any]]:
        index: dict[tuple[str, str], dict[str, Any]] = {}
        for item in load_references(self.reference_dir):
            key = (str(item["category"]), str(item["id"]))
            index[key] = {
                "id": str(item["id"]),
                "category": str(item["category"]),
                "reference": str(item["reference"]),
                "speaker": str(item.get("speaker", "")),
                "notes": str(item.get("notes", "")),
            }
        return index

    def list_items(self) -> list[dict[str, Any]]:
        items = []
        for (category, item_id), item in sorted(self.references.items()):
            audio_path = self.audio_dir / category / f"{item_id}.wav"
            row = dict(item)
            row["recorded"] = audio_path.exists()
            row["audio_path"] = str(audio_path.relative_to(self.corpus_dir))
            items.append(row)
        return items

    def save_wav(self, category: str, item_id: str, data: bytes) -> Path:
        if not SAFE_ID.fullmatch(category) or not SAFE_ID.fullmatch(item_id):
            raise ValueError("category/id inválido")

        if (category, item_id) not in self.references:
            raise ValueError("referência inexistente")

        if len(data) < 44 or data[:4] != b"RIFF" or data[8:12] != b"WAVE":
            raise ValueError("arquivo enviado não é WAV")

        target_dir = self.audio_dir / category
        target_dir.mkdir(parents=True, exist_ok=True)

        target = (target_dir / f"{item_id}.wav").resolve()
        if self.corpus_dir not in target.parents:
            raise ValueError("caminho inválido")

        target.write_bytes(data)
        return target


def make_handler(app: CorpusCollectionApp):
    class Handler(BaseHTTPRequestHandler):
        server_version = "LegendaCorpusCollector/1.0"

        def log_message(self, fmt: str, *args: Any) -> None:
            print("[corpus]", fmt % args)

        def _authorized(self) -> bool:
            if not app.token:
                return True
            return bearer_matches(
                self.headers.get("Authorization", ""),
                app.token,
            )

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
            if path == "/api/references":
                app.references = app._load_reference_index()
                self._json(200, {"items": app.list_items()})
                return

            self._json(404, {"error": "not_found"})

        def do_POST(self) -> None:
            if not self._authorized():
                self._json(401, {"error": "unauthorized"})
                return

            parts = [p for p in urlparse(self.path).path.split("/") if p]
            if len(parts) != 4 or parts[:2] != ["api", "audio"]:
                self._json(404, {"error": "not_found"})
                return

            category, item_id = parts[2], parts[3]
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0:
                    raise ValueError("arquivo vazio")
                if length > 20 * 1024 * 1024:
                    raise ValueError("arquivo excede 20 MB")

                content_type = self.headers.get("Content-Type", "")
                if "audio/wav" not in content_type and "audio/wave" not in content_type:
                    raise ValueError("Content-Type deve ser audio/wav")

                data = self.rfile.read(length)
                target = app.save_wav(category, item_id, data)
                self._json(200, {
                    "status": "saved",
                    "category": category,
                    "id": item_id,
                    "path": str(target.relative_to(app.corpus_dir)),
                    "bytes": len(data),
                })
            except ValueError as exc:
                self._json(400, {"error": "invalid_upload", "message": str(exc)})
            except Exception as exc:
                self._json(500, {"error": "save_failed", "message": str(exc)})

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default="corpus")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8060)
    parser.add_argument("--token", default="")
    args = parser.parse_args()

    app = CorpusCollectionApp(Path(args.corpus_dir), args.token)
    require_token_for_remote_bind(args.host, args.token, "corpus-collector")
    server = ThreadingHTTPServer((args.host, args.port), make_handler(app))

    print(f"Corpus collector: http://{args.host}:{args.port}")
    print(f"Referências: {len(app.references)}")
    print(f"Auth: {'on' if args.token else 'off'}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
