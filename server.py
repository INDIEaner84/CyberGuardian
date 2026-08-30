#!/usr/bin/env python3
"""Small, dependency-free browser server for CyberGuardian's control plane.

Run locally with:
    python3 server.py

The server exposes only the defensive coordination API and serves the static
browser cockpit from ``web/``.  It deliberately contains no network scanner or
command execution path.  Honeypot telemetry is simulation-only.
"""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import unquote, urlparse

from core.control_plane import ControlPlane


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
MAX_BODY_BYTES = 64 * 1024


class CyberGuardianHandler(BaseHTTPRequestHandler):
    """HTTP adapter around :class:`ControlPlane`."""

    server_version = "CyberGuardianCockpit/0.3"

    @property
    def control_plane(self) -> ControlPlane:
        return self.server.control_plane  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        # Keep the console useful without noisy per-asset request logs.
        if self.path.startswith("/api/"):
            super().log_message(format, *args)

    def _headers(self, content_type: str, cache: bool = False) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=60" if cache else "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self'; img-src 'self' data:; font-src 'self'")

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._headers("application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _send_error_json(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self._send_json({"error": message}, status)

    def _read_json(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Ungültige Content-Length") from exc
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            raise ValueError("Request ist zu groß")
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Body muss gültiges JSON sein") from exc
        if not isinstance(body, dict):
            raise ValueError("Body muss ein JSON-Objekt sein")
        return body

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._headers("application/json")
        self.send_header("Allow", "GET, POST, PATCH, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/api/state":
            self._send_json(self.control_plane.snapshot())
            return
        if path == "/api/health":
            self._send_json(
                {
                    "ok": True,
                    "service": "CyberGuardian control plane",
                    "mode": "defensive simulation",
                    "updated_at": self.control_plane.snapshot().get("updated_at"),
                }
            )
            return
        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        try:
            body = self._read_json()
            if path == "/api/agents":
                result = self.control_plane.register_agent(body.get("name"), body.get("role"), body.get("focus"))
                self._send_json(result, HTTPStatus.CREATED)
                return
            if path == "/api/plans":
                result = self.control_plane.create_plan(
                    body.get("title"),
                    body.get("objective"),
                    body.get("owner", "ORBIT"),
                    body.get("priority", "normal"),
                    body.get("created_by", "OPERATOR"),
                )
                self._send_json(result, HTTPStatus.CREATED)
                return
            if path == "/api/honeypots":
                result = self.control_plane.create_honeypot(
                    body.get("name"), body.get("service"), body.get("port"), body.get("profile")
                )
                self._send_json(result, HTTPStatus.CREATED)
                return
            if path == "/api/messages":
                result = self.control_plane.broadcast_message(
                    body.get("sender"), body.get("recipient", "ALL AGENTS"), body.get("text"), body.get("kind", "broadcast")
                )
                self._send_json(result, HTTPStatus.CREATED)
                return

            match = re.fullmatch(r"/api/honeypots/([^/]+)/toggle", path)
            if match:
                result = self.control_plane.toggle_honeypot(match.group(1), body.get("active", True))
                self._send_json(result)
                return

            match = re.fullmatch(r"/api/honeypots/([^/]+)/simulate", path)
            if match:
                result = self.control_plane.simulate_signal(
                    match.group(1), body.get("source"), body.get("tactic"), body.get("severity")
                )
                self._send_json(result, HTTPStatus.CREATED)
                return

            match = re.fullmatch(r"/api/incidents/([^/]+)/ack", path)
            if match:
                result = self.control_plane.acknowledge_incident(match.group(1))
                self._send_json(result)
                return

            self._send_error_json("Endpoint nicht gefunden", HTTPStatus.NOT_FOUND)
        except KeyError as exc:
            self._send_error_json(str(exc).strip("'"), HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # keep API errors JSON-shaped for the UI
            self._send_error_json(f"Interner Fehler: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)

    def do_PATCH(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        try:
            body = self._read_json()
            match = re.fullmatch(r"/api/plans/([^/]+)", path)
            if match:
                result = self.control_plane.update_plan(match.group(1), body.get("status"), body.get("progress"))
                self._send_json(result)
                return
            self._send_error_json("Endpoint nicht gefunden", HTTPStatus.NOT_FOUND)
        except KeyError as exc:
            self._send_error_json(str(exc).strip("'"), HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
        except Exception as exc:
            self._send_error_json(f"Interner Fehler: {exc}", HTTPStatus.INTERNAL_SERVER_ERROR)

    def _serve_static(self, path: str) -> None:
        requested = "index.html" if path in {"", "/"} else path.lstrip("/")
        candidate = (WEB_ROOT / requested).resolve()
        try:
            candidate.relative_to(WEB_ROOT.resolve())
        except ValueError:
            self._send_error_json("Datei nicht gefunden", HTTPStatus.NOT_FOUND)
            return
        if not candidate.is_file():
            # Client-side view routes still resolve to the dashboard shell.
            candidate = WEB_ROOT / "index.html"
        try:
            content = candidate.read_bytes()
        except OSError:
            self._send_error_json("Datei nicht lesbar", HTTPStatus.NOT_FOUND)
            return
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if content_type == "text/html":
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self._headers(content_type, cache=candidate.name != "index.html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)


class CyberGuardianServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, address: tuple[str, int], control_plane: ControlPlane):
        super().__init__(address, CyberGuardianHandler)
        self.control_plane = control_plane


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CyberGuardian browser cockpit")
    parser.add_argument("--host", default=os.environ.get("HOST", "0.0.0.0"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "4173")))
    parser.add_argument("--data-file", default=os.environ.get("CYBERGUARDIAN_STATE_FILE"))
    return parser


def main() -> None:
    args = build_parser().parse_args()
    plane = ControlPlane(args.data_file) if args.data_file else ControlPlane()
    server = CyberGuardianServer((args.host, args.port), plane)
    print(f"CyberGuardian cockpit listening on http://{args.host}:{args.port}")
    print(f"Shared control plane: {plane.store_path}")
    print("Safety boundary: browser lab is simulation-only; no network listener is opened.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCyberGuardian cockpit stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
