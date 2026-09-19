#!/usr/bin/env python3
"""Compara resultados JSON produzidos por benchmark_stt.py."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("results", nargs="+")
    parser.add_argument("--csv", default="benchmark_results/comparison.csv")
    args = parser.parse_args()

    rows = []
    for filename in args.results:
        data = json.loads(Path(filename).read_text(encoding="utf-8"))
        rows.append({
            "arquivo": filename,
            "engine": data.get("engine"),
            "model": data.get("model"),
            "device": data.get("device"),
            "samples": data.get("samples"),
            "wer_mean": data.get("wer_mean"),
            "latency_avg_ms": data.get("latency_avg_ms"),
            "latency_p95_ms": data.get("latency_p95_ms"),
            "rtf_mean": data.get("rtf_mean"),
            "audio_total_seconds": data.get("audio_total_seconds"),
            "inference_total_seconds": data.get("inference_total_seconds"),
        })

    print(
        f"{'ENGINE':18} {'MODEL':20} {'DEVICE':10} "
        f"{'WER':>8} {'LAT(ms)':>10} {'P95':>10} {'RTF':>8}"
    )
    print("-" * 92)
    for row in rows:
        print(
            f"{str(row['engine']):18.18} "
            f"{str(row['model']):20.20} "
            f"{str(row['device']):10.10} "
            f"{float(row['wer_mean']):8.4f} "
            f"{float(row['latency_avg_ms']):10.1f} "
            f"{float(row['latency_p95_ms']):10.1f} "
            f"{float(row['rtf_mean']):8.4f}"
        )

    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(rows[0].keys()) if rows else [])
        if rows:
            writer.writeheader()
            writer.writerows(rows)

    print(f"\nComparação salva em: {csv_path}")


if __name__ == "__main__":
    main()
