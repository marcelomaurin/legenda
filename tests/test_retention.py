import os
import tempfile
import unittest
from pathlib import Path

from bin.retention import cleanup_directory


class RetentionTests(unittest.TestCase):
    def test_removes_only_old_session_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old.wav"
            fresh = root / "fresh.jsonl"
            keep = root / "keep.txt"
            old.write_bytes(b"1234")
            fresh.write_text("x", encoding="utf-8")
            keep.write_text("x", encoding="utf-8")

            now = 2_000_000
            os.utime(old, (now - 40 * 86400, now - 40 * 86400))
            os.utime(fresh, (now - 2 * 86400, now - 2 * 86400))
            os.utime(keep, (now - 40 * 86400, now - 40 * 86400))

            result = cleanup_directory(root, 30, now=now)

            self.assertFalse(old.exists())
            self.assertTrue(fresh.exists())
            self.assertTrue(keep.exists())
            self.assertEqual(result.removed, 1)
            self.assertEqual(result.bytes_removed, 4)

    def test_dry_run_does_not_remove(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            old = root / "old.srt"
            old.write_text("x", encoding="utf-8")
            now = 2_000_000
            os.utime(old, (now - 40 * 86400, now - 40 * 86400))

            result = cleanup_directory(root, 30, dry_run=True, now=now)

            self.assertTrue(old.exists())
            self.assertEqual(result.removed, 1)


if __name__ == "__main__":
    unittest.main()
