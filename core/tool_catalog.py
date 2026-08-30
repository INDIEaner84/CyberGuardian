#!/usr/bin/env python3
"""Unified, auditable catalog for CyberGuardian's known modules.

The legacy desktop modules expose a mixture of read-only observers and
privileged system controls.  The browser must not become an unauthenticated
shell, so this catalog gives every module one documented, allowlisted action
surface.  Each browser action either performs a bounded observation or returns
a simulation/preview; no destructive legacy method is called here.
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import socket
import subprocess
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .defense_ops import DefenseOps


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean(value: Any, default: str = "", limit: int = 220) -> str:
    text = " ".join(str(value if value is not None else "").strip().split())
    return text[:limit] if text else default


class ToolCatalog:
    """Registry and safe execution gateway for all dashboard-visible tools."""

    def __init__(self, control_plane, defense_ops: Optional[DefenseOps] = None):
        self.control_plane = control_plane
        self.defense_ops = defense_ops or DefenseOps()
        self._definitions = self._build_definitions()

    def _build_definitions(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": "network_scanner", "name": "NETWORK SCANNER", "module": "core.network_scanner",
                "category": "visibility", "icon": "⌁", "accent": "cyan",
                "summary": "Genehmigte Interfaces und lokale Netzsicht zusammenfassen.",
                "explain": "Startet aus dem Browser keine fremden Probes. Der sichere Dashboard-Run liest die lokale Interface-Sicht; aktive Inventur bleibt ein separat autorisierter Workflow.",
                "boundary": "LOCAL INVENTORY / NO PROBE",
                "actions": [{"id": "interface_inventory", "label": "INTERFACES LESEN", "description": "lokale Interfaces auflisten"}],
            },
            {
                "id": "wifi_auditor", "name": "WIRELESS AUDITOR", "module": "core.wifi_auditor",
                "category": "visibility", "icon": "◉", "accent": "purple",
                "summary": "WLAN-Radio- und Adapterstatus defensiv prüfen.",
                "explain": "Zeigt nur lokale Radio-Fähigkeiten und Adapterinformationen. Kein Cracking, kein Handshake-Capture, keine Passwortprüfung.",
                "boundary": "RADIO STATUS / NO CRACKING",
                "actions": [{"id": "radio_status", "label": "RADIO STATUS", "description": "lokale WLAN-Fähigkeit prüfen"}],
            },
            {
                "id": "port_manager", "name": "PORT MANAGER", "module": "core.port_manager",
                "category": "visibility", "icon": "⊙", "accent": "orange",
                "summary": "Lokale Listening-Sockets sichtbar machen.",
                "explain": "Liest ausschließlich die eigenen Listening-Sockets. Kein Remote-Portscan und kein Firewall-Change aus dem Browser.",
                "boundary": "LOCAL SOCKETS / READ ONLY",
                "actions": [{"id": "listening_ports", "label": "LISTENING PORTS", "description": "lokale Sockets lesen"}],
            },
            {
                "id": "process_monitor", "name": "PROCESS MONITOR", "module": "core.process_monitor",
                "category": "visibility", "icon": "▦", "accent": "cyan",
                "summary": "Aktive lokale Prozesse und deren Zustand beobachten.",
                "explain": "Erstellt einen kleinen Prozess-Snapshot für Triage. Das Dashboard beendet oder startet keinen Prozess.",
                "boundary": "LOCAL PROCESSES / NO KILL",
                "actions": [{"id": "process_snapshot", "label": "SNAPSHOT LESEN", "description": "lokale Prozesse erfassen"}],
            },
            {
                "id": "wireguard", "name": "WIREGUARD", "module": "core.wireguard_manager",
                "category": "connectivity", "icon": "◇", "accent": "purple",
                "summary": "VPN-Interface-Status ohne Konfigurationsänderung prüfen.",
                "explain": "Liest nur, ob WireGuard-Interfaces sichtbar sind. Tunnel starten, stoppen oder private Schlüssel erzeugen bleibt außerhalb des Browser-Gateways.",
                "boundary": "VPN STATUS / NO MUTATION",
                "actions": [{"id": "vpn_status", "label": "VPN STATUS", "description": "WireGuard-Status lesen"}],
            },
            {
                "id": "anonymizer", "name": "ANONYMIZER / PROXY", "module": "core.anonymizer",
                "category": "connectivity", "icon": "◎", "accent": "magenta",
                "summary": "Proxy- und Anonymisierungsstatus nachvollziehbar halten.",
                "explain": "Prüft nur lokale Proxychains-Konfiguration. Keine Route, kein Tor-Start und kein externer Request wird durch den Browser ausgelöst.",
                "boundary": "PROFILE CHECK / NO ROUTE",
                "actions": [{"id": "proxy_status", "label": "PROXY STATUS", "description": "Proxy-Profil prüfen"}],
            },
            {
                "id": "router_tools", "name": "ROUTER TOOLS", "module": "core.router_tools",
                "category": "connectivity", "icon": "⌘", "accent": "orange",
                "summary": "Lokale Link- und Interface-Gesundheit lesen.",
                "explain": "Gibt nur eine kompakte lokale Adapteransicht zurück. Keine Router-Anmeldung, kein Reconfigure und kein Regel-Write.",
                "boundary": "LINK STATUS / NO WRITE",
                "actions": [{"id": "link_status", "label": "LINK STATUS", "description": "lokale Adapter lesen"}],
            },
            {
                "id": "ids_ips", "name": "IDS / IPS", "module": "core.intrusion_detection",
                "category": "defense", "icon": "✦", "accent": "red",
                "summary": "Defensive Detection-Posture und Watch-State koordinieren.",
                "explain": "Der Browser schaltet keine produktive IPS-Regel scharf. Die Karte steuert die dokumentierte Watch-Posture; echte Sensoren gehören in einen gehärteten Collector.",
                "boundary": "WATCH POSTURE / NO BLOCK",
                "actions": [{"id": "detection_posture", "label": "POSTURE PRÜFEN", "description": "defensive Beobachtung dokumentieren"}],
            },
            {
                "id": "file_integrity", "name": "FILE INTEGRITY", "module": "core.file_integrity",
                "category": "evidence", "icon": "▤", "accent": "green",
                "summary": "Baseline-Verfügbarkeit und Integritätsworkflow sichtbar machen.",
                "explain": "Prüft, ob eine lokale Baseline vorhanden ist. Hashing großer Verzeichnisse wird nicht heimlich im Browser gestartet.",
                "boundary": "BASELINE CHECK / LOCAL",
                "actions": [{"id": "baseline_status", "label": "BASELINE STATUS", "description": "lokale Baseline prüfen"}],
            },
            {
                "id": "forensics", "name": "FORENSICS", "module": "core.forensics",
                "category": "evidence", "icon": "◫", "accent": "purple",
                "summary": "Minimale lokale Systemfakten für Triage sammeln.",
                "explain": "Erfasst nur technische Eckdaten wie OS, Host und Bootzeit. Keine Dateien werden exfiltriert und keine Spuren gelöscht.",
                "boundary": "TRIAGE FACTS / LOCAL ONLY",
                "actions": [{"id": "system_snapshot", "label": "SYSTEM SNAPSHOT", "description": "lokale Eckdaten sammeln"}],
            },
            {
                "id": "backup_rollback", "name": "BACKUP / ROLLBACK", "module": "utils.backup_manager",
                "category": "recovery", "icon": "↶", "accent": "magenta",
                "summary": "Backups und Wiederherstellungsbereitschaft nachvollziehen.",
                "explain": "Listet vorhandene lokale Backups. Restore- und Firewall-Änderungen benötigen einen separaten, authentifizierten Admin-Workflow.",
                "boundary": "INVENTORY / NO RESTORE",
                "actions": [{"id": "backup_inventory", "label": "BACKUPS LISTEN", "description": "lokale Backups zählen"}],
            },
            {
                "id": "action_logger", "name": "ACTION LOGGER", "module": "utils.logger",
                "category": "coordination", "icon": "≋", "accent": "cyan",
                "summary": "Jeden Tool-Run und jede Übergabe als Audit Trail festhalten.",
                "explain": "Zeigt, dass Beobachtung und Entscheidung nachvollziehbar bleiben. Es werden keine privaten Payloads oder Geheimnisse in den Browser-Log geschrieben.",
                "boundary": "AUDIT INDEX / LOCAL ONLY",
                "actions": [{"id": "audit_inventory", "label": "AUDIT STATUS", "description": "lokalen Audit-Index prüfen"}],
            },
            {
                "id": "config", "name": "CONFIG / SAFETY", "module": "utils.config",
                "category": "coordination", "icon": "⚙", "accent": "orange",
                "summary": "Safe-Mode, Simulation und lokale Betriebsgrenzen sichtbar machen.",
                "explain": "Liest nur die nicht-geheimen Sicherheitsoptionen der Control Plane. Einstellungen werden nicht still aus dem Tool Atlas verändert.",
                "boundary": "SAFE SETTINGS / READ ONLY",
                "actions": [{"id": "safe_settings", "label": "SETTINGS LESEN", "description": "Safety-Konfiguration prüfen"}],
            },
            {
                "id": "control_plane", "name": "CONTROL PLANE", "module": "core.control_plane",
                "category": "coordination", "icon": "◈", "accent": "red",
                "summary": "Single Source of Do, Audit Trail und Agent-Kontext.",
                "explain": "Der zentrale Datenkern. Jeder Tool-Run wird hier mit Zeitpunkt, Modus und Ergebnis protokolliert.",
                "boundary": "SOT / AUDITED",
                "actions": [{"id": "sync_check", "label": "SYNC CHECK", "description": "gemeinsamen Zustand prüfen"}],
            },
            {
                "id": "defense_ops", "name": "DEFENSE OPS", "module": "core.defense_ops",
                "category": "defense", "icon": "⌘", "accent": "cyan",
                "summary": "Bounded Capture, Proxy-Check und MAC-Vorschau.",
                "explain": "Die sichere lokale Toolchain: nur Header-Metadaten, nur Profil-Inspektion, keine MAC-Mutation und keine beliebige Shell.",
                "boundary": "ALLOWLIST / BOUNDED",
                "actions": [{"id": "capability_scan", "label": "CAPABILITIES", "description": "lokale Toolchain prüfen"}],
            },
        ]

    @staticmethod
    def _command(command: str, args: List[str], timeout: int = 3) -> Dict[str, Any]:
        executable = shutil.which(command)
        if not executable:
            return {"available": False, "command": command, "output": "not installed"}
        try:
            result = subprocess.run([executable, *args], capture_output=True, text=True, timeout=timeout, check=False)
            output = (result.stdout or result.stderr or "").strip()
            return {"available": result.returncode == 0, "command": command, "output": output[:700], "returncode": result.returncode}
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"available": False, "command": command, "output": str(exc)[:240]}

    def _tool_status(self, definition: Dict[str, Any]) -> Dict[str, Any]:
        tool_id = definition["id"]
        if tool_id in {"network_scanner", "port_manager", "process_monitor", "forensics", "action_logger", "config", "control_plane"}:
            availability, status = True, "ready"
        elif tool_id == "wifi_auditor":
            availability, status = bool(shutil.which("iw")), "ready" if shutil.which("iw") else "limited"
        elif tool_id == "wireguard":
            availability, status = bool(shutil.which("wg")), "ready" if shutil.which("wg") else "limited"
        elif tool_id == "anonymizer":
            proxy = self.defense_ops.proxy_status()
            availability, status = proxy["available"], "ready" if proxy["available"] else "limited"
        elif tool_id == "router_tools":
            availability, status = bool(shutil.which("ip")), "ready" if shutil.which("ip") else "limited"
        elif tool_id == "file_integrity":
            baseline = Path.home() / ".cyberguardian" / "baseline.json"
            availability, status = baseline.exists(), "ready" if baseline.exists() else "limited"
        elif tool_id == "backup_rollback":
            availability, status = True, "ready"
        elif tool_id in {"ids_ips", "defense_ops"}:
            availability, status = True, "simulated" if tool_id == "ids_ips" else "ready"
        else:
            availability, status = True, "ready"
        return {"availability": availability, "status": status}

    def catalog(self) -> List[Dict[str, Any]]:
        state = self.control_plane.snapshot()
        tool_states = state.get("tool_states", {})
        runs = state.get("tool_runs", [])
        output = []
        for definition in self._definitions:
            item = deepcopy(definition)
            item.update(self._tool_status(definition))
            item["enabled"] = tool_states.get(item["id"], {}).get("enabled", True)
            item["last_run"] = next((deepcopy(run) for run in runs if run.get("tool_id") == item["id"]), None)
            output.append(item)
        return output

    def _interfaces(self) -> List[str]:
        return self.defense_ops.interfaces()

    def _listening_ports(self) -> List[Dict[str, Any]]:
        ports: List[Dict[str, Any]] = []
        proc_file = Path("/proc/net/tcp")
        if proc_file.exists():
            for line in proc_file.read_text(encoding="ascii", errors="ignore").splitlines()[1:]:
                fields = line.split()
                if len(fields) < 4 or fields[3] != "0A":
                    continue
                try:
                    port = int(fields[1].rsplit(":", 1)[1], 16)
                    address = fields[1].split(":", 1)[0]
                    ports.append({"address": address, "port": port, "protocol": "TCP", "source": "/proc"})
                except (ValueError, IndexError):
                    continue
        return ports[:24]

    def _process_snapshot(self) -> List[Dict[str, Any]]:
        processes: List[Dict[str, Any]] = []
        proc_root = Path("/proc")
        if proc_root.exists():
            for entry in proc_root.iterdir():
                if not entry.name.isdigit() or len(processes) >= 16:
                    continue
                try:
                    name = (entry / "comm").read_text(encoding="utf-8", errors="ignore").strip()
                    processes.append({"pid": int(entry.name), "name": name or "unknown", "source": "/proc"})
                except (OSError, ValueError):
                    continue
        return sorted(processes, key=lambda item: item["pid"])[:16]

    def _run_action(self, tool_id: str, action: str) -> Dict[str, Any]:
        if tool_id == "network_scanner" and action == "interface_inventory":
            interfaces = self._interfaces()
            return {"mode": "read-only", "summary": f"{len(interfaces)} lokale Interfaces gefunden.", "details": {"interfaces": interfaces}}
        if tool_id == "wifi_auditor" and action == "radio_status":
            result = self._command("iw", ["dev"])
            return {"mode": "read-only" if result["available"] else "not-installed", "summary": "WLAN-Radio geprüft." if result["available"] else "iw nicht installiert; nur Status notiert.", "details": {"output": result["output"][:500], "available": result["available"]}}
        if tool_id == "port_manager" and action == "listening_ports":
            ports = self._listening_ports()
            return {"mode": "read-only", "summary": f"{len(ports)} lokale Listening-Sockets gefunden.", "details": {"ports": ports}}
        if tool_id == "process_monitor" and action == "process_snapshot":
            processes = self._process_snapshot()
            return {"mode": "read-only", "summary": f"{len(processes)} Prozesse im Snapshot erfasst.", "details": {"processes": processes}}
        if tool_id == "wireguard" and action == "vpn_status":
            result = self._command("wg", ["show", "interfaces"])
            interfaces = result["output"].split() if result["available"] else []
            return {"mode": "read-only" if result["available"] else "not-installed", "summary": f"{len(interfaces)} WireGuard-Interfaces sichtbar." if result["available"] else "wg nicht installiert; kein Tunnelstatus verfügbar.", "details": {"interfaces": interfaces, "available": result["available"]}}
        if tool_id == "anonymizer" and action == "proxy_status":
            proxy = self.defense_ops.proxy_status()
            return {"mode": "inspection-only", "summary": "Proxyprofil geprüft; keine Route gestartet.", "details": proxy}
        if tool_id == "router_tools" and action == "link_status":
            result = self._command("ip", ["-brief", "link"])
            return {"mode": "read-only" if result["available"] else "not-installed", "summary": "Lokale Link-Ansicht gelesen." if result["available"] else "ip nicht verfügbar; Linkstatus nicht gelesen.", "details": {"output": result["output"][:600], "available": result["available"]}}
        if tool_id == "ids_ips" and action == "detection_posture":
            return {"mode": "simulation", "summary": "Defensive Watch-Posture dokumentiert; keine Blockregel aktiviert.", "details": {"posture": "observe", "response": "none", "sensor": "browser-safe simulation"}}
        if tool_id == "file_integrity" and action == "baseline_status":
            baseline = Path.home() / ".cyberguardian" / "baseline.json"
            exists = baseline.exists()
            size = baseline.stat().st_size if exists else 0
            return {"mode": "read-only", "summary": "Baseline gefunden." if exists else "Keine Baseline gefunden.", "details": {"path": str(baseline), "exists": exists, "bytes": size}}
        if tool_id == "forensics" and action == "system_snapshot":
            return {"mode": "read-only", "summary": "Lokale Triage-Fakten gesammelt.", "details": {"os": f"{platform.system()} {platform.release()}", "hostname": socket.gethostname(), "python": platform.python_version(), "cwd": os.getcwd()}}
        if tool_id == "backup_rollback" and action == "backup_inventory":
            backup_dir = Path.home() / ".cyberguardian" / "backups"
            files = sorted(item.name for item in backup_dir.iterdir() if item.is_file()) if backup_dir.exists() else []
            return {"mode": "read-only", "summary": f"{len(files)} lokale Backups gefunden.", "details": {"directory": str(backup_dir), "files": files[:40]}}
        if tool_id == "action_logger" and action == "audit_inventory":
            snapshot = self.control_plane.snapshot()
            return {"mode": "audited", "summary": f"{len(snapshot.get('activity', []))} Activity-Einträge und {len(snapshot.get('tool_runs', []))} Tool-Runs im lokalen Trail.", "details": {"activity_entries": len(snapshot.get("activity", [])), "tool_runs": len(snapshot.get("tool_runs", [])), "retention": snapshot.get("settings", {}).get("retention", "local only")}}
        if tool_id == "config" and action == "safe_settings":
            snapshot = self.control_plane.snapshot()
            settings = snapshot.get("settings", {})
            safe_settings = {key: value for key, value in settings.items() if key in {"safe_mode", "simulation_mode", "network_actions", "retention"}}
            return {"mode": "read-only", "summary": "Nicht-geheime Safety-Einstellungen gelesen.", "details": safe_settings}
        if tool_id == "control_plane" and action == "sync_check":
            snapshot = self.control_plane.snapshot()
            return {"mode": "audited", "summary": "Single Source of Do ist erreichbar und konsistent lesbar.", "details": {"updated_at": snapshot.get("updated_at"), "stats": snapshot.get("stats", {}), "schema": snapshot.get("schema")}}
        if tool_id == "defense_ops" and action == "capability_scan":
            overview = self.defense_ops.overview()
            return {"mode": "allowlisted", "summary": f"Defense Ops geprüft; Capture-Engine: {overview.get('capture_engine')}.", "details": overview}
        raise ValueError("Tool-Aktion nicht erlaubt")

    def run(self, tool_id: Any, action: Any) -> Dict[str, Any]:
        clean_tool = _clean(tool_id, "", 60)
        clean_action = _clean(action, "", 60)
        definition = next((item for item in self._definitions if item["id"] == clean_tool), None)
        if not definition:
            raise KeyError(f"Tool nicht gefunden: {clean_tool}")
        if clean_action not in {item["id"] for item in definition["actions"]}:
            raise ValueError("Tool-Aktion nicht erlaubt")
        started = _now()
        try:
            result = self._run_action(clean_tool, clean_action)
            status = "completed"
            summary = result.get("summary", "Tool-Run abgeschlossen.")
            error = ""
        except Exception as exc:
            result = {"mode": "error", "summary": "Tool-Run konnte nicht abgeschlossen werden.", "details": {}}
            status = "error"
            summary = result["summary"]
            error = _clean(exc, "unknown error", 240)
        run = {
            "id": f"RUN-{datetime.now(timezone.utc).strftime('%H%M%S%f')[-8:]}",
            "tool_id": clean_tool,
            "action": clean_action,
            "status": status,
            "mode": result.get("mode", "read-only"),
            "safe": True,
            "summary": summary,
            "details": result.get("details", {}),
            "error": error,
            "started_at": started,
            "completed_at": _now(),
        }
        return run


__all__ = ["ToolCatalog"]
