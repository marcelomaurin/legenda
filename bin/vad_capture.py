"""Captura de áudio com VAD em tempo real para o Legenda v2."""

from __future__ import annotations

import time
import uuid
from collections import deque
from dataclasses import dataclass
from typing import Iterator

import pyaudio
import webrtcvad


@dataclass(slots=True)
class AudioChunk:
    utterance_id: str
    pcm: bytes
    final: bool
    start_ms: int
    end_ms: int


class VADAudioCapture:
    """Segmenta fala usando frames WebRTC VAD de 10/20/30 ms."""

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        vad_mode: int = 2,
        padding_ms: int = 300,
        start_ratio: float = 0.6,
        end_ratio: float = 0.8,
        partial_interval_ms: int = 900,
        min_partial_ms: int = 700,
        min_utterance_ms: int = 250,
        max_utterance_ms: int = 15000,
        input_device_index: int | None = None,
    ) -> None:
        if sample_rate not in {8000, 16000, 32000, 48000}:
            raise ValueError("sample_rate incompatível com WebRTC VAD.")
        if frame_duration_ms not in {10, 20, 30}:
            raise ValueError("frame_duration_ms deve ser 10, 20 ou 30.")

        self.sample_rate = sample_rate
        self.frame_duration_ms = frame_duration_ms
        self.padding_ms = max(padding_ms, frame_duration_ms)
        self.start_ratio = start_ratio
        self.end_ratio = end_ratio
        self.partial_interval_ms = partial_interval_ms
        self.min_partial_ms = min_partial_ms
        self.min_utterance_ms = min_utterance_ms
        self.max_utterance_ms = max_utterance_ms
        self.input_device_index = input_device_index

        self.samples_per_frame = int(sample_rate * frame_duration_ms / 1000)
        self.bytes_per_frame = self.samples_per_frame * 2

        self.vad = webrtcvad.Vad()
        self.vad.set_mode(vad_mode)

    def chunks(self) -> Iterator[AudioChunk]:
        audio = pyaudio.PyAudio()
        stream = audio.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=self.sample_rate,
            input=True,
            frames_per_buffer=self.samples_per_frame,
            input_device_index=self.input_device_index,
        )

        padding_frames = max(1, self.padding_ms // self.frame_duration_ms)
        ring: deque[tuple[bytes, bool]] = deque(maxlen=padding_frames)

        triggered = False
        frames: list[bytes] = []
        utterance_id = ""
        utterance_start = 0.0
        last_partial_at = 0.0
        session_start = time.monotonic()

        try:
            while True:
                frame = stream.read(self.samples_per_frame, exception_on_overflow=False)
                if len(frame) != self.bytes_per_frame:
                    continue

                now = time.monotonic()
                is_speech = self.vad.is_speech(frame, self.sample_rate)

                if not triggered:
                    ring.append((frame, is_speech))
                    voiced = sum(1 for _, speech in ring if speech)

                    if len(ring) == ring.maxlen and voiced / len(ring) >= self.start_ratio:
                        triggered = True
                        utterance_id = uuid.uuid4().hex[:12]
                        utterance_start = now - (len(ring) * self.frame_duration_ms / 1000.0)
                        last_partial_at = now
                        frames = [data for data, _ in ring]
                        ring.clear()
                    continue

                frames.append(frame)
                ring.append((frame, is_speech))

                duration_ms = int((now - utterance_start) * 1000)
                since_partial_ms = int((now - last_partial_at) * 1000)

                if (
                    self.partial_interval_ms > 0
                    and duration_ms >= self.min_partial_ms
                    and since_partial_ms >= self.partial_interval_ms
                ):
                    yield AudioChunk(
                        utterance_id=utterance_id,
                        pcm=b"".join(frames),
                        final=False,
                        start_ms=max(0, int((utterance_start - session_start) * 1000)),
                        end_ms=max(0, int((now - session_start) * 1000)),
                    )
                    last_partial_at = now

                unvoiced = sum(1 for _, speech in ring if not speech)
                end_detected = len(ring) == ring.maxlen and unvoiced / len(ring) >= self.end_ratio
                forced_end = duration_ms >= self.max_utterance_ms

                if end_detected or forced_end:
                    if duration_ms >= self.min_utterance_ms:
                        yield AudioChunk(
                            utterance_id=utterance_id,
                            pcm=b"".join(frames),
                            final=True,
                            start_ms=max(0, int((utterance_start - session_start) * 1000)),
                            end_ms=max(0, int((now - session_start) * 1000)),
                        )

                    triggered = False
                    frames = []
                    ring.clear()
                    utterance_id = ""
        finally:
            stream.stop_stream()
            stream.close()
            audio.terminate()
