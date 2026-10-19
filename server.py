#!/usr/bin/env python3
"""Small, dependency-free browser server for CyberGuardian's control plane.

Run locally with:
    python3 server.py

The server exposes the defensive coordination API and serves the static
browser cockpit from ``web/``.  Optional Defense Ops endpoints are strictly
allowlisted and bounded: they can inspect local capabilities, perform a short
packet-metadata capture when tshark/tcpdump is installed, inspect proxychains,
and preview a MAC rotation.  They never run arbitrary commands or mutate the
network identity. Honeypot telemetry is simulation-only. An explicitly enabled
VM lab can send only fixed test requests to a loopback-forwarded guest sensor.
"""

from __future__ import annotations

import argparse
import hmac
import json
import mimetypes
import os
import re
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.parse import parse_qs, unquote, urlparse

from core.control_plane import ControlPlane
from core.defense_ops import DefenseOps
from core.detection_replay import replay, rule_catalog
from core.offline_import import parse_import
from core.tool_catalog import ToolCatalog
from core.vm_lab import VMLab


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
MAX_BODY_BYTES = 64 * 1024


def _valid_secret(token: str) -> bool:
    return 32 <= len(token) <= 128 and token.isascii() and token.isprintable() and not any(c.isspace() for c in token)


def _token_matches(supplied: str, expected: str) -> bool:
    try:
        return hmac.compare_digest(supplied, expected)
    except TypeError:  # compare_digest rejects non-ASCII header values
        return False


