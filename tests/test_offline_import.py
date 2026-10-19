"""Bounded metadata-only imports from local JSONL fixtures."""
import json
import tempfile
import unittest
from pathlib import Path

from core.control_plane import ControlPlane
from core.detection_replay import replay
from core.offline_import import MAX_ALERTS, MAX_IMPORT_BYTES, MAX_LINES, parse_import

FIXTURES = Path(__file__).parent / "fixtures"


class OfflineImportTests(unittest.TestCase):
    def test_suricata_alerts_only_and_deduplication(self):
        content = (FIXTURES / "suricata-eve.jsonl").read_text()
        parsed = parse_import("suricata-eve", content)
        self.assertEqual(parsed["ignored_unrelated"], 1)
        self.assertEqual(len(parsed["records"]), 2)
        self.assertEqual([row["severity"] for row in parsed["records"]], ["medium", "high"])
        self.assertEqual(parsed["records"][1]["source_ip"], "2001:db8::10")
        self.assertFalse(parsed["records"][0]["verified"])
        self.assertFalse(parsed["records"][0]["live"])
        self.assertNotIn("SECRET_PAYLOAD", json.dumps(parsed))
        self.assertNotIn("/private/example", json.dumps(parsed))
        with tempfile.TemporaryDirectory() as directory:
            plane = ControlPlane(Path(directory) / "state.json")
            before = plane.snapshot()
            first = plane.import_offline_alerts(parsed["records"], parsed["format"], parsed["ignored_unrelated"])
            again = plane.import_offline_alerts(parsed["records"], parsed["format"], parsed["ignored_unrelated"])
            self.assertEqual((first["accepted"], again["accepted"], again["duplicates"]), (2, 0, 2))
            state = ControlPlane(plane.store_path).snapshot()
            self.assertEqual(len(state["imported_alerts"]), 2)
            self.assertEqual(state["vm_alerts"], before["vm_alerts"])
            self.assertEqual(state["incidents"], before["incidents"])
            self.assertEqual(replay(state)["match_count"], replay(before)["match_count"])
            self.assertEqual(state["activity"][0]["kind"], "evidence.import")
            self.assertNotIn("SECRET_PAYLOAD", json.dumps(state))

    def test_zeek_notice_fields_are_allowlisted(self):
        content = (FIXTURES / "zeek-notice.jsonl").read_text()
        parsed = parse_import("zeek-notice", content)
        self.assertEqual(len(parsed["records"]), 2)
        self.assertEqual(parsed["records"][0]["signature"], "Scan::Port_Scan")
        self.assertEqual(parsed["records"][1]["destination_ip"], "—")
        self.assertTrue(parsed["records"][0]["sensor_timestamp"].endswith("Z"))
        self.assertNotIn("PRIVATE_MESSAGE", json.dumps(parsed))
        self.assertNotIn("PRIVATE_USER", json.dumps(parsed))

    def test_limits_schema_and_unrelated_events_fail_closed(self):
        alert = json.loads((FIXTURES / "suricata-eve.jsonl").read_text().splitlines()[0])
        cases = [
            ("unknown", json.dumps(alert)),
            ("suricata-eve", ""),
            ("suricata-eve", "x" * (MAX_IMPORT_BYTES + 1)),
            ("suricata-eve", ("{}\n" * (MAX_LINES + 1))),
            ("suricata-eve", json.dumps({"event_type": "flow"})),
            ("suricata-eve", "[1,2,3]"),
            ("suricata-eve", "{broken"),
            ("suricata-eve", json.dumps({**alert, "src_ip": "http://outside"})),
            ("suricata-eve", json.dumps({**alert, "timestamp": "2026-10-18T12:00:00"})),
            ("suricata-eve", json.dumps({**alert, "alert": {"signature": "x", "severity": True}})),
            ("suricata-eve", json.dumps(alert) + "\n" + json.dumps({**alert, "dest_ip": "bad"})),
            ("zeek-notice", json.dumps({"ts": float("nan"), "note": "Scan::Port_Scan", "src": "192.0.2.1"})),
            ("zeek-notice", json.dumps({"ts": 1792324800, "note": "x" * 101, "src": "192.0.2.1"})),
        ]
        for fmt, content in cases:
            with self.subTest(fmt=fmt, content=content[:35]), self.assertRaises(ValueError):
                parse_import(fmt, content)
        with self.assertRaises(ValueError):
            parse_import("suricata-eve", (json.dumps(alert) + "\n") * (MAX_ALERTS + 1))
        with self.assertRaises(ValueError):
            parse_import("suricata-eve", json.dumps({**alert, "payload_printable": "x" * 2100}))


if __name__ == "__main__":
    unittest.main()
