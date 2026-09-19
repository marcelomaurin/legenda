#!/usr/bin/env python3
"""Servidor Legenda v2.

Captura áudio, reconhece fala e distribui eventos de legenda em JSON Lines/TCP
e WebSocket. O protocolo foi desenhado para suportar futuramente VAD,
transcrição incremental, diarização, tradução e múltiplos motores STT.
"""

from __future__ import annotations

import json
import logging
import socket
import threading
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from queue import Empty, Full, Queue
from typing import Any

import speech_recognition as sr

try:
    from websockets.sync.server import serve as websocket_serve
except ImportError:
    websocket_serve = None


DEFAULT_CONFIG: dict[str, Any] = {
    "host": "0.0.0.0",
    "port": 8097,
    "websocket_enabled": True,
    "websocket_port": 8098,
    "language": "pt-BR",
    "phrase_time_limit": 5,
    "ambient_noise_duration": 1.0,
    "pause_threshold": 0.8,
    "queue_size": 100,
    "listen_backlog": 16,
    "save_transcript": True,
    "transcript_dir": "transcripts",
}


@dataclass(slots=True)
class CaptionEvent:
    version: int
    type: str
    session_id: str
    sequence: int
    timestamp: str
    language: str
    text: str
    final: bool = True

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    def to_json_line(self) -> bytes:
        return (self.to_json() + "\n").encode("utf-8")


