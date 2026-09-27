"""HTTP-level tests: a real CyberGuardianServer on an ephemeral port with a temp state file."""

import contextlib
import http.client
import io
import json
import os
import re
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from core.control_plane import ControlPlane
from core.defense_ops import DefenseOps
from server import WEB_ROOT, CyberGuardianHandler, CyberGuardianServer, HostPolicy, build_parser


class OfflineDefenseOps(DefenseOps):
    """Deterministic adapter: no capture tools installed → synthetic metadata only."""

    @staticmethod
    def _which(*commands):
        return None


class ServerTestCase(unittest.TestCase):
    allowed_hosts = ()

    @classmethod
    def setUpClass(cls):
        cls.quiet = [
            patch.object(CyberGuardianHandler, "log_message", lambda *args, **kwargs: None),
            patch.object(CyberGuardianHandler, "log_error", lambda *args, **kwargs: None),
        ]
        for quiet in cls.quiet:
            quiet.start()
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.plane = ControlPlane(Path(cls.temp_dir.name) / "state.json")
        cls.server = CyberGuardianServer(
            ("127.0.0.1", 0), cls.plane, defense_ops=OfflineDefenseOps(), allowed_hosts=cls.allowed_hosts
        )
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.temp_dir.cleanup()
        for quiet in cls.quiet:
            quiet.stop()

    def request(self, method, path, body=None, headers=None, raw=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        final_headers = {}
        payload = raw
        if body is not None:
            payload = json.dumps(body).encode("utf-8")
            final_headers["Content-Type"] = "application/json"
        final_headers.update(headers or {})
        try:
            connection.request(method, path, body=payload, headers=final_headers)
            response = connection.getresponse()
            data = response.read()
        finally:
            connection.close()
        content_type = response.getheader("Content-Type", "")
        parsed = json.loads(data) if data and content_type.startswith("application/json") else data
        return response.status, parsed, response


class ApiTests(ServerTestCase):
    def test_health_and_security_headers(self):
        status, body, response = self.request("GET", "/api/health")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])
        self.assertIn("default-src 'self'", response.getheader("Content-Security-Policy"))
        self.assertEqual(response.getheader("X-Content-Type-Options"), "nosniff")
        self.assertEqual(response.getheader("Cache-Control"), "no-store")
        self.assertNotIn("Python", response.getheader("Server"))

    def test_state_snapshot_has_schema_and_stats(self):
        status, body, _ = self.request("GET", "/api/state")
        self.assertEqual(status, 200)
        self.assertEqual(body["schema"], "cyberguardian-control-plane-v1")
        self.assertIn("signals_total", body["stats"])
        self.assertIn("signals_today", body["stats"])

    def test_unknown_api_route_is_json_404(self):
        for method, path, payload in (("GET", "/api/does-not-exist", None), ("POST", "/api/nope", {}), ("PATCH", "/api/nope", {})):
            status, body, response = self.request(method, path, payload)
            self.assertEqual(status, 404, path)
            self.assertIn("application/json", response.getheader("Content-Type"))
            self.assertIn("error", body)

    def test_static_shell_assets_and_client_routes(self):
        status, body, response = self.request("GET", "/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", response.getheader("Content-Type"))
        self.assertIn(b"CYBERGUARDIAN", body)
        self.assertEqual(self.request("GET", "/styles.css")[2].getheader("Content-Type"), "text/css; charset=utf-8")
        self.assertIn("javascript", self.request("GET", "/app.js")[2].getheader("Content-Type"))
        self.assertEqual(self.request("GET", "/themes.css")[2].getheader("Content-Type"), "text/css; charset=utf-8")
        self.assertIn("javascript", self.request("GET", "/theme-boot.js")[2].getheader("Content-Type"))
        self.assertIn("text/html", self.request("GET", "/ops")[2].getheader("Content-Type"))
        self.assertEqual(self.request("GET", "/missing-file.js")[0], 404)

    def test_every_bundled_font_is_served(self):
        css = "".join((WEB_ROOT / name).read_text(encoding="utf-8") for name in ("styles.css", "themes.css"))
        fonts = sorted(set(re.findall(r"url\('(fonts/[^']+\.woff2)'\)", css)))
        self.assertGreaterEqual(len(fonts), 19)
        for font in fonts:
            status, body, response = self.request("GET", f"/{font}")
            self.assertEqual(status, 200, font)
            self.assertEqual(response.getheader("Content-Type"), "font/woff2")
            self.assertEqual(body[:4], b"wOF2", font)

    def test_head_request_has_headers_but_no_body(self):
        status, body, response = self.request("HEAD", "/")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"")
        self.assertGreater(int(response.getheader("Content-Length")), 0)

    def test_path_traversal_is_blocked(self):
        for path in ("/../server.py", "/%2e%2e/server.py", "/..%2fserver.py", "/fonts/../../server.py"):
            status, body, _ = self.request("GET", path)
            self.assertEqual(status, 404, path)
            self.assertNotIn("ThreadingHTTPServer", json.dumps(body) if isinstance(body, dict) else body.decode("utf-8", "replace"))

    def test_plan_lifecycle(self):
        status, plan, _ = self.request("POST", "/api/plans", {"title": "Evidence Relay", "objective": "Korrelation", "owner": "kai", "priority": "high"})
        self.assertEqual(status, 201)
        self.assertEqual(plan["owner"], "KAI")
        self.assertEqual(plan["status"], "queued")
        status, updated, _ = self.request("PATCH", f"/api/plans/{plan['id']}", {"status": "done"})
        self.assertEqual(status, 200)
        self.assertEqual(updated["progress"], 100)
        self.assertEqual(self.request("PATCH", f"/api/plans/{plan['id']}", {"status": "exploded"})[0], 400)
        status, body, _ = self.request("PATCH", "/api/plans/PLN-NOPE", {"status": "active"})
        self.assertEqual(status, 404)
        self.assertEqual(body["error"], "Plan nicht gefunden: PLN-NOPE")

    def test_write_requests_require_json_content_type(self):
        before = len(self.plane.snapshot()["plans"])
        for content_type, raw in (("text/plain", b'{"title": "csrf"}'), ("application/x-www-form-urlencoded", b"title=csrf"), ("multipart/form-data; boundary=x", b"--x--")):
            status, body, _ = self.request("POST", "/api/plans", raw=raw, headers={"Content-Type": content_type})
            self.assertEqual(status, 415, content_type)
        self.assertEqual(self.request("POST", "/api/ops/proxy-check", raw=b"")[0], 415)
        self.assertEqual(len(self.plane.snapshot()["plans"]), before)

    def test_cross_site_writes_are_rejected(self):
        own_origin = f"http://127.0.0.1:{self.port}"
        blocked = ({"Sec-Fetch-Site": "cross-site"}, {"Sec-Fetch-Site": "same-site"}, {"Origin": "https://evil.example"}, {"Origin": "null"})
        for headers in blocked:
            self.assertEqual(self.request("POST", "/api/messages", {"text": "csrf"}, headers=headers)[0], 403, headers)
        allowed = ({"Origin": own_origin}, {"Sec-Fetch-Site": "same-origin", "Origin": own_origin}, {})
        for headers in allowed:
            self.assertEqual(self.request("POST", "/api/messages", {"text": "legit"}, headers=headers)[0], 201, headers)
        texts = [message["text"] for message in self.plane.snapshot()["messages"]]
        self.assertNotIn("csrf", texts)

    def test_dns_rebinding_hosts_are_rejected(self):
        self.assertEqual(self.request("GET", "/api/state", headers={"Host": "attacker.example:4173"})[0], 403)
        self.assertEqual(self.request("GET", "/", headers={"Host": "rebind.attacker.example"})[0], 403)
        self.assertEqual(self.request("GET", "/api/state", headers={"Host": f"localhost:{self.port}"})[0], 200)

    def test_body_validation_and_limits(self):
        json_header = {"Content-Type": "application/json"}
        self.assertEqual(self.request("POST", "/api/messages", raw=b"{not json", headers=json_header)[0], 400)
        status, body, _ = self.request("POST", "/api/messages", raw=b"[1, 2]", headers=json_header)
        self.assertEqual(status, 400)
        self.assertIn("JSON-Objekt", body["error"])
        oversized = json.dumps({"text": "a" * 70_000}).encode("utf-8")
        self.assertEqual(self.request("POST", "/api/messages", raw=oversized, headers=json_header)[0], 413)
        self.assertEqual(self.request("POST", "/api/messages", {"text": "   "})[0], 400)

    def test_honeypot_flow_is_simulation_only(self):
        status, pot, _ = self.request("POST", "/api/honeypots", {"name": "test-vault", "service": "HTTP decoy", "port": 8081})
        self.assertEqual(status, 201)
        self.assertEqual(pot["status"], "standby")
        self.assertEqual(self.request("POST", f"/api/honeypots/{pot['id']}/simulate", {"source": "198.51.100.5"})[0], 400)
        status, toggled, _ = self.request("POST", f"/api/honeypots/{pot['id']}/toggle", {"active": True})
        self.assertEqual(toggled["status"], "active")
        self.assertEqual(self.request("POST", f"/api/honeypots/{pot['id']}/simulate", {"source": "8.8.8.8"})[0], 400)
        status, result, _ = self.request(
            "POST", f"/api/honeypots/{pot['id']}/simulate", {"source": "198.51.100.5", "tactic": "banner check", "severity": "high"}
        )
        self.assertEqual(status, 201)
        self.assertTrue(result["signal"]["simulated"])
        self.assertEqual(result["signal"]["incident_id"], result["incident"]["id"])
        status, acked, _ = self.request("POST", f"/api/incidents/{result['incident']['id']}/ack", {})
        self.assertEqual(status, 200)
        self.assertEqual(acked["status"], "acknowledged")
        self.assertEqual(self.request("POST", "/api/incidents/INC-NOPE/ack", {})[0], 404)
        self.assertEqual(self.request("POST", "/api/honeypots/HP-NOPE/toggle", {"active": True})[0], 404)
        self.assertEqual(self.request("POST", "/api/honeypots", {"name": "bad", "port": 70000})[0], 400)

    def test_agents_and_messages_are_shared(self):
        status, agent, _ = self.request("POST", "/api/agents", {"name": "vega", "role": "Evidence", "focus": "handoffs"})
        self.assertEqual(status, 201)
        self.assertEqual(agent["name"], "VEGA")
        state = self.request("GET", "/api/state")[1]
        self.assertIn("VEGA", [item["name"] for item in state["agents"]])
        status, message, _ = self.request("POST", "/api/messages", {"sender": "VEGA", "recipient": "ALL AGENTS", "text": "Übergabe bereit"})
        self.assertEqual(status, 201)
        self.assertEqual(message["text"], "Übergabe bereit")

    def test_tool_endpoints_are_allowlisted(self):
        status, body, _ = self.request("GET", "/api/tools")
        self.assertEqual(status, 200)
        self.assertEqual(len(body["tools"]), 15)
        status, run, _ = self.request("POST", "/api/tools/control_plane/run", {"action": "sync_check"})
        self.assertEqual(status, 201)
        self.assertEqual(run["status"], "completed")
        self.assertEqual(self.request("POST", "/api/tools/control_plane/run", {"action": "rm -rf /"})[0], 400)
        self.assertEqual(self.request("POST", "/api/tools/unknown/run", {"action": "x"})[0], 404)
        status, watch, _ = self.request("POST", "/api/tools/ids_ips/toggle", {"enabled": False})
        self.assertEqual(status, 200)
        self.assertFalse(watch["enabled"])
        self.assertEqual(self.request("POST", "/api/tools/unknown/toggle", {"enabled": False})[0], 404)

    def test_defense_ops_endpoints_stay_bounded(self):
        status, overview, _ = self.request("GET", "/api/ops/overview")
        self.assertEqual(status, 200)
        self.assertEqual(overview["capture_engine"], "simulation")
        status, capture, _ = self.request("POST", "/api/ops/capture", {"interface": "any", "duration": 99, "limit": 99, "preset": "web"})
        self.assertEqual(status, 201)
        self.assertEqual(capture["mode"], "simulation")
        self.assertEqual(capture["duration"], 8)
        self.assertLessEqual(len(capture["packets"]), 30)
        self.assertTrue(all(packet["synthetic"] for packet in capture["packets"]))
        self.assertEqual(self.request("POST", "/api/ops/capture", {"interface": "eth0; rm -rf /"})[0], 400)
        self.assertEqual(self.request("POST", "/api/ops/capture", {"interface": "any", "preset": "nope"})[0], 400)
        interface = overview["interfaces"][0]
        status, preview, _ = self.request("POST", "/api/ops/mac-preview", {"interface": interface})
        self.assertEqual(status, 200)
        self.assertFalse(preview["mutated"])
        self.assertEqual(self.request("GET", "/api/ops/mac?interface=bad%20name")[0], 400)
        self.assertEqual(self.request("POST", "/api/ops/proxy-check", {})[0], 200)

    def test_internal_errors_do_not_leak_details(self):
        with patch.object(ControlPlane, "snapshot", side_effect=RuntimeError("secret /home/operator/path")):
            with contextlib.redirect_stderr(io.StringIO()) as log:
                status, body, _ = self.request("GET", "/api/state")
        self.assertEqual(status, 500)
        self.assertNotIn("secret", body["error"])
        self.assertIn("RuntimeError", body["error"])
        self.assertIn("secret", log.getvalue())  # full traceback stays in the server log


