"""Fixed-scenario bridge to the loopback-forwarded, optional QEMU guest sensor."""
from __future__ import annotations

import json
import secrets
import threading
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener

SCENARIOS = {
    "baseline": {"title": "Health-Check", "description": "Ein harmloser VM-Health-Request; kein Alert erwartet.", "steps": [("GET", "/health")]},
    "discovery": {"title": "Pfad-Erkundung", "description": "Zwei feste Decoy-Pfade; Regel path-discovery.", "steps": [("GET", "/probe/admin"), ("GET", "/probe/settings")]},
    "retries": {"title": "Login-Wiederholungen", "description": "Drei leere Login-Anfragen ohne Zugangsdaten; Regel login-retries.", "steps": [("POST", "/login")] * 3},
}


class VMLab:
    def __init__(self, control_plane, key_file: Path | str, enabled: bool = False, port: int = 18081):
        self.control_plane = control_plane
        self.key_file = Path(key_file)
        self.enabled = enabled
        self.port = port
        self._lock = threading.Lock()
        # Never forward the guest key to a proxy inherited from HTTP_PROXY.
        self._opener = build_opener(ProxyHandler({}))

    def _request(self, path, method="GET", run_id=""):
        # The URL is never derived from a browser-supplied host or path.
        key = self.key_file.read_text(encoding="ascii").strip()
        if len(key) < 32:
            raise ValueError("VM-Lab-Schlüssel fehlt oder ist ungültig")
        req = Request(f"http://127.0.0.1:{self.port}{path}", method=method,
                      headers={"X-Lab-Key": key, "X-Lab-Run": run_id},
                      data=b"" if method == "POST" else None)
        try:
            with self._opener.open(req, timeout=2) as response:
                return json.load(response)
        except HTTPError as exc:
            # Fixed decoy 403/404 responses are expected observations, not failures.
            if path in ("/probe/admin", "/probe/settings", "/login") and exc.code in (403, 404):
                return {"status": exc.code}
            raise

    def _collect(self):
        payload = self._request("/events")
        for event in payload.get("events", [])[-100:]:
            self.control_plane.record_vm_alert(event)
        return len(payload.get("events", []))

    def status(self, collect: bool = True):
        result = {"enabled": self.enabled, "connected": False,
                  "mode": "real VM sensor" if self.enabled else "disabled",
                  "scenarios": [{"id": key, "title": item["title"], "description": item["description"]}
                                for key, item in SCENARIOS.items()]}
        if not self.enabled:
            result["message"] = "VM-Lab nicht aktiviert. Anleitung: README → QEMU VM-Lab."
            return result
        try:
            with self._lock:
                health = self._request("/health")
                if not health.get("ok"):
                    raise ValueError("Ungültige Sensor-Antwort")
                if collect:
                    self._collect()
            result.update(connected=True, boot_id=health.get("boot_id"), message="VM-Sensor erreichbar; echte HTTP-Beobachtung.")
        except (OSError, ValueError, URLError, TimeoutError) as exc:
            result["message"] = f"VM-Sensor nicht erreichbar ({type(exc).__name__}). QEMU und Schlüssel prüfen."
        return result

    def run(self, scenario_id):
        if scenario_id not in SCENARIOS:
            raise ValueError("Unbekanntes VM-Lab-Szenario")
        if not self.enabled:
            raise RuntimeError("VM-Lab ist nicht aktiviert")
        with self._lock:
            run_id = secrets.token_hex(16)
            try:
                self._request("/health")
                for method, path in SCENARIOS[scenario_id]["steps"]:
                    self._request(path, method, run_id)
                self._collect()
            except (OSError, ValueError, URLError, TimeoutError) as exc:
                raise RuntimeError("VM-Sensor nicht erreichbar; kein Test als erfolgreich markiert") from exc
            alerts = [item for item in self.control_plane.snapshot().get("vm_alerts", [])
                      if item.get("run_id") == run_id]
            self.control_plane.record_observation("vm.lab.run",
                f"VM-Lab {scenario_id}: {len(alerts)} vom Gast-Sensor gemeldete Alerts.",
                "yellow" if alerts else "green")
            return {"run_id": run_id, "scenario": scenario_id, "requests": len(SCENARIOS[scenario_id]["steps"]),
                    "alerts": alerts, "mode": "real VM sensor"}
