import json
import tempfile
import unittest
from pathlib import Path

from bin.prepare_corpus_manifest import load_references


class CorpusTests(unittest.TestCase):
    def test_load_references(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            refs = root / "references"
            refs.mkdir()
            (refs / "clean.jsonl").write_text(
                json.dumps({
                    "id": "clean-001",
                    "category": "clean",
                    "reference": "bom dia",
                    "speaker": "speaker-01"
                }, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )

            items = load_references(refs)
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["id"], "clean-001")
            self.assertEqual(items[0]["category"], "clean")
            self.assertIn("_source", items[0])


if __name__ == "__main__":
    unittest.main()
