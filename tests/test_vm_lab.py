import base64
import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.request import ProxyHandler

from core.control_plane import ControlPlane
from core.vm_lab import VMLab
from lab import guest_sensor, vm


class VMLabTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        root = Path(self.directory.name)
        self.key = root / "secret"
        self.key.write_text("a" * 64, encoding="ascii")
        self.plane = ControlPlane(root / "state.json")
        guest_sensor.EVENTS.clear()
        guest_sensor.COUNTS.clear()
        guest_sensor.SEQUENCE = 0
        self.key_patch = patch.object(guest_sensor, "KEY_FILE", str(self.key))
        self.key_patch.start()
        self.sensor = ThreadingHTTPServer(("127.0.0.1", 0), guest_sensor.Handler)
        self.thread = threading.Thread(target=self.sensor.serve_forever, daemon=True)
        self.thread.start()
        self.lab = VMLab(self.plane, self.key, True, self.sensor.server_port)

    def tearDown(self):
        self.sensor.shutdown()
        self.sensor.server_close()
        self.thread.join()
        self.key_patch.stop()
        self.directory.cleanup()

    def test_guest_reports_only_observed_thresholds_and_deduplicates(self):
        self.assertTrue(self.lab.status()["connected"])
        self.assertEqual(self.lab.run("baseline")["alerts"], [])
        discovery = self.lab.run("discovery")
        retries = self.lab.run("retries")
        self.assertEqual([alert["rule"] for alert in discovery["alerts"]], ["path-discovery"])
        self.assertEqual([alert["rule"] for alert in retries["alerts"]], ["login-retries"])
        self.assertFalse(retries["alerts"][0]["simulated"])
        self.lab.status()
        self.lab.status()
        reloaded = ControlPlane(self.plane.store_path)
        self.assertEqual(len(reloaded.snapshot()["vm_alerts"]), 2)
        self.assertEqual(reloaded.snapshot()["vm_alerts"][0]["severity"], "high")

    def test_guest_key_never_uses_host_proxy(self):
        self.assertFalse(any(isinstance(handler, ProxyHandler) for handler in self.lab._opener.handlers))
        self.assertTrue(self.lab.status()["connected"])

    def test_no_arbitrary_scenario_or_disabled_execution(self):
        with self.assertRaises(ValueError):
            self.lab.run("http://other-host")
        disabled = VMLab(self.plane, self.key, False, self.sensor.server_port)
        self.assertFalse(disabled.status()["connected"])
        with self.assertRaises(RuntimeError):
            disabled.run("discovery")
        self.assertEqual(self.plane.snapshot()["vm_alerts"], [])

    def test_sensor_requires_key_and_alert_validation(self):
        with patch.object(self.lab, "key_file", Path(self.directory.name) / "missing"):
            self.assertFalse(self.lab.status()["connected"])
        with self.assertRaises(ValueError):
            self.plane.record_vm_alert({"boot_id": "0" * 16, "run_id": "0" * 32,
                                        "seq": 1, "rule": "arbitrary"})


class VMProvisionTests(unittest.TestCase):
    def test_cloud_init_keeps_key_private_and_guest_network_bounded(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            image = root / "trusted.qcow2"
            image.write_bytes(b"fixture")
            with patch.object(vm, "DATA", root / "lab"), patch.object(vm, "need", side_effect=lambda binary: binary), \
                 patch.object(vm.subprocess, "run") as runner:
                vm.prepare(image)
                user_data = (root / "lab" / "user-data").read_text()
                self.assertIn("#cloud-config", user_data)
                self.assertIn("guest_sensor.py", user_data)
                self.assertIn('"ssh_pwauth": false', user_data)
                config = json.loads(user_data.split("\n", 1)[1])
                files = {item["path"]: item for item in config["write_files"]}
                unit = base64.b64decode(files["/etc/systemd/system/cyberguardian-sensor.service"]["content"])
                self.assertTrue(unit.startswith(b"[Unit]\nDescription="))
                self.assertEqual(files["/etc/cyberguardian-lab.key"]["permissions"], "0640")
                self.assertEqual((root / "lab" / "secret").stat().st_mode & 0o777, 0o600)
                self.assertEqual((root / "lab").stat().st_mode & 0o777, 0o700)
                self.assertEqual(runner.call_count, 2)
                with self.assertRaises(SystemExit):
                    vm.prepare(image)  # never overwrite a guest/key
                runner.reset_mock()
                with patch.object(vm, "DATA", root / "lab"), patch.object(vm, "need", return_value="qemu-system-x86_64"), \
                     patch.object(vm.Path, "exists", return_value=False):
                    # fake generated artifacts because subprocess is mocked
                    (root / "lab" / "guest.qcow2").touch()
                    (root / "lab" / "seed.iso").touch()
                    vm.run()
                args = runner.call_args.args[0]
                self.assertIn("user,id=lab,restrict=on,hostfwd=tcp:127.0.0.1:18081-:8081", args)
                self.assertIn("-snapshot", args)


if __name__ == "__main__":
    unittest.main()
