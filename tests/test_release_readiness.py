import unittest
from pathlib import Path

from bin.release_readiness import check_repo


class ReleaseReadinessTests(unittest.TestCase):
    def test_current_repository_is_structurally_ready(self):
        root = Path(__file__).resolve().parent.parent
        checks = check_repo(root)
        failed = [check.name for check in checks if not check.ok]
        self.assertEqual(failed, [])


if __name__ == "__main__":
    unittest.main()
