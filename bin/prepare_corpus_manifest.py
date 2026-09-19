#!/usr/bin/env python3
"""Gera manifesto de benchmark a partir do corpus de referência."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def load_references(reference_dir: Path) -> list[dict]:
    items = []
    for path in sorted(reference_dir.glob("*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            item = json.loads(line)
            item["_source"] = str(path)
            items.append(item)
    return items


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus-dir", default="corpus")
    parser.add_argument("--output", default="corpus/manifest.jsonl")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    corpus_dir = Path(args.corpus_dir)
    reference_dir = corpus_dir / "references"
    audio_root = corpus_dir / "audio"

    refs = load_references(reference_dir)
    manifest = []
    missing = []

    for item in refs:
        category = str(item["category"])
        item_id = str(item["id"])
        audio_path = audio_root / category / f"{item_id}.wav"

        if not audio_path.exists():
            missing.append(str(audio_path))
            continue

        manifest.append({
            "id": item_id,
            "category": category,
            "audio": str(audio_path),
            "reference": str(item["reference"]),
            "speaker": str(item.get("speaker", "")),
            "notes": str(item.get("notes", "")),
        })

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as out:
        for item in manifest:
            out.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"Referências encontradas : {len(refs)}")
    print(f"Amostras com áudio      : {len(manifest)}")
    print(f"Áudios ausentes         : {len(missing)}")
    print(f"Manifesto               : {output}")

    if missing:
        print("\nPrimeiros arquivos ausentes:")
        for path in missing[:20]:
            print(" -", path)

    if args.strict and missing:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
