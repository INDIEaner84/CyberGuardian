#!/usr/bin/env python3
"""Small, dependency-free browser server for CyberGuardian's control plane.

Run locally with:
    python3 server.py

The server exposes the defensive coordination API and serves the static
browser cockpit from ``web/``.  Optional Defense Ops endpoints are strictly
allowlisted and bounded: they can inspect local capabilities, perform a short
packet-metadata capture when tshark/tcpdump is installed, inspect proxychains,
and preview a MAC rotation.  They never run arbitrary commands or mutate the
network identity.  Honeypot telemetry is simulation-only.

Browser safety: the cockpit has no login, therefore the server binds to
``127.0.0.1`` by default, rejects cross-site write requests (CSRF) and only
answers requests whose ``Host`` header is local, an IP literal or explicitly
allowed via ``--allowed-host`` (DNS-rebinding protection).
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import mimetypes
import os
import re
import socket
import sys
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional
from urllib.parse import parse_qs, unquote, urlparse

from core.control_plane import ControlPlane, NotFoundError
from core.defense_ops import DefenseOps
from core.tool_catalog import ToolCatalog


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "web"
MAX_BODY_BYTES = 64 * 1024
MAX_DRAIN_BYTES = 1024 * 1024
DEFAULT_HOST = "127.0.0.1"
LOCAL_HOSTNAMES = {"localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback"}
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; connect-src 'self'; style-src 'self' 'unsafe-inline'; "
    "script-src 'self'; img-src 'self' data:; font-src 'self'; object-src 'none'; "
    "base-uri 'none'; form-action 'self'"
)

# Some platforms ship incomplete MIME tables; the cockpit bundles its fonts.
mimetypes.add_type("font/woff2", ".woff2")


class RequestError(Exception):
    """An expected client error with an explicit HTTP status."""

    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status


def _host_from_header(value: Optional[str]) -> str:
    """Return the lower-cased host part of a Host header (no port, no brackets)."""

    host = (value or "").strip().lower().rstrip(".")
    if not host:
        return ""
    if host.startswith("["):
        end = host.find("]")
        return host[1:end] if end != -1 else ""
    if host.count(":") == 1:
        return host.split(":", 1)[0].rstrip(".")
    return host


def _is_ip_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host.split("%", 1)[0])
    except ValueError:
        return False
    return True


def _is_loopback_bind(host: str) -> bool:
    if host.lower() in LOCAL_HOSTNAMES:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class HostPolicy:
    """Host-header allowlist that protects the unauthenticated API against DNS rebinding.

    Always allowed: ``localhost`` (and ``*.localhost``), IP literals, the machine's
    hostname and requests without a Host header (non-browser clients).  Extra
    entries may be exact names, ``*.example.org`` wildcards or ``*`` to disable
    the check entirely.
    """

    def __init__(self, allowed: Optional[Iterable[str]] = None) -> None:
        self.allow_all = False
        self.exact = set(LOCAL_HOSTNAMES)
        self.suffixes: List[str] = [".localhost"]
        machine = socket.gethostname().strip().lower().rstrip(".")
        if machine:
            self.exact.update({machine, f"{machine}.local"})
        for entry in allowed or []:
            for part in str(entry).split(","):
                pattern = part.strip().lower().rstrip(".")
                if not pattern:
                    continue
                if pattern == "*":
                    self.allow_all = True
                elif pattern.startswith("*."):
                    self.suffixes.append(pattern[1:])
                elif pattern.startswith("."):
                    self.suffixes.append(pattern)
                else:
                    self.exact.add(_host_from_header(pattern) or pattern)

    def allows(self, host_header: Optional[str]) -> bool:
        if self.allow_all:
            return True
        host = _host_from_header(host_header)
        if not host:
            return True
        if _is_ip_literal(host) or host in self.exact:
            return True
        return any(host.endswith(suffix) and len(host) > len(suffix) for suffix in self.suffixes)


def _strip_default_port(netloc: str, scheme: str = "") -> str:
    netloc = netloc.strip().lower()
    for suffix, schemes in ((":80", {"http", ""}), (":443", {"https", ""})):
        if netloc.endswith(suffix) and scheme in schemes:
            return netloc[: -len(suffix)]
    return netloc


class CyberGuardianHandler(BaseHTTPRequestHandler):
    """HTTP adapter around :class:`ControlPlane`."""

    server_version = "CyberGuardianCockpit/0.3"

    def version_string(self) -> str:
        # Do not advertise the exact Python runtime version.
        return self.server_version

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
    def host_policy(self) -> HostPolicy:
        return self.server.host_policy  # type: ignore[attr-defined]

    def log_message(self, format: str, *args: Any) -> None:
        # Keep the console useful without noisy per-asset request logs.
        if getattr(self, "path", "").startswith("/api/"):
            super().log_message(format, *args)

    def log_error(self, format: str, *args: Any) -> None:
        super().log_message(format, *args)

    # ------------------------------------------------------------------ output
    def _headers(self, content_type: str, cache: bool = False) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "public, max-age=60" if cache else "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "SAMEORIGIN")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cross-Origin-Resource-Policy", "same-origin")
        self.send_header("Content-Security-Policy", CONTENT_SECURITY_POLICY)

    def _write_body(self, raw: bytes) -> None:
        if self.command != "HEAD":
            self.wfile.write(raw)

    def _send_json(self, payload: Any, status: HTTPStatus = HTTPStatus.OK) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._headers("application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self._write_body(raw)

    def _send_error_json(self, message: str, status: HTTPStatus = HTTPStatus.BAD_REQUEST) -> None:
        self._send_json({"error": message}, status)

    # ------------------------------------------------------------------ guards
    def _check_host(self) -> None:
        if not self.host_policy.allows(self.headers.get("Host")):
            host = _host_from_header(self.headers.get("Host")) or "?"
            raise RequestError(
                HTTPStatus.FORBIDDEN,
                f"Host '{host}' ist nicht erlaubt. Server mit --allowed-host {host} starten, "
                "wenn dieser Zugriff beabsichtigt ist.",
            )

    def _origin_matches_host(self, origin: str) -> bool:
        if origin.strip().lower() == "null":
            return False
        parsed = urlparse(origin.strip())
        if not parsed.netloc:
            return False
        host = self.headers.get("Host") or ""
        return _strip_default_port(parsed.netloc, parsed.scheme.lower()) == _strip_default_port(host)

    def _check_write_request(self) -> None:
        """Block CSRF: writes must be JSON and must not come from another site."""

        mime = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if mime != "application/json":
            raise RequestError(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, "Content-Type muss application/json sein")
        fetch_site = (self.headers.get("Sec-Fetch-Site") or "").strip().lower()
        if fetch_site in {"cross-site", "same-site"}:
            raise RequestError(HTTPStatus.FORBIDDEN, "Cross-Site-Request blockiert")
        origin = self.headers.get("Origin")
        if not fetch_site and origin is not None and not self._origin_matches_host(origin):
            raise RequestError(HTTPStatus.FORBIDDEN, "Origin passt nicht zum Host — Request blockiert")

    def _read_json(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Ungültige Content-Length") from exc
        if length <= 0:
            return {}
        if length > MAX_BODY_BYTES:
            self.close_connection = True
            if length <= MAX_DRAIN_BYTES:
                # Drain moderately oversized bodies so the client reliably receives the 413
                # instead of a TCP reset caused by unread data.
                self.rfile.read(length)
            raise RequestError(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "Request ist zu groß")
        raw = self.rfile.read(length)
        try:
            body = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("Body muss gültiges JSON sein") from exc
        if not isinstance(body, dict):
            raise ValueError("Body muss ein JSON-Objekt sein")
        return body

    # ---------------------------------------------------------------- dispatch
    def _dispatch(self, method: str) -> None:
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        try:
            self._check_host()
            if method == "GET":
                self._handle_get(path, parsed.query)
                return
            self._check_write_request()
            body = self._read_json()
            if method == "POST":
                self._handle_post(path, body)
            else:
                self._handle_patch(path, body)
        except (BrokenPipeError, ConnectionResetError):
            return
        except RequestError as exc:
            self._send_error_json(str(exc), exc.status)
        except NotFoundError as exc:
            self._send_error_json(str(exc), HTTPStatus.NOT_FOUND)
        except ValueError as exc:
            self._send_error_json(str(exc), HTTPStatus.BAD_REQUEST)
        except Exception as exc:  # keep API errors JSON-shaped for the UI
            sys.stderr.write(f"[CyberGuardian] {method} {path} failed\n{traceback.format_exc()}")
            self._send_error_json(
                f"Interner Fehler ({exc.__class__.__name__}) — Details im Server-Log",
                HTTPStatus.INTERNAL_SERVER_ERROR,
            )

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._headers("application/json")
        self.send_header("Allow", "GET, HEAD, POST, PATCH, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_HEAD(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_PATCH(self) -> None:  # noqa: N802
        self._dispatch("PATCH")

    # ------------------------------------------------------------------ routes
    def _handle_get(self, path: str, query_string: str) -> None:
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
        if path == "/api/ops/overview":
            self._send_json(self.defense_ops.overview())
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
            interface = parse_qs(query_string).get("interface", [""])[0]
            self._send_json(self.defense_ops.mac_status(interface))
            return
        if path == "/api" or path.startswith("/api/"):
            raise RequestError(HTTPStatus.NOT_FOUND, "API-Endpoint nicht gefunden")
        self._serve_static(path)

    def _handle_post(self, path: str, body: Dict[str, Any]) -> None:
        match = re.fullmatch(r"/api/tools/([^/]+)/run", path)
        if match:
            run = self.tool_catalog.run(match.group(1), body.get("action"))
            stored = self.control_plane.record_tool_run(run)
            self._send_json(stored, HTTPStatus.CREATED if stored.get("status") == "completed" else HTTPStatus.OK)
            return
        match = re.fullmatch(r"/api/tools/([^/]+)/toggle", path)
        if match:
            if not self.tool_catalog.has_tool(match.group(1)):
                raise NotFoundError(f"Tool nicht gefunden: {match.group(1)}")
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

        match = re.fullmatch(r"/api/incidents/([^/]+)/ack", path)
        if match:
            result = self.control_plane.acknowledge_incident(match.group(1))
            self._send_json(result)
            return

        raise RequestError(HTTPStatus.NOT_FOUND, "Endpoint nicht gefunden")

    def _handle_patch(self, path: str, body: Dict[str, Any]) -> None:
        match = re.fullmatch(r"/api/plans/([^/]+)", path)
        if match:
            result = self.control_plane.update_plan(match.group(1), body.get("status"), body.get("progress"))
            self._send_json(result)
            return
        raise RequestError(HTTPStatus.NOT_FOUND, "Endpoint nicht gefunden")

    def _serve_static(self, path: str) -> None:
        requested = "index.html" if path in {"", "/"} else path.lstrip("/")
        web_root = WEB_ROOT.resolve()
        candidate = (web_root / requested).resolve()
        try:
            candidate.relative_to(web_root)
        except ValueError:
            raise RequestError(HTTPStatus.NOT_FOUND, "Datei nicht gefunden") from None
        if not candidate.is_file():
            if Path(requested).suffix:
                # Missing assets must not silently turn into HTML documents.
                raise RequestError(HTTPStatus.NOT_FOUND, "Datei nicht gefunden")
            # Client-side view routes still resolve to the dashboard shell.
            candidate = web_root / "index.html"
        try:
            content = candidate.read_bytes()
        except OSError:
            raise RequestError(HTTPStatus.NOT_FOUND, "Datei nicht lesbar") from None
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type in {"application/javascript", "image/svg+xml"}:
            content_type += "; charset=utf-8"
        self.send_response(HTTPStatus.OK)
        self._headers(content_type, cache=candidate.name != "index.html")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self._write_body(content)


class CyberGuardianServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        control_plane: ControlPlane,
        defense_ops: Optional[DefenseOps] = None,
        allowed_hosts: Optional[Iterable[str]] = None,
    ):
        if ":" in address[0]:
            self.address_family = socket.AF_INET6
        super().__init__(address, CyberGuardianHandler)
        self.control_plane = control_plane
        self.defense_ops = defense_ops or DefenseOps()
        self.tool_catalog = ToolCatalog(control_plane, self.defense_ops)
        self.host_policy = HostPolicy([address[0], *(allowed_hosts or [])])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="CyberGuardian browser cockpit")
    parser.add_argument(
        "--host",
        default=os.environ.get("HOST", DEFAULT_HOST),
        help="Bind-Adresse (Standard: 127.0.0.1). 0.0.0.0 macht das Cockpit ohne Login im Netzwerk erreichbar.",
    )
    parser.add_argument("--port", type=int, default=int(os.environ.get("PORT", "4173")))
    parser.add_argument("--data-file", default=os.environ.get("CYBERGUARDIAN_STATE_FILE"))
    parser.add_argument(
        "--allowed-host",
        action="append",
        default=[entry.strip() for entry in os.environ.get("CYBERGUARDIAN_ALLOWED_HOSTS", "").split(",") if entry.strip()],
        metavar="HOST",
        help="Zusätzlich erlaubter Host-Header, z. B. cockpit.lan oder '*.e2b.app' (mehrfach nutzbar).",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    plane = ControlPlane(args.data_file) if args.data_file else ControlPlane()
    server = CyberGuardianServer((args.host, args.port), plane, allowed_hosts=args.allowed_host)
    display_host = f"[{args.host}]" if ":" in args.host else args.host
    print(f"CyberGuardian cockpit listening on http://{display_host}:{args.port}")
    print(f"Shared control plane: {plane.store_path}")
    print("Safety boundary: browser lab is simulation-only; no network listener is opened.")
    if not _is_loopback_bind(args.host):
        print(
            "WARNUNG: Das Cockpit ist ohne Login im Netzwerk erreichbar. "
            "Nur in vertrauenswürdigen Netzen oder hinter einem authentifizierenden Proxy betreiben."
        )
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nCyberGuardian cockpit stopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
