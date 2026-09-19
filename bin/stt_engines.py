"""Motores de reconhecimento de fala do Legenda v2."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np
import speech_recognition as sr


@dataclass(slots=True)
class TranscriptionResult:
    text: str
    language: str | None = None


class SpeechEngine(ABC):
    @abstractmethod
    def transcribe_pcm(
        self,
        pcm: bytes,
        sample_rate: int,
        sample_width: int = 2,
    ) -> TranscriptionResult:
        raise NotImplementedError


class GoogleSpeechEngine(SpeechEngine):
    def __init__(self, language: str = "pt-BR") -> None:
        self.language = language
        self.recognizer = sr.Recognizer()

    def transcribe_pcm(
        self,
        pcm: bytes,
        sample_rate: int,
        sample_width: int = 2,
    ) -> TranscriptionResult:
        audio = sr.AudioData(pcm, sample_rate, sample_width)
        text = self.recognizer.recognize_google(audio, language=self.language)
        return TranscriptionResult(text=text.strip(), language=self.language)


class FasterWhisperSpeechEngine(SpeechEngine):
    def __init__(self, config: dict[str, Any]) -> None:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise RuntimeError(
                "faster-whisper não está instalado. Execute: pip install -r requirements.txt"
            ) from exc

        self.language = normalize_whisper_language(str(config.get("language", "pt-BR")))
        self.beam_size = int(config.get("whisper_beam_size", 5))
        self.vad_filter = bool(config.get("whisper_vad_filter", True))
        self.vad_min_silence_ms = int(config.get("whisper_vad_min_silence_ms", 300))
        self.hotwords = str(config.get("hotwords", "")).strip() or None

        self.model = WhisperModel(
            str(config.get("whisper_model", "small")),
            device=str(config.get("whisper_device", "cpu")),
            compute_type=str(config.get("whisper_compute_type", "int8")),
        )

    def transcribe_pcm(
        self,
        pcm: bytes,
        sample_rate: int,
        sample_width: int = 2,
    ) -> TranscriptionResult:
        if sample_width != 2:
            raise ValueError("FasterWhisperSpeechEngine espera PCM 16-bit.")

        if sample_rate != 16000:
            raise ValueError("FasterWhisperSpeechEngine espera áudio a 16 kHz.")

        audio = np.frombuffer(pcm, dtype=np.int16).astype(np.float32) / 32768.0

        segments, info = self.model.transcribe(
            audio,
            language=self.language,
            beam_size=self.beam_size,
            vad_filter=self.vad_filter,
            vad_parameters={"min_silence_duration_ms": self.vad_min_silence_ms},
            hotwords=self.hotwords,
            condition_on_previous_text=False,
        )

        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()
        detected_language = getattr(info, "language", None) or self.language
        return TranscriptionResult(text=text, language=detected_language)


def normalize_whisper_language(language: str) -> str:
    language = language.strip().lower()
    if "-" in language:
        language = language.split("-", 1)[0]
    return language or "pt"


def create_engine(config: dict[str, Any]) -> SpeechEngine:
    engine = str(config.get("stt_engine", "google")).strip().lower()

    if engine in {"whisper", "faster-whisper", "faster_whisper"}:
        return FasterWhisperSpeechEngine(config)

    if engine == "google":
        return GoogleSpeechEngine(str(config.get("language", "pt-BR")))

    raise ValueError(f"Motor STT desconhecido: {engine}")
