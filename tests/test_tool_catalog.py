import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.control_plane import ControlPlane, NotFoundError
from core.defense_ops import DefenseOps
from core.tool_catalog import ToolCatalog, _decode_proc_address


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

    def test_every_allowlisted_action_completes_and_is_json_serializable(self):
        with patch.dict(os.environ, {"CYBERGUARDIAN_DATA_DIR": self.temp_dir.name}):
            for tool in self.catalog.catalog():
                for action in tool["actions"]:
                    with self.subTest(tool=tool["id"], action=action["id"]):
                        run = self.catalog.run(tool["id"], action["id"])
                        self.assertEqual(run["status"], "completed", run.get("error"))
                        self.assertTrue(run["safe"])
                        json.dumps(run)  # must be storable in the shared state
                        self.plane.record_tool_run(run)
        self.assertEqual(len(self.plane.get_tool_runs(120)), 15)

    def test_unknown_tool_is_not_found(self):
        with self.assertRaises(NotFoundError):
            self.catalog.run("does_not_exist", "anything")
        self.assertFalse(self.catalog.has_tool("does_not_exist"))
        self.assertTrue(self.catalog.has_tool("port_manager"))

    def test_proc_net_addresses_are_decoded(self):
        self.assertEqual(_decode_proc_address("0100007F"), "127.0.0.1")
        self.assertEqual(_decode_proc_address("00000000"), "0.0.0.0")
        self.assertEqual(_decode_proc_address("00000000000000000000000001000000"), "::1")
        self.assertEqual(_decode_proc_address("B80D0120000000000000000001000000"), "2001:db8::1")
        tcp = (
            "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
            "   0: 0100007F:104D 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 1 1\n"
            "   1: 0100007F:A1B2 0100007F:104D 01 00000000:00000000 00:00000000 00000000  1000        0 2 1\n"
        )
        ports = ToolCatalog._parse_proc_net_tcp(tcp)
        self.assertEqual(ports, [{"address": "127.0.0.1", "port": 4173, "protocol": "TCP", "source": "/proc/net/tcp"}])

    def test_listening_ports_merge_ipv4_and_ipv6(self):
        header = "  sl  local_address rem_address   st\n"
        proc = Path(self.temp_dir.name) / "net"
        proc.mkdir()
        (proc / "tcp").write_text(header + "   0: 00000000:0016 00000000:0000 0A\n", encoding="ascii")
        (proc / "tcp6").write_text(header + "   0: 00000000000000000000000001000000:104D 00000000000000000000000000000000:0000 0A\n", encoding="ascii")
        ports = self.catalog._listening_ports(proc)
        self.assertEqual([(item["address"], item["port"], item["protocol"]) for item in ports], [("0.0.0.0", 22, "TCP"), ("::1", 4173, "TCP6")])

    def test_baseline_and_backups_follow_data_dir(self):
        data_dir = Path(self.temp_dir.name) / "data"
        (data_dir / "backups").mkdir(parents=True)
        (data_dir / "baseline.json").write_text("{}", encoding="utf-8")
        (data_dir / "backups" / "2026-09-25.tar").write_text("x", encoding="utf-8")
        with patch.dict(os.environ, {"CYBERGUARDIAN_DATA_DIR": str(data_dir)}):
            baseline = self.catalog.run("file_integrity", "baseline_status")
            backups = self.catalog.run("backup_rollback", "backup_inventory")
        self.assertTrue(baseline["details"]["exists"])
        self.assertEqual(backups["details"]["files"], ["2026-09-25.tar"])


if __name__ == "__main__":
    unittest.main()