class CyberGuardianHandler(BaseHTTPRequestHandler):
    """HTTP adapter around :class:`ControlPlane`."""

    server_version = "CyberGuardianCockpit/0.3"

    @property
    def control_plane(self) -> ControlPlane:
        return self.server.control_plane  # type: ignore[attr-defined]

    @property
    def defense_ops(self) -> DefenseOps:
        return self.server.defense_ops  # type: ignore[attr-defined]

    @property
    def tool_catalog(self) -> ToolCatalog:
        return self.server.tool_catalog  # type: ignore[attr-defined]

    @property
    def vm_lab(self) -> VMLab:
        return self.server.vm_lab  # type: ignore[attr-defined]

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

    def _api_role(self) -> Optional[str]:
        """Resolve the single request credential; never persist or echo it."""
        operator = self.server.api_token  # type: ignore[attr-defined]
        if not operator:
            return "operator"  # localhost or explicitly unsafe demo
        supplied = self.headers.get("Authorization", "")
        if _token_matches(supplied, f"Bearer {operator}"):
            return "operator"
        viewer = self.server.viewer_token  # type: ignore[attr-defined]
        if viewer and _token_matches(supplied, f"Bearer {viewer}"):
            return "viewer"
        return None

    def _authorized(self, path: str, write: bool = False) -> bool:
        """Guard every API route before reading bodies or disclosing state."""
        role = self._api_role()
        if role is None:
            self._send_json({"error": "API-Schlüssel fehlt oder ist ungültig", "code": "api_auth_required"}, HTTPStatus.UNAUTHORIZED)
            return False
        if write and role != "operator":
            self._send_json({"error": "Lesezugang: Änderungen sind nicht erlaubt", "code": "read_only"}, HTTPStatus.FORBIDDEN)
            return False
        if write:
            origin = self.headers.get("Origin")
            if (origin and urlparse(origin).netloc != self.headers.get("Host") or
                not origin and self.client_address[0] not in {"127.0.0.1", "::1"}):
                self._send_error_json("Same-Origin-Zugriff erforderlich", HTTPStatus.FORBIDDEN)
                return False
        return True

    def do_OPTIONS(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        if path.startswith("/api/") and path != "/api/auth" and not self._authorized(path):
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self._headers("application/json")
        self.send_header("Allow", "GET, OPTIONS" if path.startswith("/api/") and self._api_role() == "viewer" else "GET, POST, PATCH, OPTIONS")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        if path == "/api/auth":
            self._send_json({"required": bool(self.server.api_token)})  # type: ignore[attr-defined]
            return
        if path.startswith("/api/") and not self._authorized(path):
            return
        if path == "/api/session":
            self._send_json({"role": self._api_role(), "authenticated": bool(self.server.api_token)})  # type: ignore[attr-defined]
            return
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
        if path == "/api/detection/rules":
            self._send_json({"mode": "offline-replay", "rules": rule_catalog()})
            return
        if path == "/api/ops/overview":
            self._send_json(self.defense_ops.overview())
            return
        if path == "/api/vm-lab":
            result = self.vm_lab.status(collect=self._api_role() == "operator")
            result["operator_token_required"] = True
            if self.server.vm_lab_requested and not self.server.vm_operator_token:  # type: ignore[attr-defined]
                result["message"] = "VM-Lab gesperrt: CYBERGUARDIAN_VM_OPERATOR_TOKEN (32–128 Zeichen) fehlt."
            self._send_json(result)
            return
        if path == "/api/tools":
            self._send_json({
                "tools": self.tool_catalog.catalog(),
                "runs": self.control_plane.get_tool_runs(40),
                "safety": {
                    "mode": "allowlisted",
                    "browser_mutations": False,
                    "audit": "every tool run is stored in the local control plane",
                },
            })
            return
        if path == "/api/ops/mac":

            query = parse_qs(parsed.query)
            interface = query.get("interface", [""])[0]
            try:
                self._send_json(self.defense_ops.mac_status(interface))
            except ValueError as exc:
                self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
            return
        if path.startswith("/api/"):
            self._send_error_json("Endpoint nicht gefunden", HTTPStatus.NOT_FOUND)
            return
        self._serve_static(path)

    def do_POST(self) -> None:  # noqa: N802
        path = unquote(urlparse(self.path).path)
        if not self._authorized(path, write=True):
            return
        try:
            body = self._read_json()
            if path == "/api/evidence/import":
                if set(body) != {"format", "content"}:
                    raise ValueError("Offline-Import erlaubt nur format und content; keine Dateipfade")
                parsed_import = parse_import(body["format"], body["content"])
                result = self.control_plane.import_offline_alerts(
                    parsed_import["records"], parsed_import["format"], parsed_import["ignored_unrelated"])
                self._send_json(result, HTTPStatus.CREATED if result["accepted"] else HTTPStatus.OK)
                return
            if path == "/api/detection/replay":
                if set(body) - {"source", "limit"}:
                    raise ValueError("Replay erlaubt nur source und limit; keine Pfade, Regeln oder Kommandos")
                result = replay(self.control_plane.snapshot(), body.get("source", "all"), body.get("limit", 40))
                self.control_plane.record_observation(
                    "detection.replay", f"Offline-Replay: {result['evaluated']} lokale Ereignisse, {result['match_count']} Regel-Treffer ({result['source']}).", "cyan")
                self._send_json(result)
                return
            match = re.fullmatch(r"/api/vm-lab/scenarios/([a-z-]+)/run", path)
            if match:
                if not self.vm_lab.enabled:
                    self._send_error_json("VM-Lab ist nicht aktiviert oder der Operator-Schlüssel fehlt", HTTPStatus.SERVICE_UNAVAILABLE)
                    return
                expected = self.server.vm_operator_token  # type: ignore[attr-defined]
                supplied = self.headers.get("X-VM-Operator-Token", "")
                if not expected or not _token_matches(supplied, expected):
                    self._send_error_json("Operator-Schlüssel fehlt oder ist ungültig", HTTPStatus.UNAUTHORIZED)
                    return
                try:
                    self._send_json(self.vm_lab.run(match.group(1)), HTTPStatus.CREATED)
                except RuntimeError as exc:
                    self._send_error_json(str(exc), HTTPStatus.SERVICE_UNAVAILABLE)
                return
            match = re.fullmatch(r"/api/tools/([^/]+)/run", path)
            if match:
                run = self.tool_catalog.run(match.group(1), body.get("action"))
                stored = self.control_plane.record_tool_run(run)
                self._send_json(stored, HTTPStatus.CREATED if stored.get("status") == "completed" else HTTPStatus.OK)
                return
            match = re.fullmatch(r"/api/tools/([^/]+)/toggle", path)
            if match:
                result = self.control_plane.set_tool_state(match.group(1), body.get("enabled", True))
                self._send_json(result)
                return
            if path == "/api/ops/capture":

                result = self.defense_ops.capture_metadata(
                    body.get("interface", "lo"),
                    body.get("duration", 5),
                    body.get("limit", 12),
                    body.get("preset", "metadata"),
                )
                self.control_plane.record_observation(
                    "ops.capture",
                    f"Packet Observatory: {result.get('engine', 'unknown')} / {result.get('mode', 'unknown')} / {len(result.get('packets', []))} metadata rows.",
                    "green" if result.get("ok") else "yellow",
                )
                self._send_json(result, HTTPStatus.CREATED if result.get("ok") else HTTPStatus.OK)
                return
            if path == "/api/ops/mac-preview":
                result = self.defense_ops.mac_preview(body.get("interface", "lo"))
                self.control_plane.record_observation(
                    "ops.mac.preview",
                    f"MAC-Rotation für {result['interface']} nur als Vorschau erzeugt — keine Mutation.",
                    "cyan",
                )
                self._send_json(result)
                return
            if path == "/api/ops/proxy-check":
                result = self.defense_ops.proxy_status()
                self.control_plane.record_observation(
                    "ops.proxy.check",
                    f"Proxychains-Profil geprüft: {'bereit' if result.get('configured') else 'nicht konfiguriert'} — keine Route gestartet.",
                    "cyan",
                )
                self._send_json(result)
                return
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

            match = re.fullmatch(r"/api/vm-alerts/([0-9a-f]{16}:[1-9][0-9]{0,6})/review", path)
            if match:
                result = self.control_plane.review_vm_alert(match.group(1), body.get("note", ""))
                self._send_json(result)
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
        if not self._authorized(path, write=True):
            return
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

    def __init__(self, address: tuple[str, int], control_plane: ControlPlane, defense_ops: Optional[DefenseOps] = None,
                 vm_lab: Optional[VMLab] = None, allow_unauthenticated: bool = False):
        token = os.environ.get("CYBERGUARDIAN_API_TOKEN", "")
        if token and not _valid_secret(token):
            raise ValueError("CYBERGUARDIAN_API_TOKEN muss 32–128 druckbare ASCII-Zeichen ohne Leerzeichen enthalten")
        viewer_token = os.environ.get("CYBERGUARDIAN_VIEWER_TOKEN", "")
        if viewer_token and (not _valid_secret(viewer_token) or not token or viewer_token == token):
            raise ValueError("CYBERGUARDIAN_VIEWER_TOKEN benötigt einen anderen gültigen API-Operator-Schlüssel (32–128 Zeichen)")
        if address[0] not in {"127.0.0.1", "::1", "localhost"} and not token and not allow_unauthenticated:
            raise ValueError("Nicht-lokaler Host erfordert CYBERGUARDIAN_API_TOKEN (oder explizit --allow-unauthenticated für eine unsichere Demo)")
        super().__init__(address, CyberGuardianHandler)
        self.api_token = token
        self.viewer_token = viewer_token
        self.control_plane = control_plane
        self.defense_ops = defense_ops or DefenseOps()
        lab_dir = Path(os.environ.get("CYBERGUARDIAN_VM_LAB_DIR", Path.home() / ".cyberguardian" / "vm-lab"))
        self.vm_lab_requested = os.environ.get("CYBERGUARDIAN_ENABLE_VM_LAB") == "1"
        if self.vm_lab_requested and not self.api_token and address[0] not in {"127.0.0.1", "::1", "localhost"}:
            self.server_close()
            raise ValueError("VM-Lab auf nicht-lokalem Host benötigt CYBERGUARDIAN_API_TOKEN")
        token = os.environ.get("CYBERGUARDIAN_VM_OPERATOR_TOKEN", "")
        self.vm_operator_token = token if _valid_secret(token) else ""
        self.vm_lab = vm_lab or VMLab(control_plane, lab_dir / "secret", self.vm_lab_requested and bool(self.vm_operator_token))
        self.tool_catalog = ToolCatalog(control_plane, self.defense_ops, self.vm_lab)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CyberGuardian browser cockpit")
    parser.add_argument("--host", default=os.environ.get("HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "4173")))
    parser.add_argument("--data-file", default=os.environ.get("CYBERGUARDIAN_STATE_FILE"))
    parser.add_argument("--allow-unauthenticated", action="store_true", help="Unsecured non-local demo; never use for real data")
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    plane = ControlPlane(args.data_file) if args.data_file else ControlPlane()
    try:
        server = CyberGuardianServer((args.host, args.port), plane, allow_unauthenticated=args.allow_unauthenticated)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"CyberGuardian cockpit listening on http://{args.host}:{args.port}")
    if args.allow_unauthenticated and not server.api_token:
        print("WARNING: unauthenticated non-local demo; do not expose personal or production data.")
    print(f"Shared control plane: {plane.store_path}")
    print("Safety boundary: honeypots are simulated; optional VM-Lab uses only a fixed loopback-forwarded guest sensor.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCyberGuardian cockpit stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
