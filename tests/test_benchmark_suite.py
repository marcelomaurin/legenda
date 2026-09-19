import unittest
from pathlib import Path

from bin.benchmark_suite import build_commands


class BenchmarkSuiteTests(unittest.TestCase):
    def test_builds_enabled_runs(self):
        suite = {
            "manifest": "corpus/manifest.jsonl",
            "config": "config.json",
            "output_dir": "out",
            "runs": [
                {
                    "engine": "faster-whisper",
                    "model": "tiny",
                    "device": "cpu",
                    "compute_type": "int8",
                },
                {
                    "engine": "faster-whisper",
                    "model": "small",
                    "device": "cuda",
                    "enabled": False,
                },
            ],
        }
        commands = build_commands(
            suite,
            python_exe="python",
            project_root=Path("/project"),
        )
        self.assertEqual(len(commands), 1)
        cmd = commands[0]
        self.assertIn("--engine", cmd)
        self.assertIn("faster-whisper", cmd)
        self.assertIn("--model", cmd)
        self.assertIn("tiny", cmd)
        self.assertIn("--compute-type", cmd)
        self.assertIn("int8", cmd)


if __name__ == "__main__":
    unittest.main()
