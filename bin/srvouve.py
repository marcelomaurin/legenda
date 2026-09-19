#!/usr/bin/env python3
"""Servidor Legenda v2 - captura VAD, STT plugável, TCP e WebSocket."""

from __future__ import annotations

import json
import logging
import socket
import threading
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from queue import Empty, Full, Queue
from typing import Any

from stt_engines import SpeechEngine, create_engine
from vad_capture import AudioChunk, VADAudioCapture
from session_export import SessionWaveRecorder, SubtitleExporter

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
    "stt_engine": "faster-whisper",
    "whisper_model": "small",
    "whisper_device": "cpu",
    "whisper_compute_type": "int8",
    "whisper_beam_size": 5,
    "whisper_vad_filter": True,
    "whisper_vad_min_silence_ms": 300,
    "hotwords": "",
    "sample_rate": 16000,
    "vad_frame_ms": 30,
    "vad_mode": 2,
    "vad_padding_ms": 300,
    "vad_start_ratio": 0.6,
    "vad_end_ratio": 0.8,
    "partial_enabled": True,
    "partial_interval_ms": 900,
    "min_partial_ms": 700,
    "min_utterance_ms": 250,
    "max_utterance_ms": 15000,
    "input_device_index": None,
    "queue_size": 100,
    "transcription_queue_size": 8,
    "listen_backlog": 16,
    "save_transcript": True,
    "export_subtitles": True,
    "save_session_audio": True,
    "transcript_dir": "transcripts",
}


@dataclass(slots=True)
class CaptionEvent:
    version: int
    type: str
    session_id: str
    utterance_id: str
    sequence: int
    timestamp: str
    language: str
    text: str
    final: bool
    start_ms: int
    end_ms: int
    latency_ms: int
    engine: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    def to_json_line(self) -> bytes:
        return (self.to_json() + "\n").encode("utf-8")


@dataclass(slots=True)
class TranscriptionJob:
    chunk: AudioChunk
    queued_at: float


