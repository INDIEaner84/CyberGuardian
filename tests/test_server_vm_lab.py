"""HTTP-level boundary: a connected guest is not enough to authorize tests."""
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from core.control_plane import ControlPlane
from core.vm_lab import VMLab
from lab import guest_sensor
from server import CyberGuardianServer


class ServerVMLabTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        key = root / "secret"
        key.write_text("a" * 64)
        self.key_patch = patch.object(guest_sensor, "KEY_FILE", str(key))
        self.key_patch.start()
        guest_sensor.EVENTS.clear()
        guest_sensor.COUNTS.clear()
        guest_sensor.SEQUENCE = 0
        self.sensor = ThreadingHTTPServer(("127.0.0.1", 0), guest_sensor.Handler)
        self.sensor_thread = threading.Thread(target=self.sensor.serve_forever, daemon=True)
        self.sensor_thread.start()
        self.plane = ControlPlane(root / "state.json")
        self.lab = VMLab(self.plane, key, True, self.sensor.server_port)
        self.operator_token = "operator-" + "b" * 40
        with patch.dict("server.os.environ", {"CYBERGUARDIAN_ENABLE_VM_LAB": "1",
                                              "CYBERGUARDIAN_VM_OPERATOR_TOKEN": self.operator_token}):
            self.server = CyberGuardianServer(("127.0.0.1", 0), self.plane, vm_lab=self.lab)
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.server_thread.join()
        self.sensor.shutdown()
        self.sensor.server_close()
        self.sensor_thread.join()
        self.key_patch.stop()
        self.directory.cleanup()

    def post(self, token="", origin=None, scenario="discovery"):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-VM-Operator-Token"] = token
        if origin:
            headers["Origin"] = origin
        request = Request(f"{self.base}/api/vm-lab/scenarios/{scenario}/run", data=b"{}", headers=headers, method="POST")
        try:
            with urlopen(request, timeout=4) as response:
                return response.status, json.load(response)
        except HTTPError as exc:
            return exc.code, json.load(exc)

    def test_opt_in_without_operator_token_fails_closed(self):
        with patch.dict("server.os.environ", {"CYBERGUARDIAN_ENABLE_VM_LAB": "1",
                                              "CYBERGUARDIAN_VM_OPERATOR_TOKEN": "short"}):
            server = CyberGuardianServer(("127.0.0.1", 0), self.plane)
        try:
            self.assertFalse(server.vm_lab.enabled)
            self.assertEqual(server.vm_operator_token, "")
        finally:
            server.server_close()

    def test_token_same_origin_and_allowlist(self):
        self.assertEqual(self.post()[0], 401)
        self.assertEqual(self.post("wrong")[0], 401)
        self.assertEqual(self.post(self.operator_token, "https://other.invalid")[0], 403)
        self.assertEqual(self.plane.snapshot()["vm_alerts"], [])
        status, result = self.post(self.operator_token, self.base)
        self.assertEqual(status, 201)
        self.assertEqual(result["alerts"][0]["rule"], "path-discovery")
        self.assertNotIn(self.operator_token, json.dumps(self.plane.snapshot()))
        self.assertEqual(self.post(self.operator_token, self.base, "external-host")[0], 400)
        with urlopen(self.base + "/api/tools", timeout=4) as response:
            tools = json.load(response)["tools"]
        self.assertTrue(next(item for item in tools if item["id"] == "vm_lab")["availability"])


if __name__ == "__main__":
    unittest.main()
