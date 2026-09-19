import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from bin.session_export import SubtitleExporter


class SubtitleExporterTests(unittest.TestCase):
    def test_exports_srt_and_vtt(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            exporter = SubtitleExporter(directory, "sessao")
            event = SimpleNamespace(
                start_ms=1234,
                end_ms=5678,
                text="Olá mundo",
                speaker=None,
            )
            exporter.append(event)

            srt = (directory / "sessao.srt").read_text(encoding="utf-8")
            vtt = (directory / "sessao.vtt").read_text(encoding="utf-8")

            self.assertIn("00:00:01,234 --> 00:00:05,678", srt)
            self.assertIn("Olá mundo", srt)
            self.assertTrue(vtt.startswith("WEBVTT"))
            self.assertIn("00:00:01.234 --> 00:00:05.678", vtt)


if __name__ == "__main__":
    unittest.main()
