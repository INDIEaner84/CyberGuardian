import json
import tempfile
import unittest
from pathlib import Path

from core.control_plane import ControlPlane


class ControlPlaneTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.plane = ControlPlane(Path(self.temp_dir.name) / "control-plane.json")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_seed_is_defensive_and_shared(self):
        state = self.plane.snapshot()
        self.assertEqual(state["schema"], "cyberguardian-control-plane-v1")
        self.assertTrue(state["settings"]["safe_mode"])
        self.assertTrue(state["settings"]["simulation_mode"])
        self.assertEqual(state["stats"]["total_agents"], 4)

    def test_plan_is_broadcast_and_persisted(self):
        plan = self.plane.create_plan("Evidence Relay", "Review a local fixture", "KAI", "high")
        state = self.plane.snapshot()
        self.assertIn(plan["id"], [item["id"] for item in state["plans"]])
        self.assertEqual(state["messages"][0]["to"], "ALL AGENTS")
        self.assertIn(plan["id"], state["messages"][0]["text"])

        reloaded = ControlPlane(Path(self.temp_dir.name) / "control-plane.json")
        self.assertEqual(reloaded.snapshot()["plans"][0]["title"], "Evidence Relay")

    def test_honeypot_signal_is_synthetic_and_creates_incident(self):
        pot = self.plane.create_honeypot("LAB-DECOY", "HTTP decoy", 8080)
        self.plane.toggle_honeypot(pot["id"], True)
        result = self.plane.simulate_signal(pot["id"], "198.51.100.9", "banner check", "low")
        self.assertTrue(result["signal"]["simulated"])
        self.assertEqual(result["signal"]["action"], "captured / no response")
        self.assertEqual(self.plane.snapshot()["stats"]["open_incidents"], 2)

    def test_invalid_port_is_rejected(self):
        with self.assertRaises(ValueError):
            self.plane.create_honeypot("BAD", "HTTP decoy", 70000)


if __name__ == "__main__":
    unittest.main()