class AllowedHostServerTests(ServerTestCase):
    allowed_hosts = ("*.preview.test",)

    def test_configured_wildcard_host_is_accepted(self):
        self.assertEqual(self.request("GET", "/api/health", headers={"Host": "4173-abc.preview.test"})[0], 200)
        self.assertEqual(self.request("GET", "/api/health", headers={"Host": "preview.test.evil.example"})[0], 403)


class HostPolicyTests(unittest.TestCase):
    def test_local_and_ip_hosts_are_allowed_by_default(self):
        policy = HostPolicy()
        for host in ("localhost", "localhost:4173", "127.0.0.1:4173", "[::1]:4173", "192.168.1.20", "app.localhost", "", None):
            self.assertTrue(policy.allows(host), host)
        for host in ("evil.example", "localhost.evil.example", "127.0.0.1.nip.io"):
            self.assertFalse(policy.allows(host), host)

    def test_extra_hosts_and_wildcards(self):
        policy = HostPolicy(["*.e2b.app", "cockpit.lan, .corp.example"])
        self.assertTrue(policy.allows("4173-abc.e2b.app"))
        self.assertFalse(policy.allows("e2b.app"))
        self.assertTrue(policy.allows("cockpit.lan:4173"))
        self.assertTrue(policy.allows("soc.corp.example"))
        self.assertFalse(policy.allows("evil.lan"))
        self.assertTrue(HostPolicy(["*"]).allows("anything.example"))


class CliTests(unittest.TestCase):
    def test_default_bind_is_loopback(self):
        with patch.dict(os.environ, {}, clear=True):
            args = build_parser().parse_args([])
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.allowed_host, [])

    def test_allowed_hosts_from_environment_and_flags(self):
        with patch.dict(os.environ, {"CYBERGUARDIAN_ALLOWED_HOSTS": "cockpit.lan, *.e2b.app"}, clear=True):
            args = build_parser().parse_args(["--allowed-host", "soc.example"])
        self.assertEqual(args.allowed_host, ["cockpit.lan", "*.e2b.app", "soc.example"])


if __name__ == "__main__":
    unittest.main()
