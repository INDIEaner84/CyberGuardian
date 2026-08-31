import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from core.defense_ops import DefenseOps


class DefenseOpsTests(unittest.TestCase):
    def setUp(self):
        self.ops = DefenseOps()
        self.interface = self.ops.interfaces()[0]

    def test_simulation_capture_is_bounded_and_metadata_only(self):
        with patch.object(DefenseOps, "_which", return_value=None):
            result = self.ops.capture_metadata(self.interface, duration=99, limit=99, preset="metadata")
        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "simulation")
        self.assertLessEqual(len(result["packets"]), 30)
        self.assertTrue(all(packet["synthetic"] for packet in result["packets"]))

    def test_mac_preview_never_mutates_interface(self):
        result = self.ops.mac_preview(self.interface)
        self.assertFalse(result["mutated"])
        self.assertEqual(len(result["proposed"].split(":")), 6)
        self.assertIn("Vorschau", result["warning"])

    def test_live_capture_requests_only_bounded_metadata(self):
        runner = Mock(return_value=SimpleNamespace(returncode=0, stdout="1.0|192.0.2.10|51834|192.0.2.1|443|TCP\n", stderr=""))
        ops = DefenseOps(command_runner=runner)

        def which(*commands):
            return "/usr/bin/tshark" if "tshark" in commands else None

        with patch.object(DefenseOps, "_which", side_effect=which):
            result = ops.capture_metadata(self.interface, duration=99, limit=99, preset="tcp")

        argv = runner.call_args.args[0]
        self.assertTrue(result["ok"])
        self.assertEqual(result["mode"], "live-metadata")
        self.assertIn("-p", argv)  # no promiscuous mode
        self.assertIn("-T", argv)
        self.assertNotIn("-w", argv)  # never write a capture file/payload
        self.assertEqual(result["packets"][0]["protocol"], "TCP")

    def test_capture_profile_is_allowlisted(self):
        with self.assertRaises(ValueError):
            self.ops.capture_metadata(self.interface, preset="arbitrary shell text")


if __name__ == "__main__":
    unittest.main()
