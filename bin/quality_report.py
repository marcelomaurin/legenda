#!/usr/bin/env python3
"""Gera relatório HTML consolidado a partir dos JSONs de benchmark do Legenda."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path
from statistics import fmean
from typing import Any


def load_results(directory: Path) -> list[dict[str, Any]]:
    rows = []
    for path in sorted(directory.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "wer_mean" not in data or "rtf_mean" not in data:
            continue
        data["_file"] = str(path)
        rows.append(data)
    return rows


def fmt(value: Any, digits: int = 3, suffix: str = "") -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.{digits}f}{suffix}"
    except Exception:
        return html.escape(str(value))


def category_summary(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for run in results:
        label = f"{run.get('engine', '-')}/{run.get('model', '-')}/{run.get('device', '-')}"
        for category, values in (run.get("categories") or {}).items():
            grouped.setdefault(category, []).append({
                "label": label,
                "wer": values.get("wer_mean"),
                "latency": values.get("latency_avg_ms"),
                "p95": values.get("latency_p95_ms"),
                "rtf": values.get("rtf_mean"),
                "samples": values.get("samples"),
            })
    return grouped


def render_report(results: list[dict[str, Any]], title: str) -> str:
    if not results:
        body = """
        <section class="empty">
          <h2>Nenhum resultado medido encontrado</h2>
          <p>Execute <code>bin/benchmark_stt.py</code> e gere arquivos JSON em
          <code>benchmark_results/</code>. Este relatório não cria valores fictícios.</p>
        </section>
        """
        summary_cards = ""
        category_html = ""
    else:
        wers = [float(r["wer_mean"]) for r in results if r.get("wer_mean") is not None]
        rtfs = [float(r["rtf_mean"]) for r in results if r.get("rtf_mean") is not None]
        lats = [float(r["latency_avg_ms"]) for r in results if r.get("latency_avg_ms") is not None]

        summary_cards = f"""
        <section class="cards">
          <div class="card"><span>Execuções</span><strong>{len(results)}</strong></div>
          <div class="card"><span>WER médio das execuções</span><strong>{fmt(fmean(wers) if wers else None, 4)}</strong></div>
          <div class="card"><span>RTF médio</span><strong>{fmt(fmean(rtfs) if rtfs else None, 4)}</strong></div>
          <div class="card"><span>Latência média</span><strong>{fmt(fmean(lats) if lats else None, 1, " ms")}</strong></div>
        </section>
        """

        table_rows = []
        for r in sorted(results, key=lambda x: (
            float(x.get("wer_mean") if x.get("wer_mean") is not None else 999),
            float(x.get("rtf_mean") if x.get("rtf_mean") is not None else 999),
        )):
            table_rows.append(
                "<tr>"
                f"<td>{html.escape(str(r.get('engine', '-')))}</td>"
                f"<td>{html.escape(str(r.get('model', '-')))}</td>"
                f"<td>{html.escape(str(r.get('device', '-')))}</td>"
                f"<td>{html.escape(str(r.get('samples', '-')))}</td>"
                f"<td>{fmt(r.get('wer_mean'), 4)}</td>"
                f"<td>{fmt(r.get('latency_avg_ms'), 1)}</td>"
                f"<td>{fmt(r.get('latency_p95_ms'), 1)}</td>"
                f"<td>{fmt(r.get('rtf_mean'), 4)}</td>"
                "</tr>"
            )

        body = f"""
        <section class="panel">
          <h2>Comparação global</h2>
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Engine</th><th>Modelo</th><th>Device</th><th>N</th><th>WER</th><th>Lat. média ms</th><th>P95 ms</th><th>RTF</th></tr>
              </thead>
              <tbody>{''.join(table_rows)}</tbody>
            </table>
          </div>
        </section>
        """

        category_blocks = []
        for category, rows in sorted(category_summary(results).items()):
            category_rows = []
            for row in sorted(rows, key=lambda x: (
                float(x["wer"] if x["wer"] is not None else 999),
                float(x["rtf"] if x["rtf"] is not None else 999),
            )):
                category_rows.append(
                    "<tr>"
                    f"<td>{html.escape(row['label'])}</td>"
                    f"<td>{html.escape(str(row.get('samples', '-')))}</td>"
                    f"<td>{fmt(row.get('wer'), 4)}</td>"
                    f"<td>{fmt(row.get('latency'), 1)}</td>"
                    f"<td>{fmt(row.get('p95'), 1)}</td>"
                    f"<td>{fmt(row.get('rtf'), 4)}</td>"
                    "</tr>"
                )
            category_blocks.append(f"""
            <section class="panel">
              <h2>Categoria: {html.escape(category)}</h2>
              <div class="table-wrap">
                <table>
                  <thead>
                    <tr><th>Configuração</th><th>N</th><th>WER</th><th>Lat. média ms</th><th>P95 ms</th><th>RTF</th></tr>
                  </thead>
                  <tbody>{''.join(category_rows)}</tbody>
                </table>
              </div>
            </section>
            """)
        category_html = "".join(category_blocks)

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{ color-scheme: light dark; }}
* {{ box-sizing: border-box; }}
body {{ margin:0; font-family:system-ui,-apple-system,"Segoe UI",sans-serif; background:Canvas; color:CanvasText; }}
header {{ padding:1.2rem 1.5rem; border-bottom:1px solid color-mix(in srgb,CanvasText 18%,transparent); }}
main {{ width:min(1500px,96vw); margin:1.4rem auto 3rem; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(210px,1fr)); gap:1rem; margin-bottom:1rem; }}
.card,.panel,.empty {{ border:1px solid color-mix(in srgb,CanvasText 18%,transparent); border-radius:.8rem; padding:1rem; margin-bottom:1rem; }}
.card span {{ display:block; opacity:.7; }}
.card strong {{ display:block; font-size:2rem; margin-top:.3rem; }}
.table-wrap {{ overflow:auto; }}
table {{ width:100%; border-collapse:collapse; }}
th,td {{ text-align:left; padding:.55rem .45rem; border-bottom:1px solid color-mix(in srgb,CanvasText 12%,transparent); white-space:nowrap; }}
code {{ padding:.1rem .25rem; border-radius:.25rem; background:color-mix(in srgb,CanvasText 10%,transparent); }}
.note {{ opacity:.72; }}
</style>
</head>
<body>
<header>
  <h1>{html.escape(title)}</h1>
  <div class="note">WER menor é melhor. RTF abaixo de 1 indica processamento mais rápido que o tempo real.</div>
</header>
<main>
{summary_cards}
{body}
{category_html}
</main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", default="benchmark_results")
    parser.add_argument("--output", default="benchmark_results/report.html")
    parser.add_argument("--title", default="Legenda v2 — Relatório consolidado de qualidade")
    args = parser.parse_args()

    results = load_results(Path(args.input_dir))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(results, args.title), encoding="utf-8")

    print(f"Execuções carregadas: {len(results)}")
    print(f"Relatório: {output}")


if __name__ == "__main__":
    main()
