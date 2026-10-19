"""Offline replay classifies existing evidence without becoming a live detector."""
import copy
import unittest

from core.detection_replay import MAX_ROWS_PER_SOURCE, replay, rule_catalog


class DetectionReplayTests(unittest.TestCase):
    def test_fixed_rules_keep_observed_and_simulated_evidence_separate(self):
        state = {
            "vm_alerts": [
                {"id": "VM-1", "simulated": False, "rule": "path-discovery", "run_id": "a" * 32},
                {"id": "VM-2", "simulated": False, "rule": "login-retries", "run_id": "b" * 32},
                {"id": "VM-FALSE", "simulated": True, "rule": "path-discovery"},
                {"id": "VM-NEAR", "simulated": False, "rule": "path-discovery-maybe"},
            ],
            "honeypot_logs": [
                {"id": "HP-1", "simulated": True, "tactic": "credential probe"},
                {"id": "HP-2", "simulated": True, "tactic": "path discovery"},
                {"id": "HP-FALSE", "simulated": False, "tactic": "credential probe"},
                {"id": "HP-NEAR", "simulated": True, "tactic": "credential probe attempt"},
            ],
        }
        before = copy.deepcopy(state)
        result = replay(state, limit=10)
        self.assertEqual(result["mode"], "offline-replay")
        self.assertFalse(result["live_detection"])
        self.assertEqual(result["evaluated"], 8)
        self.assertEqual([row["rule_id"] for row in result["matches"]],
                         ["VM-PATH-01", "VM-LOGIN-01", "HP-CRED-01", "HP-PATH-01"])
        self.assertEqual([row["simulated"] for row in result["matches"]], [False, False, True, True])
        self.assertEqual(result["matches"][0]["run_id"], "a" * 32)
        self.assertEqual(state, before)  # no new alert or incident in the source
        self.assertEqual(len(rule_catalog()), 4)
        self.assertEqual(replay(state, source="vm")["match_count"], 2)
        self.assertEqual(replay(state, source="honeypot")["match_count"], 2)

    def test_limits_and_malformed_input_do_not_expand_scope(self):
        rows = [{"id": f"HP-{n}", "simulated": True, "tactic": "credential probe"} for n in range(120)]
        state = {"vm_alerts": [], "honeypot_logs": rows}
        result = replay(state, source="honeypot", limit=MAX_ROWS_PER_SOURCE)
        self.assertEqual(result["evaluated"], 100)
        self.assertEqual(result["match_count"], 100)
        self.assertTrue(result["truncated"])
        for source, limit in (("outside", 20), ([], 20), ("all", 101), ("all", 0), ("all", True), ("all", "40")):
            with self.subTest(source=source, limit=limit), self.assertRaises(ValueError):
                replay(state, source=source, limit=limit)
        with self.assertRaises(ValueError):
            replay({"vm_alerts": "not a list"}, source="vm")
        self.assertEqual(replay({"vm_alerts": [None, {"id": "x", "simulated": False, "rule": "other"}]}, source="vm")["match_count"], 0)


if __name__ == "__main__":
    unittest.main()
