import json
import tempfile
import unittest
from pathlib import Path

from bin.quality_report import category_summary, load_results, render_report


class QualityReportTests(unittest.TestCase):
    def test_loads_only_benchmark_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "valid.json").write_text(json.dumps({
                "engine": "faster-whisper",
                "model": "small",
                "device": "cpu",
                "wer_mean": 0.1,
                "rtf_mean": 0.2,
                "latency_avg_ms": 300,
                "latency_p95_ms": 450,
                "samples": 3,
                "categories": {}
            }), encoding="utf-8")
            (root / "other.json").write_text(json.dumps({"foo": "bar"}), encoding="utf-8")

            results = load_results(root)
            self.assertEqual(len(results), 1)

    def test_category_summary(self):
        grouped = category_summary([{
            "engine": "faster-whisper",
            "model": "small",
            "device": "cpu",
            "categories": {
                "clean": {
                    "wer_mean": 0.05,
                    "latency_avg_ms": 100,
                    "latency_p95_ms": 120,
                    "rtf_mean": 0.1,
                    "samples": 2
                }
            }
        }])
        self.assertIn("clean", grouped)
        self.assertEqual(grouped["clean"][0]["samples"], 2)

    def test_empty_report_does_not_invent_results(self):
        rendered = render_report([], "Relatório")
        self.assertIn("Nenhum resultado medido encontrado", rendered)


if __name__ == "__main__":
    unittest.main()
