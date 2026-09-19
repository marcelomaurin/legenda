#!/usr/bin/env python3
"""Pós-processa uma sessão Legenda com pyannote Community-1."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_events(path: Path) -> list[dict[str, Any]]:
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            events.append(json.loads(line))
    return events


def overlap_ms(a0: int, a1: int, b0: int, b1: int) -> int:
    return max(0, min(a1, b1) - max(a0, b0))


def extract_turns(diarization: Any) -> list[tuple[int, int, str]]:
    turns: list[tuple[int, int, str]] = []
    if hasattr(diarization, "itertracks"):
        iterator = (
            (turn, speaker)
            for turn, _, speaker in diarization.itertracks(yield_label=True)
        )
    else:
        iterator = iter(diarization)

    for turn, speaker in iterator:
        turns.append(
            (int(turn.start * 1000), int(turn.end * 1000), str(speaker))
        )
    return turns


def assign_speakers(
    events: list[dict[str, Any]],
    turns: list[tuple[int, int, str]],
) -> list[dict[str, Any]]:
    for event in events:
        start_ms = int(event.get("start_ms", 0))
        end_ms = int(event.get("end_ms", start_ms))
        best_speaker = None
        best_overlap = 0

        for t0, t1, speaker in turns:
            ov = overlap_ms(start_ms, end_ms, t0, t1)
            if ov > best_overlap:
                best_overlap = ov
                best_speaker = speaker

        event["speaker"] = best_speaker

    return events


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("session", help="ID da sessão ou caminho base sem extensão")
    parser.add_argument("--dir", default="transcripts")
    parser.add_argument("--token", default=None)
    parser.add_argument(
        "--model",
        default="pyannote/speaker-diarization-community-1",
    )
    args = parser.parse_args()

    base_dir = Path(args.dir)
    session_id = Path(args.session).stem
    wav_path = base_dir / f"{session_id}.wav"
    jsonl_path = base_dir / f"{session_id}.jsonl"

    if not wav_path.exists() or not jsonl_path.exists():
        raise SystemExit("Sessão não encontrada (.wav + .jsonl necessários).")

    try:
        from pyannote.audio import Pipeline
    except ImportError as exc:
        raise SystemExit(
            "Instale as dependências de diarização: "
            "pip install -r requirements-diarization.txt"
        ) from exc

    pipeline = Pipeline.from_pretrained(args.model, token=args.token)
    output = pipeline(str(wav_path))

    diarization = getattr(output, "exclusive_speaker_diarization", None)
    if diarization is None:
        diarization = output.speaker_diarization

    turns = extract_turns(diarization)
    events = assign_speakers(load_events(jsonl_path), turns)

    out_jsonl = base_dir / f"{session_id}.diarized.jsonl"
    with out_jsonl.open("w", encoding="utf-8") as out:
        for event in events:
            out.write(json.dumps(event, ensure_ascii=False) + "\n")

    try:
        from .session_export import SubtitleExporter
    except ImportError:
        from session_export import SubtitleExporter
    exporter = SubtitleExporter(base_dir, session_id + ".diarized")
    for event in events:
        class Obj:
            pass
        obj = Obj()
        for k, v in event.items():
            setattr(obj, k, v)
        exporter.append(obj)

    print(f"Diarização concluída: {out_jsonl}")


if __name__ == "__main__":
    main()
