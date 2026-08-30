import tempfile
import unittest
from pathlib import Path

from core.control_plane import ControlPlane
from core.defense_ops import DefenseOps
from core.tool_catalog import ToolCatalog


class ToolCatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.plane = ControlPlane(Path(self.temp_dir.name) / "state.json")
        self.catalog = ToolCatalog(self.plane, DefenseOps())

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_every_known_module_has_one_allowlisted_action(self):
        tools = self.catalog.catalog()
        self.assertEqual(len(tools), 15)
        self.assertTrue(all(tool["actions"] for tool in tools))
        self.assertTrue(all("boundary" in tool and "explain" in tool for tool in tools))

    def test_run_is_auditable_and_invalid_action_is_rejected(self):
        run = self.catalog.run("control_plane", "sync_check")
        self.plane.record_tool_run(run)
        self.assertTrue(run["safe"])
        self.assertEqual(self.plane.get_tool_runs(1)[0]["tool_id"], "control_plane")
        with self.assertRaises(ValueError):
            self.catalog.run("control_plane", "arbitrary_shell")

    def test_tool_watch_state_is_persisted(self):
        self.plane.set_tool_state("ids_ips", False)
        item = next(tool for tool in self.catalog.catalog() if tool["id"] == "ids_ips")
        self.assertFalse(item["enabled"])


if __name__ == "__main__":
    unittest.main()
