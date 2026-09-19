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
            self.assertTrue(orchestrator.instances[0].config_path.resolve().is_relative_to(root.resolve()))

            status = orchestrator.status_snapshot()
            self.assertEqual(status["type"], "orchestrator_status")
            self.assertEqual(len(status["instances"]), 1)
            self.assertEqual(status["instances"][0]["name"], "sala1")
            self.assertFalse(status["instances"][0]["running"])
            self.assertTrue(status["instances"][0]["desired_running"])

    def test_stop_marks_instance_as_not_desired(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "instances.json").write_text(json.dumps({
                "instances": [{"name": "sala1", "overrides": {}}]
            }), encoding="utf-8")

            orchestrator = Orchestrator(root / "instances.json")
            instance = orchestrator.instances[0]
            orchestrator.stop(instance, disable_restart=True)
            self.assertFalse(instance.desired_running)

    def test_preserves_runtime_audio_device_across_restart(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            definition = root / "instances.json"
            definition.write_text(json.dumps({
                "runtime_dir": ".runtime",
                "instances": [{
                    "name": "sala1",
                    "overrides": {"input_device_index": 1}
                }]
            }), encoding="utf-8")

            first = Orchestrator(definition)
            runtime = first.instances[0].config_path
            current = json.loads(runtime.read_text(encoding="utf-8"))
            current["input_device_index"] = 7
            runtime.write_text(json.dumps(current), encoding="utf-8")

            second = Orchestrator(definition)
            rebuilt = json.loads(
                second.instances[0].config_path.read_text(encoding="utf-8")
            )
            self.assertEqual(rebuilt["input_device_index"], 7)

    def test_can_reset_runtime_settings_from_definition(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            definition = root / "instances.json"
            definition.write_text(json.dumps({
                "runtime_dir": ".runtime",
                "instances": [{
                    "name": "sala1",
                    "overrides": {"input_device_index": 1}
                }]
            }), encoding="utf-8")

            first = Orchestrator(definition)
            runtime = first.instances[0].config_path
            current = json.loads(runtime.read_text(encoding="utf-8"))
            current["input_device_index"] = 7
            runtime.write_text(json.dumps(current), encoding="utf-8")

            definition.write_text(json.dumps({
                "runtime_dir": ".runtime",
                "reset_runtime_settings": True,
                "instances": [{
                    "name": "sala1",
                    "overrides": {"input_device_index": 1}
                }]
            }), encoding="utf-8")

            second = Orchestrator(definition)
            rebuilt = json.loads(
                second.instances[0].config_path.read_text(encoding="utf-8")
            )
            self.assertEqual(rebuilt["input_device_index"], 1)


if __name__ == "__main__":
    unittest.main()
