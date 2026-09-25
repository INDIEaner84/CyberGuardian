import json
import os
import secrets
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.control_plane import ControlPlane, NotFoundError


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

    def test_signal_requires_active_decoy_and_documentation_source(self):
        pot = self.plane.create_honeypot("LAB-DECOY", "HTTP decoy", 8080)
        with self.assertRaisesRegex(ValueError, "Standby"):
            self.plane.simulate_signal(pot["id"], "198.51.100.9")
        self.plane.toggle_honeypot(pot["id"], True)
        for source in ("8.8.8.8", "10.0.0.5", "not-an-ip", "2001:4860::8888"):
            with self.assertRaisesRegex(ValueError, "Dokumentationsadresse"):
                self.plane.simulate_signal(pot["id"], source)
        for source in ("192.0.2.1", "198.51.100.200", "203.0.113.7", "2001:db8::5", None):
            result = self.plane.simulate_signal(pot["id"], source)
            self.assertEqual(result["signal"]["incident_id"], result["incident"]["id"])
            self.assertEqual(result["incident"]["signal_id"], result["signal"]["id"])
        with self.assertRaises(NotFoundError):
            self.plane.simulate_signal("HP-NOPE")

    def test_not_found_errors_are_readable_key_errors(self):
        with self.assertRaises(KeyError) as caught:
            self.plane.update_plan("PLN-NOPE", "active")
        self.assertEqual(str(caught.exception), "Plan nicht gefunden: PLN-NOPE")
        with self.assertRaises(NotFoundError):
            self.plane.acknowledge_incident("INC-NOPE")

    def test_plan_status_rules(self):
        plan = self.plane.create_plan("Rules", "Status handling", "orbit", "urgent")
        self.assertEqual(plan["owner"], "ORBIT")
        self.assertEqual(plan["priority"], "normal")  # unknown priorities fall back
        self.assertEqual(self.plane.update_plan(plan["id"], "done")["progress"], 100)
        self.assertEqual(self.plane.update_plan(plan["id"], "active", 250)["progress"], 100)
        self.assertEqual(self.plane.update_plan(plan["id"], None, -5)["progress"], 0)
        with self.assertRaises(ValueError):
            self.plane.update_plan(plan["id"], "exploded")

    def test_register_agent_updates_existing_presence(self):
        self.plane.register_agent("vega", "observer", "handoffs")
        self.plane.register_agent("VEGA", "evidence", "correlation")
        agents = [agent for agent in self.plane.snapshot()["agents"] if agent["name"] == "VEGA"]
        self.assertEqual(len(agents), 1)
        self.assertEqual(agents[0]["role"], "evidence")

    def test_generated_ids_never_collide(self):
        existing = self.plane.snapshot()["plans"][0]["id"]  # e.g. PLN-001
        suffix = existing.split("-", 1)[1]
        tokens = iter([suffix.lower(), suffix.lower(), "beef"])
        real_token_hex = secrets.token_hex

        def token_hex(nbytes):
            return next(tokens, None) or real_token_hex(nbytes)

        with patch("core.control_plane.secrets.token_hex", side_effect=token_hex):
            plan = self.plane.create_plan("Collision", "Deterministic token sequence")
        self.assertEqual(plan["id"], "PLN-BEEF")
        ids = [item["id"] for item in self.plane.snapshot()["plans"]]
        self.assertEqual(len(ids), len(set(ids)))

    def test_tool_run_ids_are_unique(self):
        first = self.plane.record_tool_run({"id": "RUN-1", "tool_id": "config", "summary": "one"})
        second = self.plane.record_tool_run({"id": "RUN-1", "tool_id": "config", "summary": "two"})
        self.assertEqual(first["id"], "RUN-1")
        self.assertNotEqual(second["id"], "RUN-1")

    def test_signal_stats_distinguish_today_and_total(self):
        stats = self.plane.snapshot()["stats"]
        self.assertEqual(stats["signals_total"], 3)
        self.assertLessEqual(stats["signals_today"], stats["signals_total"])

    def test_corrupt_state_is_backed_up_and_reseeded(self):
        path = Path(self.temp_dir.name) / "broken.json"
        path.write_text("{ this is not json", encoding="utf-8")
        plane = ControlPlane(path)
        self.assertEqual(plane.snapshot()["schema"], "cyberguardian-control-plane-v1")
        backups = list(Path(self.temp_dir.name).glob("broken.corrupt-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "{ this is not json")

    def test_unknown_schema_is_not_overwritten_silently(self):
        path = Path(self.temp_dir.name) / "foreign.json"
        path.write_text(json.dumps({"schema": "someone-else-v9", "precious": True}), encoding="utf-8")
        ControlPlane(path)
        backups = list(Path(self.temp_dir.name).glob("foreign.unknown-schema-*.json"))
        self.assertEqual(len(backups), 1)
        self.assertTrue(json.loads(backups[0].read_text(encoding="utf-8"))["precious"])

    def test_missing_collections_are_normalized(self):
        path = Path(self.temp_dir.name) / "partial.json"
        path.write_text(json.dumps({"schema": "cyberguardian-control-plane-v1", "plans": "oops", "agents": [1, {"name": "X"}]}), encoding="utf-8")
        plane = ControlPlane(path)
        state = plane.snapshot()
        self.assertEqual(state["plans"], [])
        self.assertEqual(state["agents"], [{"name": "X"}])
        self.assertEqual(state["tool_states"], {})
        plan = plane.create_plan("Recovered", "Works after normalization")
        self.assertEqual(plane.snapshot()["plans"][0]["id"], plan["id"])

    @unittest.skipIf(os.name == "nt", "POSIX permissions only")
    def test_state_file_is_private_and_leaves_no_temp_files(self):
        self.plane.create_plan("Private", "Permission check")
        mode = stat.S_IMODE(os.stat(self.plane.store_path).st_mode)
        self.assertEqual(mode, 0o600)
        leftovers = [item.name for item in Path(self.temp_dir.name).iterdir() if item.name.endswith(".tmp")]
        self.assertEqual(leftovers, [])


if __name__ == "__main__":
    unittest.main()
