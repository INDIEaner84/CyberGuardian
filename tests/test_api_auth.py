"""API auth and VM review HTTP boundaries (no QEMU or extra dependencies)."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from core.control_plane import ControlPlane
from server import CyberGuardianServer


class APIAuthTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.plane = ControlPlane(Path(self.directory.name) / "state.json")
        self.token = "api-" + "c" * 40
        self.viewer = "viewer-" + "v" * 40
        with patch.dict("server.os.environ", {"CYBERGUARDIAN_API_TOKEN": self.token,
                                              "CYBERGUARDIAN_VIEWER_TOKEN": self.viewer,
                                              "CYBERGUARDIAN_ENABLE_VM_LAB": "0"}):
            self.server = CyberGuardianServer(("127.0.0.1", 0), self.plane)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.directory.cleanup()

    def call(self, path, method="GET", token=None, body=None, origin=None):
        headers = {"Content-Type": "application/json"}
        if token is not None:
            headers["Authorization"] = f"Bearer {token}"
        if origin is not None:
            headers["Origin"] = origin
        request = Request(self.base + path, headers=headers, method=method,
                          data=json.dumps(body or {}).encode() if method in {"POST", "PATCH"} else None)
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, json.load(response) if response.status != 204 else {}
        except HTTPError as exc:
            return exc.code, json.load(exc)

    def test_all_api_methods_guarded_and_origin_checked(self):
        self.assertEqual(self.call("/api/auth"), (200, {"required": True}))
        self.assertEqual(self.call("/api/state", "OPTIONS")[0], 401)
        for path in ("/api/state", "/api/health", "/api/tools", "/api/vm-lab", "/api/ops/overview", "/api/unknown"):
            status, payload = self.call(path)
            self.assertEqual((status, payload.get("code")), (401, "api_auth_required"))
        self.assertEqual(self.call("/api/plans", "POST", body={"title": "blocked"})[0], 401)
        self.assertEqual(self.call("/api/plans/PLN-001", "PATCH", body={"status": "done"})[0], 401)
        self.assertEqual(self.call("/api/plans", "POST", token="wrong")[0], 401)
        self.assertEqual(self.call("/api/plans", "POST", token=self.token, origin="https://other.invalid")[0], 403)
        self.assertEqual(self.call("/api/state", token=self.token)[0], 200)
        self.assertEqual(self.call("/api/unknown", token=self.token)[0], 404)
        status, plan = self.call("/api/plans", "POST", token=self.token, origin=self.base, body={"title": "review plan"})
        self.assertEqual(status, 201)
        self.assertEqual(plan["title"], "review plan")
        self.assertNotIn(self.token, json.dumps(self.plane.snapshot()))

    def test_viewer_can_read_but_cannot_write_or_trigger_guest_collection(self):
        self.assertEqual(self.call("/api/session")[0], 401)
        self.assertEqual(self.call("/api/session", token="wrong")[0], 401)
        self.assertEqual(self.call("/api/session", token=self.token),
                         (200, {"role": "operator", "authenticated": True}))
        self.assertEqual(self.call("/api/session", token=self.viewer),
                         (200, {"role": "viewer", "authenticated": True}))
        before = self.plane.snapshot()
        self.server.vm_lab.enabled = True
        with patch.object(self.server.vm_lab, "_request", return_value={"ok": True, "boot_id": "a" * 16}), \
             patch.object(self.server.vm_lab, "_collect", side_effect=AssertionError("viewer collected guest events")):
            for path in ("/api/state", "/api/health", "/api/tools", "/api/vm-lab",
                         "/api/ops/overview", "/api/ops/mac?interface=lo", "/api/detection/rules"):
                self.assertEqual(self.call(path, token=self.viewer)[0], 200, path)
        self.assertEqual(self.plane.snapshot(), before)
        self.assertEqual(self.call("/api/state", "OPTIONS", token=self.viewer)[0], 204)
        for path, method in (("/api/plans", "POST"), ("/api/plans/PLN-001", "PATCH"),
                             ("/api/vm-lab/scenarios/discovery/run", "POST"),
                             ("/api/detection/replay", "POST"), ("/api/evidence/import", "POST"),
                             ("/api/vm-alerts/any/review", "POST"), ("/api/tools/vm_lab/run", "POST"),
                             ("/api/unknown", "POST")):
            status, response = self.call(path, method, token=self.viewer, body={"invalid": True}, origin=self.base)
            self.assertEqual((status, response.get("code")), (403, "read_only"), path)
        # The denial precedes body parsing, VM-key checks and all write handlers.
        malformed = Request(self.base + "/api/plans", method="POST", data=b"not json",
                            headers={"Authorization": f"Bearer {self.viewer}", "Origin": self.base})
        with self.assertRaises(HTTPError) as denied:
            urlopen(malformed, timeout=5)
        self.assertEqual(denied.exception.code, 403)
        denied.exception.close()
        self.assertEqual(self.plane.snapshot(), before)
        self.assertNotIn(self.viewer, json.dumps(self.plane.snapshot()))
        self.assertNotIn(self.viewer, json.dumps(self.call("/api/session", token=self.viewer)))

    def test_viewer_configuration_requires_distinct_valid_operator_key(self):
        for operator, viewer in (("", self.viewer), (self.token, self.token),
                                 (self.token, "short"), (self.token, "ü" * 40),
                                 (self.token, "x" * 32 + " ")):
            with patch.dict("server.os.environ", {"CYBERGUARDIAN_API_TOKEN": operator,
                                                  "CYBERGUARDIAN_VIEWER_TOKEN": viewer,
                                                  "CYBERGUARDIAN_ENABLE_VM_LAB": "0"}):
                with self.assertRaises(ValueError):
                    CyberGuardianServer(("127.0.0.1", 0), self.plane, allow_unauthenticated=True)

    def test_guest_alert_review_audits_without_changing_sensor_evidence(self):
        alert = self.plane.record_vm_alert({"boot_id": "a" * 16, "run_id": "b" * 32,
                                            "seq": 1, "rule": "path-discovery", "observed_at": "2026-10-18T12:00:00Z"})
        path = f"/api/vm-alerts/{alert['id']}/review"
        self.assertEqual(self.call(path, "POST", body={"note": "unbefugt"})[0], 401)
        status, reviewed = self.call(path, "POST", token=self.token, body={"note": "lokal geprüft"})
        self.assertEqual(status, 200)
        self.assertEqual(reviewed["status"], "acknowledged")
        self.assertEqual(reviewed["run_id"], alert["run_id"])
        self.assertEqual(reviewed["observed_at"], alert["observed_at"])
        self.assertEqual(self.call(path, "POST", token=self.token, body={"note": ""})[0], 400)
        self.assertEqual(self.call(path, "POST", token=self.token, body={"note": "x" * 241})[0], 400)
        self.assertEqual(self.call(path, "POST", token=self.token, body={"note": "bad" + chr(0) + "note"})[0], 400)
        self.assertEqual(self.call(path, "POST", token=self.token, body={"note": "zweite Notiz"})[0], 200)
        self.assertEqual(self.call("/api/vm-alerts/" + "c" * 16 + ":1/review", "POST", token=self.token)[0], 404)
        reloaded = ControlPlane(self.plane.store_path).snapshot()["vm_alerts"][0]
        self.assertEqual([entry["action"] for entry in reloaded["reviews"]], ["acknowledged", "note"])
        self.assertNotIn("lokal geprüft", json.dumps(self.plane.snapshot()["activity"]))

    def test_replay_api_is_authenticated_bounded_and_does_not_create_incidents(self):
        self.assertEqual(self.call("/api/detection/rules")[0], 401)
        status, catalog = self.call("/api/detection/rules", token=self.token)
        self.assertEqual(status, 200)
        self.assertEqual(len(catalog["rules"]), 4)
        before = self.plane.snapshot()
        self.assertEqual(self.call("/api/detection/replay", "POST")[0], 401)
        self.assertEqual(self.call("/api/detection/replay", "POST", token=self.token, body={"path": "/etc/passwd"})[0], 400)
        self.assertEqual(self.call("/api/detection/replay", "POST", token=self.token, body={"source": "http://other"})[0], 400)
        self.assertEqual(self.call("/api/detection/replay", "POST", token=self.token, body={"limit": 500})[0], 400)
        status, result = self.call("/api/detection/replay", "POST", token=self.token,
                                   body={"source": "honeypot", "limit": 20})
        self.assertEqual(status, 200)
        self.assertEqual(result["mode"], "offline-replay")
        self.assertFalse(result["live_detection"])
        self.assertTrue(all(item["simulated"] for item in result["matches"]))
        after = self.plane.snapshot()
        self.assertEqual(after["incidents"], before["incidents"])
        self.assertEqual(after["vm_alerts"], before["vm_alerts"])
        self.assertEqual(after["activity"][0]["kind"], "detection.replay")

    def test_offline_import_api_requires_auth_and_only_keeps_metadata(self):
        fixture = (Path(__file__).parent / "fixtures" / "suricata-eve.jsonl").read_text()
        body = {"format": "suricata-eve", "content": fixture}
        before = self.plane.snapshot()
        self.assertEqual(self.call("/api/evidence/import", "POST", body=body)[0], 401)
        self.assertEqual(self.call("/api/evidence/import", "POST", token=self.token, origin="https://other.invalid", body=body)[0], 403)
        self.assertEqual(self.call("/api/evidence/import", "POST", token=self.token,
                                   body={**body, "path": "/tmp/data"})[0], 400)
        self.assertEqual(self.call("/api/evidence/import", "POST", token=self.token,
                                   body={"format": "zeek-notice", "content": fixture})[0], 400)
        status, first = self.call("/api/evidence/import", "POST", token=self.token, origin=self.base, body=body)
        self.assertEqual((status, first["accepted"], first["ignored_unrelated"]), (201, 2, 1))
        status, duplicate = self.call("/api/evidence/import", "POST", token=self.token, body=body)
        self.assertEqual((status, duplicate["accepted"], duplicate["duplicates"]), (200, 0, 2))
        state = self.plane.snapshot()
        self.assertEqual(len(state["imported_alerts"]), 2)
        self.assertEqual(state["vm_alerts"], before["vm_alerts"])
        self.assertEqual(state["incidents"], before["incidents"])
        self.assertNotIn("SECRET_PAYLOAD_DO_NOT_STORE", json.dumps(state))

    def test_non_local_binding_fails_closed_without_api_key(self):
        with patch.dict("server.os.environ", {"CYBERGUARDIAN_API_TOKEN": "",
                                              "CYBERGUARDIAN_ENABLE_VM_LAB": "0"}):
            with self.assertRaises(ValueError):
                CyberGuardianServer(("0.0.0.0", 0), self.plane)
            demo = CyberGuardianServer(("0.0.0.0", 0), self.plane, allow_unauthenticated=True)
            demo.server_close()
        with patch.dict("server.os.environ", {"CYBERGUARDIAN_API_TOKEN": "",
                                              "CYBERGUARDIAN_ENABLE_VM_LAB": "1"}):
            with self.assertRaises(ValueError):
                CyberGuardianServer(("0.0.0.0", 0), self.plane, allow_unauthenticated=True)
        for invalid in ("short", "ü" * 40, "x" * 32 + " "):
            with patch.dict("server.os.environ", {"CYBERGUARDIAN_API_TOKEN": invalid}):
                with self.assertRaises(ValueError):
                    CyberGuardianServer(("127.0.0.1", 0), self.plane)


if __name__ == "__main__":
    unittest.main()
