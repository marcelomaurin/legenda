import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bin.fleet_server import Fleet


class FleetTests(unittest.TestCase):
    def make_config(self, root: Path) -> Path:
        path = root / "nodes.json"
        path.write_text(json.dumps({
            "fleet_token": "fleet-secret",
            "timeout_seconds": 1,
            "nodes": [
                {
                    "id": "node-a",
                    "name": "Node A",
                    "url": "http://127.0.0.1:8070",
                    "token": "node-secret"
                }
            ]
        }), encoding="utf-8")
        return path

    def test_loads_nodes(self):
        with tempfile.TemporaryDirectory() as tmp:
            fleet = Fleet(self.make_config(Path(tmp)))
            self.assertEqual(len(fleet.nodes), 1)
            self.assertEqual(fleet.nodes[0]["id"], "node-a")
            self.assertEqual(fleet.api_token, "fleet-secret")

    def test_status_marks_online_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            fleet = Fleet(self.make_config(Path(tmp)))
            with patch.object(fleet, "_request", return_value={
                "instances": [{"name": "sala1", "running": True}]
            }):
                status = fleet.status()
            self.assertTrue(status["nodes"][0]["online"])
            self.assertEqual(status["nodes"][0]["instances"][0]["name"], "sala1")

    def test_status_marks_offline_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            fleet = Fleet(self.make_config(Path(tmp)))
            with patch.object(fleet, "_request", side_effect=OSError("offline")):
                status = fleet.status()
            self.assertFalse(status["nodes"][0]["online"])
            self.assertIn("offline", status["nodes"][0]["error"])

    def test_control_validates_node(self):
        with tempfile.TemporaryDirectory() as tmp:
            fleet = Fleet(self.make_config(Path(tmp)))
            with self.assertRaises(ValueError):
                fleet.control("missing", "restart", "sala")


if __name__ == "__main__":
    unittest.main()
