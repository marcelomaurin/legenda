#!/usr/bin/env python3
"""Valida referências e áudios do corpus Legenda v2."""

from __future__ import annotations

import argparse
import json
import wave
from collections import Counter
from pathlib import Path


REQUIRED_CATEGORIES = {
    "clean", "noise", "fast", "distance",
    "names", "acronyms", "technical", "mixed",
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default="corpus")
    args = parser.parse_args()

    root = Path(args.corpus_dir)
    refs_dir = root / "references"
    audio_dir = root / "audio"

    errors = []
    warnings = []
    ids = set()
    categories = Counter()
    speakers = Counter()
    references = []

    for ref_file in sorted(refs_dir.glob("*.jsonl")):
        for lineno, line in enumerate(ref_file.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except Exception as exc:
                errors.append(f"{ref_file}:{lineno}: JSON inválido: {exc}")
                continue

            item_id = str(item.get("id", "")).strip()
            category = str(item.get("category", "")).strip()
            reference = str(item.get("reference", "")).strip()
            speaker = str(item.get("speaker", "")).strip()

            if not item_id:
                errors.append(f"{ref_file}:{lineno}: id ausente")
                continue
            if item_id in ids:
                errors.append(f"{ref_file}:{lineno}: id duplicado: {item_id}")
            ids.add(item_id)

            if category not in REQUIRED_CATEGORIES:
                errors.append(f"{ref_file}:{lineno}: categoria inválida: {category}")
            categories[category] += 1

            if not reference:
                errors.append(f"{ref_file}:{lineno}: referência vazia")
            if speaker:
                speakers[speaker] += 1

            references.append(item)

    for category in REQUIRED_CATEGORIES:
        if categories[category] == 0:
            warnings.append(f"categoria sem referências: {category}")

    wav_count = 0
    invalid_wav = 0
    missing_audio = 0

    for item in references:
        path = audio_dir / item["category"] / f"{item['id']}.wav"
        if not path.exists():
            missing_audio += 1
            continue
        wav_count += 1
        try:
            with wave.open(str(path), "rb") as wf:
                if wf.getnchannels() != 1:
                    errors.append(f"{path}: áudio deve ser mono")
                    invalid_wav += 1
                if wf.getsampwidth() != 2:
                    errors.append(f"{path}: áudio deve ser PCM 16-bit")
                    invalid_wav += 1
                if wf.getframerate() != 16000:
                    warnings.append(f"{path}: sample rate {wf.getframerate()} Hz; recomendado 16000 Hz")
        except Exception as exc:
            errors.append(f"{path}: WAV inválido: {exc}")
            invalid_wav += 1

    print(f"Referências : {len(references)}")
    print(f"Áudios      : {wav_count}")
    print(f"Ausentes    : {missing_audio}")
    print(f"Locutores   : {len(speakers)}")
    print(f"Erros       : {len(errors)}")
    print(f"Avisos      : {len(warnings)}")

    print("\nCategorias:")
    for category in sorted(REQUIRED_CATEGORIES):
        print(f"  {category:10} {categories[category]}")

    if warnings:
        print("\nAvisos:")
        for warning in warnings[:30]:
            print(" -", warning)

    if errors:
        print("\nErros:")
        for error in errors[:30]:
            print(" -", error)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
