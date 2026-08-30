import unittest
from unittest.mock import patch

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

    def test_capture_profile_is_allowlisted(self):
        with self.assertRaises(ValueError):
            self.ops.capture_metadata(self.interface, preset="arbitrary shell text")


if __name__ == "__main__":
    unittest.main()
