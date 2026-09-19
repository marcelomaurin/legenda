#!/usr/bin/env python3
"""Benchmark de STT do Legenda v2.

Formato do manifesto JSONL:
{"audio":"samples/01.wav","reference":"bom dia a todos","id":"01"}
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import time
import wave
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import fmean
from typing import Any


def normalize_text(text: str) -> list[str]:
    cleaned = []
    for ch in text.lower():
        if ch.isalnum() or ch.isspace():
            cleaned.append(ch)
        else:
            cleaned.append(" ")
    return " ".join("".join(cleaned).split()).split()


def levenshtein(ref: list[str], hyp: list[str]) -> int:
    if not ref:
        return len(hyp)
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, start=1):
        curr = [i]
        for j, h in enumerate(hyp, start=1):
            cost = 0 if r == h else 1
            curr.append(min(
                curr[-1] + 1,
                prev[j] + 1,
                prev[j - 1] + cost,
            ))
        prev = curr
    return prev[-1]


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref = normalize_text(reference)
    hyp = normalize_text(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    return levenshtein(ref, hyp) / len(ref)


def read_wav_pcm(path: Path) -> tuple[bytes, int, int, int]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        sample_rate = wf.getframerate()
        sample_width = wf.getsampwidth()
        frames = wf.getnframes()
        pcm = wf.readframes(frames)

    if channels != 1:
        raise ValueError(f"{path}: esperado áudio mono, encontrado {channels} canais")
    if sample_width != 2:
        raise ValueError(f"{path}: esperado PCM 16-bit")
    return pcm, sample_rate, sample_width, frames


@dataclass
class BenchmarkRow:
    id: str
    category: str
    audio: str
    reference: str
    hypothesis: str
    wer: float
    duration_seconds: float
    inference_seconds: float
    rtf: float
    engine: str
    model: str
    device: str


def load_manifest(path: Path) -> list[dict[str, Any]]:
    rows = []
    for idx, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        item.setdefault("id", str(idx))
        rows.append(item)
    return rows


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    pos = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * q)))
    return ordered[pos]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("--config", default="config.json")
    parser.add_argument("--engine", default=None)
    parser.add_argument("--model", default=None)
    parser.add_argument("--device", default=None)
    parser.add_argument("--compute-type", default=None)
    parser.add_argument("--output-dir", default="benchmark_results")
    args = parser.parse_args()

    config_path = Path(args.config)
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}

    if args.engine:
        config["stt_engine"] = args.engine
    if args.model:
        config["whisper_model"] = args.model
    if args.device:
        config["whisper_device"] = args.device
    if args.compute_type:
        config["whisper_compute_type"] = args.compute_type

    engine_name = str(config.get("stt_engine", "google"))
    model_name = str(config.get("whisper_model", "-"))
    device_name = str(config.get("whisper_device", "-"))

    try:
        from .stt_engines import create_engine
    except ImportError:
        from stt_engines import create_engine

    engine = create_engine(config)
    manifest_path = Path(args.manifest)
    items = load_manifest(manifest_path)

    results: list[BenchmarkRow] = []

    for item in items:
        audio_path = Path(item["audio"])
        pcm, sample_rate, sample_width, frames = read_wav_pcm(audio_path)
        duration = frames / sample_rate

        started = time.perf_counter()
        result = engine.transcribe_pcm(pcm, sample_rate, sample_width)
        elapsed = time.perf_counter() - started

        hypothesis = result.text.strip()
        wer = word_error_rate(str(item["reference"]), hypothesis)
        rtf = elapsed / duration if duration > 0 else math.inf

        row = BenchmarkRow(
            id=str(item["id"]),
            category=str(item.get("category", "uncategorized")),
            audio=str(audio_path),
            reference=str(item["reference"]),
            hypothesis=hypothesis,
            wer=wer,
            duration_seconds=duration,
            inference_seconds=elapsed,
            rtf=rtf,
            engine=engine_name,
            model=model_name,
            device=device_name,
        )
        results.append(row)
        print(
            f"[{row.id}] WER={row.wer:.3f} "
            f"tempo={row.inference_seconds:.3f}s RTF={row.rtf:.3f}"
        )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    stamp = time.strftime("%Y%m%d-%H%M%S")
    safe_engine = engine_name.replace("/", "_")
    safe_model = model_name.replace("/", "_")
    base = out_dir / f"{stamp}-{safe_engine}-{safe_model}"

    csv_path = base.with_suffix(".csv")
    json_path = base.with_suffix(".json")

    with csv_path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.DictWriter(out, fieldnames=list(asdict(results[0]).keys()) if results else [])
        if results:
            writer.writeheader()
            for row in results:
                writer.writerow(asdict(row))

    wers = [row.wer for row in results]
    latencies = [row.inference_seconds * 1000 for row in results]
    rtfs = [row.rtf for row in results]

    categories: dict[str, dict[str, Any]] = {}
    for category in sorted({row.category for row in results}):
        subset = [row for row in results if row.category == category]
        subset_wers = [row.wer for row in subset]
        subset_latencies = [row.inference_seconds * 1000 for row in subset]
        subset_rtfs = [row.rtf for row in subset]
        categories[category] = {
            "samples": len(subset),
            "wer_mean": fmean(subset_wers) if subset_wers else None,
            "latency_avg_ms": fmean(subset_latencies) if subset_latencies else None,
            "latency_p95_ms": percentile(subset_latencies, 0.95),
            "rtf_mean": fmean(subset_rtfs) if subset_rtfs else None,
        }

    summary = {
        "engine": engine_name,
        "model": model_name,
        "device": device_name,
        "samples": len(results),
        "wer_mean": fmean(wers) if wers else None,
        "latency_avg_ms": fmean(latencies) if latencies else None,
        "latency_p95_ms": percentile(latencies, 0.95),
        "rtf_mean": fmean(rtfs) if rtfs else None,
        "audio_total_seconds": sum(row.duration_seconds for row in results),
        "inference_total_seconds": sum(row.inference_seconds for row in results),
        "categories": categories,
        "results": [asdict(row) for row in results],
    }

    json_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print()
    print(f"JSON: {json_path}")
    print(f"CSV : {csv_path}")
    if summary["wer_mean"] is not None:
        print(f"WER médio : {summary['wer_mean']:.4f}")
        print(f"RTF médio : {summary['rtf_mean']:.4f}")
        print(f"Latência  : {summary['latency_avg_ms']:.1f} ms")
        print(f"P95       : {summary['latency_p95_ms']:.1f} ms")

        if categories:
            print("\nPor categoria:")
            print(f"{'CATEGORIA':14} {'N':>4} {'WER':>8} {'LAT(ms)':>10} {'P95':>10} {'RTF':>8}")
            print("-" * 60)
            for category, data in categories.items():
                print(
                    f"{category:14.14} "
                    f"{int(data['samples']):4d} "
                    f"{float(data['wer_mean']):8.4f} "
                    f"{float(data['latency_avg_ms']):10.1f} "
                    f"{float(data['latency_p95_ms']):10.1f} "
                    f"{float(data['rtf_mean']):8.4f}"
                )


if __name__ == "__main__":
    main()