class CaptionServer:
    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

        self.clients: set[socket.socket] = set()
        self.clients_lock = threading.Lock()

        self.websocket_clients: set[Any] = set()
        self.websocket_clients_lock = threading.Lock()

        self.events: Queue[CaptionEvent] = Queue(maxsize=int(config["queue_size"]))
        self.transcription_jobs: Queue[TranscriptionJob] = Queue(
            maxsize=int(config["transcription_queue_size"])
        )

        self.stop_event = threading.Event()
        self.server_socket: socket.socket | None = None

        self.session_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
        self.sequence = 0
        self.sequence_lock = threading.Lock()

        self.engine_name = str(config["stt_engine"])
        logging.info("Carregando motor STT: %s", self.engine_name)
        self.engine: SpeechEngine = create_engine(config)

        self.capture = VADAudioCapture(
            sample_rate=int(config["sample_rate"]),
            frame_duration_ms=int(config["vad_frame_ms"]),
            vad_mode=int(config["vad_mode"]),
            padding_ms=int(config["vad_padding_ms"]),
            start_ratio=float(config["vad_start_ratio"]),
            end_ratio=float(config["vad_end_ratio"]),
            partial_interval_ms=int(config["partial_interval_ms"]),
            min_partial_ms=int(config["min_partial_ms"]),
            min_utterance_ms=int(config["min_utterance_ms"]),
            max_utterance_ms=int(config["max_utterance_ms"]),
            input_device_index=config.get("input_device_index"),
        )

        transcript_dir = Path(str(config["transcript_dir"]))
        transcript_dir.mkdir(parents=True, exist_ok=True)
        self.transcript_file = transcript_dir / f"{self.session_id}.jsonl"
        self.subtitle_exporter = (
            SubtitleExporter(transcript_dir, self.session_id)
            if bool(config.get("export_subtitles", True))
            else None
        )
        self.session_recorder = (
            SessionWaveRecorder(
                transcript_dir / f"{self.session_id}.wav",
                sample_rate=int(config["sample_rate"]),
            )
            if bool(config.get("save_session_audio", True))
            else None
        )

    def next_sequence(self) -> int:
        with self.sequence_lock:
            self.sequence += 1
            return self.sequence

    def make_event(
        self,
        chunk: AudioChunk,
        text: str,
        language: str | None,
        latency_ms: int,
    ) -> CaptionEvent:
        return CaptionEvent(
            version=2,
            type="caption" if chunk.final else "partial",
            session_id=self.session_id,
            utterance_id=chunk.utterance_id,
            sequence=self.next_sequence(),
            timestamp=datetime.now().astimezone().isoformat(timespec="milliseconds"),
            language=language or str(self.config["language"]),
            text=text,
            final=chunk.final,
            start_ms=chunk.start_ms,
            end_ms=chunk.end_ms,
            latency_ms=latency_ms,
            engine=self.engine_name,
        )

    def enqueue_event(self, event: CaptionEvent) -> None:
        try:
            self.events.put_nowait(event)
        except Full:
            try:
                self.events.get_nowait()
                self.events.task_done()
            except Empty:
                pass
            self.events.put_nowait(event)
            logging.warning("Fila de eventos cheia: evento mais antigo descartado.")

    def submit_audio(self, chunk: AudioChunk) -> None:
        if not chunk.final and not bool(self.config.get("partial_enabled", True)):
            return

        job = TranscriptionJob(chunk=chunk, queued_at=time.monotonic())

        if chunk.final:
            try:
                self.transcription_jobs.put(job, timeout=2.0)
            except Full:
                logging.error("Fila STT cheia: segmento final não pôde ser enfileirado.")
            return

        try:
            self.transcription_jobs.put_nowait(job)
        except Full:
            logging.debug("Fila STT ocupada: atualização parcial descartada.")

    def transcription_loop(self) -> None:
        sample_rate = int(self.config["sample_rate"])

        while not self.stop_event.is_set():
            try:
                job = self.transcription_jobs.get(timeout=0.5)
            except Empty:
                continue

            started = time.monotonic()
            try:
                result = self.engine.transcribe_pcm(job.chunk.pcm, sample_rate, 2)
                text = result.text.strip()
                if not text:
                    continue

                latency_ms = int((time.monotonic() - started) * 1000)
                event = self.make_event(job.chunk, text, result.language, latency_ms)
                if job.chunk.final and self.session_recorder is not None:
                    self.session_recorder.append(job.chunk.pcm, job.chunk.start_ms)
                self.enqueue_event(event)

                logging.info(
                    "%s [%s] %d ms: %s",
                    "FINAL" if job.chunk.final else "PARTIAL",
                    job.chunk.utterance_id,
                    latency_ms,
                    text,
                )
            except Exception as exc:
                logging.warning(
                    "Falha de transcrição (%s): %s",
                    "final" if job.chunk.final else "partial",
                    exc,
                )
            finally:
                self.transcription_jobs.task_done()

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
            logging.warning("WebSocket desativado: dependência 'websockets' ausente.")
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

    # ---------- persistência / distribuição ----------

    def save_event(self, event: CaptionEvent) -> None:
        if not self.config.get("save_transcript", True) or not event.final:
            return

        with self.transcript_file.open("a", encoding="utf-8") as output:
            output.write(event.to_json() + "\n")

        if self.subtitle_exporter is not None:
            self.subtitle_exporter.append(event)

    def sender_loop(self) -> None:
        while not self.stop_event.is_set():
            try:
                event = self.events.get(timeout=0.5)
            except Empty:
                continue

            try:
                # O Lazarus recebe somente finais; evita piscar texto parcial.
                if event.final:
                    self.broadcast_tcp(event)

                if self.config.get("websocket_enabled", True):
                    self.broadcast_websocket(event)

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
        threading.Thread(target=self.transcription_loop, daemon=True, name="stt-worker").start()

        if self.config.get("websocket_enabled", True):
            threading.Thread(target=self.websocket_loop, daemon=True, name="websocket").start()

        logging.info(
            "Legenda v2 | sessão %s | TCP %s:%s | STT %s",
            self.session_id,
            self.config["host"],
            self.config["port"],
            self.engine_name,
        )

    def listen_forever(self) -> None:
        logging.info(
            "Captura VAD ativa: %s Hz / frames %s ms / modo %s",
            self.config["sample_rate"],
            self.config["vad_frame_ms"],
            self.config["vad_mode"],
        )

        for chunk in self.capture.chunks():
            if self.stop_event.is_set():
                break
            self.submit_audio(chunk)

    def stop(self) -> None:
        self.stop_event.set()

        if self.server_socket is not None:
            try:
                self.server_socket.close()
            except OSError:
                pass

        for client in self.snapshot_clients():
            self.remove_client(client)

        if self.session_recorder is not None:
            try:
                self.session_recorder.close()
            except Exception:
                logging.exception("Falha ao fechar áudio da sessão.")
            self.session_recorder = None


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

    server: CaptionServer | None = None
    try:
        server = CaptionServer(load_config())
        server.start_network()
        server.listen_forever()
    except KeyboardInterrupt:
        logging.info("Encerramento solicitado.")
    except Exception:
        logging.exception("Falha fatal no Legenda.")
        raise
    finally:
        if server is not None:
            server.stop()


if __name__ == "__main__":
    main()
