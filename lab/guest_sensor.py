#!/usr/bin/env python3
"""Minimal HTTP sensor inside the *dedicated* QEMU lab guest.

Only authenticated, bounded requests to this decoy are observed. No shell,
credential collection, host scanning, or network response beyond a fixed JSON
reply. The host polls alerts; the guest never calls out to the Internet.
"""
from __future__ import annotations

import hmac
import json
import os
import secrets
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

KEY_FILE = os.environ.get("CG_LAB_KEY_FILE", "/etc/cyberguardian-lab.key")
BOOT_ID = secrets.token_hex(8)
LOCK = threading.Lock()
EVENTS = deque(maxlen=100)
COUNTS = defaultdict(lambda: deque(maxlen=10))
SEQUENCE = 0


def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def observe(run_id, rule, threshold, severity, summary):
    global SEQUENCE
    with LOCK:
        current = time.monotonic()
        if len(COUNTS) >= 256:
            for key, values in list(COUNTS.items()):
                if not values or current - values[-1] > 15:
                    del COUNTS[key]
            if len(COUNTS) >= 256:
                del COUNTS[next(iter(COUNTS))]
        times = COUNTS[(run_id, rule)]
        times.append(current)
        while times and current - times[0] > 15:
            times.popleft()
        if len(times) == threshold:
            SEQUENCE += 1
            EVENTS.append({"seq": SEQUENCE, "boot_id": BOOT_ID, "run_id": run_id,
                           "rule": rule, "severity": severity, "summary": summary,
                           "count": len(times), "observed_at": now(), "source": "VM HTTP sensor"})


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass  # No request bodies or credentials in logs.

    def send_json(self, payload, status=200):
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def handle_request(self):
        try:
            with open(KEY_FILE, encoding="ascii") as handle:
                key = handle.read().strip()
        except OSError:
            self.send_json({"error": "sensor not configured"}, 503)
            return
        if not hmac.compare_digest(self.headers.get("X-Lab-Key", ""), key):
            self.send_json({"error": "unauthorized"}, 403)
            return
        path = urlsplit(self.path).path
        if self.command == "GET" and path == "/health":
            self.send_json({"ok": True, "boot_id": BOOT_ID, "sensor": "guest-http-v1"})
            return
        if self.command == "GET" and path == "/events":
            with LOCK:
                events = list(EVENTS)
            self.send_json({"boot_id": BOOT_ID, "events": events})
            return
        run_id = self.headers.get("X-Lab-Run", "")
        if len(run_id) != 32 or any(char not in "0123456789abcdef" for char in run_id):
            self.send_json({"error": "invalid run"}, 400)
            return
        if self.command == "GET" and path in ("/probe/admin", "/probe/settings"):
            observe(run_id, "path-discovery", 2, "medium", "Mehrere geschützte Pfade im VM-Decoy angefragt")
            self.send_json({"ok": False, "message": "decoy path"}, 404)
        elif self.command == "POST" and path == "/login":
            # Discard a tiny fixed body; the exercise sends no usernames/passwords.
            try:
                size = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                size = -1
            if size < 0 or size > 128:
                self.send_json({"error": "body too large"}, 413)
                return
            self.rfile.read(size)
            observe(run_id, "login-retries", 3, "high", "Wiederholte Login-Anfragen an den VM-Decoy")
            self.send_json({"ok": False, "message": "login disabled"}, 403)
        else:
            self.send_json({"error": "not found"}, 404)

    def do_GET(self):
        self.handle_request()

    def do_POST(self):
        self.handle_request()


if __name__ == "__main__":
    ThreadingHTTPServer(("0.0.0.0", 8081), Handler).serve_forever()