class CaptionServer:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config
        self.recognizer = sr.Recognizer()

        self.clients: set[socket.socket] = set()
        self.clients_lock = threading.Lock()

        self.websocket_clients: set[Any] = set()
        self.websocket_clients_lock = threading.Lock()

        self.events: Queue[CaptionEvent] = Queue(maxsize=int(config["queue_size"]))
        self.stop_event = threading.Event()
        self.server_socket: socket.socket | None = None

        self.session_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
        self.sequence = 0
        self.sequence_lock = threading.Lock()

        transcript_dir = Path(str(config["transcript_dir"]))
        transcript_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_file = transcript_dir / f"{self.session_id}.jsonl"

    def next_sequence(self) -> int:
        with self.sequence_lock:
            self.sequence += 1
            return self.sequence

    def make_event(self, text: str, event_type: str = "caption", final: bool = True) -> CaptionEvent:
        return CaptionEvent(
            version=2,
            type=event_type,
            session_id=self.session_id,
            sequence=self.next_sequence(),
            timestamp=datetime.now().astimezone().isoformat(timespec="milliseconds"),
            language=str(self.config["language"]),
            text=text,
            final=final,
        )

    def enqueue(self, event: CaptionEvent) -> None:
        try:
            self.events.put_nowait(event)
        except Full:
            try:
                self.events.get_nowait()
                self.events.task_done()
            except Empty:
                pass
            self.events.put_nowait(event)
            logging.warning("Fila cheia: evento mais antigo descartado.")

    # ---------- TCP ----------

    def add_client(self, client: socket.socket) -> None:
        with self.clients_lock:
            self.clients.add(client)

    def remove_client(self, client: socket.socket) -> None:
        with self.clients_lock:
            self.clients.discard(client)
        try:
            client.close()
        except OSError:
            pass

    def snapshot_clients(self) -> list[socket.socket]:
        with self.clients_lock:
            return list(self.clients)

    def broadcast_tcp(self, event: CaptionEvent) -> None:
        payload = event.to_json_line()
        for client in self.snapshot_clients():
            try:
                client.sendall(payload)
            except OSError:
                self.remove_client(client)

    def client_loop(self, client: socket.socket, address: tuple[str, int]) -> None:
        logging.info("Cliente TCP conectado: %s:%s", *address)
        client.settimeout(1.0)
        try:
            while not self.stop_event.is_set():
                try:
                    data = client.recv(1024)
                    if not data:
                        break
                    # Reservado para futuros comandos do cliente.
                except socket.timeout:
                    continue
                except OSError:
                    break
        finally:
            self.remove_client(client)
            logging.info("Cliente TCP desconectado: %s:%s", *address)

    def accept_loop(self) -> None:
        assert self.server_socket is not None
        while not self.stop_event.is_set():
            try:
                client, address = self.server_socket.accept()
            except OSError:
                if self.stop_event.is_set():
                    break
                raise

            client.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
            self.add_client(client)
            threading.Thread(
                target=self.client_loop,
                args=(client, address),
                daemon=True,
                name=f"tcp-{address[0]}-{address[1]}",
            ).start()

    # ---------- WebSocket ----------

    def websocket_handler(self, connection: Any) -> None:
        with self.websocket_clients_lock:
            self.websocket_clients.add(connection)
        logging.info("Cliente WebSocket conectado.")

        try:
            for _message in connection:
                # Canal reservado para comandos futuros (idioma, sala, etc.).
                if self.stop_event.is_set():
                    break
        except Exception as exc:
            logging.debug("WebSocket encerrado: %s", exc)
        finally:
            with self.websocket_clients_lock:
                self.websocket_clients.discard(connection)
            logging.info("Cliente WebSocket desconectado.")

    def websocket_loop(self) -> None:
        if websocket_serve is None:
            logging.warning(
                "WebSocket desativado: instale a dependência 'websockets' do requirements.txt."
            )
            return

        host = str(self.config["host"])
        port = int(self.config["websocket_port"])
        try:
            with websocket_serve(self.websocket_handler, host, port) as server:
                logging.info("WebSocket disponível em ws://%s:%s", host, port)
                server.serve_forever()
        except Exception as exc:
            logging.error("Falha no servidor WebSocket: %s", exc)

    def broadcast_websocket(self, event: CaptionEvent) -> None:
        payload = event.to_json()
        with self.websocket_clients_lock:
            connections = list(self.websocket_clients)

        for connection in connections:
            try:
                connection.send(payload)
            except Exception:
                with self.websocket_clients_lock:
                    self.websocket_clients.discard(connection)

    # ---------- eventos / persistência ----------

    def save_event(self, event: CaptionEvent) -> None:
        if not self.config.get("save_transcript", True):
            return

        with self.transcript_file.open("a", encoding="utf-8") as output:
            output.write(event.to_json() + "\n")

    def sender_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                event = self.events.get(timeout=0.5)
            except Empty:
                continue

            try:
                self.broadcast_tcp(event)
                if self.config.get("websocket_enabled", True):
                    self.broadcast_websocket(event)
                if event.final:
                    self.save_event(event)
            finally:
                self.events.task_done()

    # ---------- inicialização ----------

    def start_network(self) -> None:
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((str(self.config["host"]), int(self.config["port"])))
        self.server_socket.listen(int(self.config["listen_backlog"]))

        threading.Thread(target=self.accept_loop, daemon=True, name="tcp-accept").start()
        threading.Thread(target=self.sender_loop, daemon=True, name="caption-sender").start()

        if self.config.get("websocket_enabled", True):
            threading.Thread(target=self.websocket_loop, daemon=True, name="websocket").start()

        logging.info(
            "Legenda v2 TCP em %s:%s | sessão %s",
            self.config["host"],
            self.config["port"],
            self.session_id,
        )

    def listen_forever(self) -> None:
        self.recognizer.pause_threshold = float(self.config["pause_threshold"])

        with sr.Microphone() as source:
            logging.info("Ajustando ruído ambiente...")
            self.recognizer.adjust_for_ambient_noise(
                source,
                duration=float(self.config["ambient_noise_duration"]),
            )
            logging.info("Reconhecimento ativo (%s).", self.config["language"])

            while not self.stop_event.is_set():
                try:
                    audio = self.recognizer.listen(
                        source,
                        phrase_time_limit=float(self.config["phrase_time_limit"]),
                    )
                    text = self.recognizer.recognize_google(
                        audio,
                        language=str(self.config["language"]),
                    ).strip()

                    if text:
                        logging.info("Legenda: %s", text)
                        self.enqueue(self.make_event(text))
                except sr.UnknownValueError:
                    logging.debug("Áudio não compreendido.")
                except sr.RequestError as exc:
                    logging.error("Falha no serviço de reconhecimento: %s", exc)
                except OSError as exc:
                    logging.error("Falha de áudio: %s", exc)

    def stop(self) -> None:
        self.stop_event.set()

        if self.server_socket is not None:
            try:
                self.server_socket.close()
            except OSError:
                pass

        for client in self.snapshot_clients():
            self.remove_client(client)


def load_config(path: str = "config.json") -> dict[str, Any]:
    config = DEFAULT_CONFIG.copy()
    config_path = Path(path)

    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as source:
            user_config = json.load(source)
        config.update(user_config)

    return config


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    server = CaptionServer(load_config())
    server.start_network()

    try:
        server.listen_forever()
    except KeyboardInterrupt:
        logging.info("Encerramento solicitado.")
    finally:
        server.stop()


if __name__ == "__main__":
    main()
