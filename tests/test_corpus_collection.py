import json
import tempfile
import unittest
import wave
from pathlib import Path

from bin.corpus_collection_server import CorpusCollectionApp


def make_wav() -> bytes:
    import io
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 160)
    return buffer.getvalue()


class CorpusCollectionTests(unittest.TestCase):
    def test_lists_and_saves_known_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            refs = root / "references"
            refs.mkdir(parents=True)
            (refs / "clean.jsonl").write_text(
                json.dumps({
                    "id": "clean-001",
                    "category": "clean",
                    "reference": "bom dia",
                    "speaker": "speaker-01",
                }, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            app = CorpusCollectionApp(root)
            items = app.list_items()
            self.assertEqual(len(items), 1)
            self.assertFalse(items[0]["recorded"])

            target = app.save_wav("clean", "clean-001", make_wav())
            self.assertTrue(target.exists())
            self.assertTrue(app.list_items()[0]["recorded"])

    def test_rejects_unknown_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "references").mkdir(parents=True)
            app = CorpusCollectionApp(root)
            with self.assertRaises(ValueError):
                app.save_wav("clean", "clean-999", make_wav())

    def test_rejects_non_wav(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            refs = root / "references"
            refs.mkdir(parents=True)
            (refs / "clean.jsonl").write_text(
                json.dumps({
                    "id": "clean-001",
                    "category": "clean",
                    "reference": "bom dia"
                }) + "\n",
                encoding="utf-8",
            )
            app = CorpusCollectionApp(root)
            with self.assertRaises(ValueError):
                app.save_wav("clean", "clean-001", b"not-a-wav")


if __name__ == "__main__":
    unittest.main()
