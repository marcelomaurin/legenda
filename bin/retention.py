#!/usr/bin/env python3
"""Política de retenção para artefatos de sessão do Legenda."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from pathlib import Path


SESSION_EXTENSIONS = {
    ".jsonl", ".srt", ".vtt", ".wav", ".log"
}


@dataclass(slots=True)
class RetentionResult:
    scanned: int = 0
    removed: int = 0
    bytes_removed: int = 0


def cleanup_directory(
    root: Path,
    retention_days: int,
    *,
    dry_run: bool = False,
    now: float | None = None,
) -> RetentionResult:
    result = RetentionResult()
    if retention_days <= 0 or not root.exists():
        return result

    current = time.time() if now is None else now
    cutoff = current - retention_days * 86400

    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in SESSION_EXTENSIONS:
            continue

        result.scanned += 1
        try:
            stat = path.stat()
        except OSError:
            continue

        if stat.st_mtime >= cutoff:
            continue

        result.removed += 1
        result.bytes_removed += stat.st_size
        if not dry_run:
            try:
                path.unlink()
            except OSError:
                result.removed -= 1
                result.bytes_removed -= stat.st_size

    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="transcripts")
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = cleanup_directory(
        Path(args.dir),
        args.days,
        dry_run=args.dry_run,
    )
    mode = "simulação" if args.dry_run else "execução"
    print(
        f"Retenção ({mode}) | analisados={result.scanned} "
        f"| removidos={result.removed} | bytes={result.bytes_removed}"
    )


if __name__ == "__main__":
    main()
