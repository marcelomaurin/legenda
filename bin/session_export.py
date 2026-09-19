"""Exportadores SRT/WebVTT e gravação temporal da sessão."""

from __future__ import annotations

import json
import wave
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Any


def _fmt_srt(ms: int) -> str:
    h, rem = divmod(max(ms, 0), 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d},{milli:03d}"


def _fmt_vtt(ms: int) -> str:
    h, rem = divmod(max(ms, 0), 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, milli = divmod(rem, 1_000)
    return f"{h:02d}:{m:02d}:{s:02d}.{milli:03d}"


class SubtitleExporter:
    def __init__(self, transcript_dir: Path, session_id: str) -> None:
        self.srt_path = transcript_dir / f"{session_id}.srt"
        self.vtt_path = transcript_dir / f"{session_id}.vtt"
        self.index = 0
        if not self.vtt_path.exists():
            self.vtt_path.write_text("WEBVTT\n\n", encoding="utf-8")

    def append(self, event: Any) -> None:
        self.index += 1
        speaker = getattr(event, "speaker", None)
        text = event.text
        if speaker:
            text = f"{speaker}: {text}"

        with self.srt_path.open("a", encoding="utf-8") as out:
            out.write(
                f"{self.index}\n"
                f"{_fmt_srt(event.start_ms)} --> {_fmt_srt(event.end_ms)}\n"
                f"{text}\n\n"
            )

        with self.vtt_path.open("a", encoding="utf-8") as out:
            out.write(
                f"{_fmt_vtt(event.start_ms)} --> {_fmt_vtt(event.end_ms)}\n"
                f"{text}\n\n"
            )


class SessionWaveRecorder:
    """Grava PCM final preservando a linha do tempo via start_ms."""

    def __init__(self, path: Path, sample_rate: int = 16000) -> None:
        self.path = path
        self.sample_rate = sample_rate
        self.sample_width = 2
        self.channels = 1
        self.frames_written = 0
        self.wave = wave.open(str(path), "wb")
        self.wave.setnchannels(self.channels)
        self.wave.setsampwidth(self.sample_width)
        self.wave.setframerate(self.sample_rate)

    def append(self, pcm: bytes, start_ms: int) -> None:
        target_frame = int(start_ms * self.sample_rate / 1000)
        if target_frame > self.frames_written:
            gap_frames = target_frame - self.frames_written
            self.wave.writeframesraw(b"\x00" * gap_frames * self.sample_width)
            self.frames_written += gap_frames

        pcm_frames = len(pcm) // self.sample_width

        if target_frame < self.frames_written:
            overlap = self.frames_written - target_frame
            if overlap >= pcm_frames:
                return
            pcm = pcm[overlap * self.sample_width:]
            pcm_frames -= overlap

        self.wave.writeframesraw(pcm)
        self.frames_written += pcm_frames

    def close(self) -> None:
        self.wave.close()
