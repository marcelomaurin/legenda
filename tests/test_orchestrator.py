import json
import tempfile
import unittest
from pathlib import Path

from bin.orchestrator import Orchestrator


class OrchestratorTests(unittest.TestCase):
    def test_builds_instance_configs_relative_to_definition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = root / "base.json"
            base.write_text(json.dumps({
                "room_auth_secret": "1234567890123456",
                "stt_engine": "google",
                "port": 8097
            }), encoding="utf-8")

            definition = root / "instances.json"
            definition.write_text(json.dumps({
                "base_config": "base.json",
                "runtime_dir": ".runtime",
                "instances": [{
                    "name": "sala1",
                    "overrides": {
                        "active_room": "sala1",
                        "port": 8197,
                        "input_device_index": 3
                    }
                }]
            }), encoding="utf-8")

            orchestrator = Orchestrator(definition)
            self.assertEqual(len(orchestrator.instances), 1)

            generated = json.loads(
                orchestrator.instances[0].config_path.read_text(encoding="utf-8")
            )

            self.assertEqual(generated["stt_engine"], "google")
            self.assertEqual(generated["active_room"], "sala1")
            self.assertEqual(generated["port"], 8197)
            self.assertEqual(generated["input_device_index"], 3)
            self.assertTrue(str(orchestrator.instances[0].config_path).startswith(str(root)))


if __name__ == "__main__":
    unittest.main()
