#!/usr/bin/env python3
"""CyberGuardian single source of truth for defensive agent coordination.

The control plane is intentionally small and dependency free.  It stores the
shared mission state that every local/browser agent can read: current plans,
agent presence, defensive honeypot configurations, safe telemetry and the
operator activity stream.

Important safety boundary
-------------------------
This module does not open sockets, probe hosts, execute payloads or relay
traffic.  A honeypot in the web dashboard is a *virtual, simulation-only*
control-plane record.  Signals can be injected as clearly labelled demo
telemetry so a team can exercise its response workflow without attacking
anything.
"""

from __future__ import annotations

import copy
import json
import os
import secrets
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


PLAN_STATUSES = {"queued", "active", "blocked", "done"}
PLAN_PRIORITIES = {"low", "normal", "high", "critical"}
INCIDENT_STATUSES = {"open", "acknowledged"}
SEVERITIES = {"low", "medium", "high", "critical"}


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""

    return datetime.now(timezone.utc)


def iso(dt: Optional[datetime] = None) -> str:
    """Serialize a timestamp in the compact format used by the API."""

    return (dt or utc_now()).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _clean(value: Any, default: str = "", limit: int = 160) -> str:
    """Turn user input into a short, single-line value for the shared state."""

    if value is None:
        return default
    text = " ".join(str(value).strip().split())
    return text[:limit] if text else default


def _clamp(value: Any, lower: int, upper: int, default: int) -> int:
    try:
        return max(lower, min(upper, int(value)))
    except (TypeError, ValueError):
        return default


class ControlPlane:
    """Thread-safe JSON-backed coordination store.

    The browser and local automation agents share this file through the HTTP
    API.  Writes are atomic (temporary file + replace), so a page refresh or a
    second agent cannot leave a half-written state behind.
    """

    def __init__(self, store_path: Optional[os.PathLike[str] | str] = None):
        default_dir = Path(os.environ.get("CYBERGUARDIAN_DATA_DIR", Path.home() / ".cyberguardian"))
        self.store_path = Path(store_path) if store_path else default_dir / "control_plane.json"
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._state = self._load_or_seed()

    # ------------------------------------------------------------------
    # Persistence and state projection
    # ------------------------------------------------------------------
    def _load_or_seed(self) -> Dict[str, Any]:
        if self.store_path.exists():
            try:
                with self.store_path.open("r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict) and loaded.get("schema") == "cyberguardian-control-plane-v1":
                    return loaded
            except (OSError, json.JSONDecodeError, TypeError):
                # A corrupt local state should never prevent the defensive UI
                # from starting.  Keep the broken file for forensic review.
                try:
                    backup = self.store_path.with_suffix(".corrupt.json")
                    self.store_path.replace(backup)
                except OSError:
                    pass
        state = self._seed_state()
        self._persist(state)
        return state

    def _persist(self, state: Dict[str, Any]) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.store_path.with_suffix(self.store_path.suffix + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(state, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        temporary.replace(self.store_path)

    def _save(self) -> None:
        self._state["updated_at"] = iso()
        self._persist(self._state)

    def _seed_state(self) -> Dict[str, Any]:
        now = utc_now()
        ago = lambda minutes: iso(now - timedelta(minutes=minutes))
        return {
            "schema": "cyberguardian-control-plane-v1",
            "version": "0.3.0",
            "updated_at": iso(now),
            "settings": {
                "safe_mode": True,
                "simulation_mode": True,
                "network_actions": "disabled in browser lab",
                "retention": "local only",
            },
            "agents": [
                {
                    "id": "agent-orbit",
                    "name": "ORBIT",
                    "role": "Triage & correlation",
                    "focus": "cross-agent context",
                    "status": "online",
                    "signal": 92,
                    "last_seen": ago(1),
                },
                {
                    "id": "agent-sentinel",
                    "name": "SENTINEL",
                    "role": "Exposure watch",
                    "focus": "approved lab perimeter",
                    "status": "online",
                    "signal": 87,
                    "last_seen": ago(2),
                },
                {
                    "id": "agent-kai",
                    "name": "KAI",
                    "role": "Deception lab",
                    "focus": "virtual honeypot telemetry",
                    "status": "online",
                    "signal": 78,
                    "last_seen": ago(1),
                },
                {
                    "id": "agent-mika",
                    "name": "MIKA",
                    "role": "Evidence keeper",
                    "focus": "chain of custody",
                    "status": "standby",
                    "signal": 64,
                    "last_seen": ago(18),
                },
            ],
            "plans": [
                {
                    "id": "PLN-001",
                    "title": "Edge-Layer Baseline",
                    "objective": "Inventar der exponierten Dienste in der genehmigten Laborzone festhalten.",
                    "owner": "SENTINEL",
                    "status": "active",
                    "priority": "high",
                    "progress": 68,
                    "broadcast": True,
                    "created_by": "system",
                    "created_at": ago(44),
                    "updated_at": ago(4),
                },
                {
                    "id": "PLN-002",
                    "title": "Honeypot Relay v2",
                    "objective": "Virtuelle Signale für die Verteidigungsübung sauber korrelieren.",
                    "owner": "KAI",
                    "status": "queued",
                    "priority": "normal",
                    "progress": 36,
                    "broadcast": True,
                    "created_by": "system",
                    "created_at": ago(31),
                    "updated_at": ago(9),
                },
                {
                    "id": "PLN-003",
                    "title": "Evidence Chain",
                    "objective": "Erkenntnisse lokal, nachvollziehbar und ohne Gegenmaßnahmen ablegen.",
                    "owner": "ORBIT",
                    "status": "done",
                    "priority": "low",
                    "progress": 100,
                    "broadcast": True,
                    "created_by": "system",
                    "created_at": ago(87),
                    "updated_at": ago(22),
                },
            ],
            "honeypots": [
                {
                    "id": "HP-001",
                    "name": "KASA-API",
                    "service": "SSH decoy",
                    "port": 2222,
                    "profile": "Neo-Tokyo edge",
                    "status": "active",
                    "mode": "simulation",
                    "signals": 14,
                    "created_at": ago(56),
                    "last_signal": ago(3),
                },
                {
                    "id": "HP-002",
                    "name": "MIRAI-VAULT",
                    "service": "HTTP decoy",
                    "port": 8088,
                    "profile": "quiet archive",
                    "status": "standby",
                    "mode": "simulation",
                    "signals": 0,
                    "created_at": ago(21),
                    "last_signal": None,
                },
            ],
            "incidents": [
                {
                    "id": "INC-014",
                    "honeypot_id": "HP-001",
                    "source": "203.0.113.42",
                    "tactic": "credential probe",
                    "severity": "high",
                    "status": "open",
                    "simulated": True,
                    "created_at": ago(3),
                },
                {
                    "id": "INC-013",
                    "honeypot_id": "HP-001",
                    "source": "198.51.100.19",
                    "tactic": "path discovery",
                    "severity": "medium",
                    "status": "acknowledged",
                    "simulated": True,
                    "created_at": ago(12),
                },
            ],
            "honeypot_logs": [
                {
                    "id": "SIG-014",
                    "honeypot_id": "HP-001",
                    "source": "203.0.113.42",
                    "destination": "KASA-API:2222",
                    "tactic": "credential probe",
                    "severity": "high",
                    "action": "captured / no response",
                    "simulated": True,
                    "created_at": ago(3),
                },
                {
                    "id": "SIG-013",
                    "honeypot_id": "HP-001",
                    "source": "198.51.100.19",
                    "destination": "KASA-API:2222",
                    "tactic": "path discovery",
                    "severity": "medium",
                    "action": "captured / no response",
                    "simulated": True,
                    "created_at": ago(12),
                },
                {
                    "id": "SIG-012",
                    "honeypot_id": "HP-001",
                    "source": "192.0.2.77",
                    "destination": "KASA-API:2222",
                    "tactic": "banner check",
                    "severity": "low",
                    "action": "captured / no response",
                    "simulated": True,
                    "created_at": ago(29),
                },
            ],
            "messages": [
                {
                    "id": "MSG-009",
                    "from": "ORBIT",
                    "to": "ALL AGENTS",
                    "kind": "broadcast",
                    "text": "SOT synchronisiert: Evidence Chain ist abgeschlossen.",
                    "created_at": ago(8),
                },
                {
                    "id": "MSG-008",
                    "from": "KAI",
                    "to": "SENTINEL",
                    "kind": "handoff",
                    "text": "HP-001 meldet ein neues simuliertes Signal; bitte nur korrelieren, nicht reagieren.",
                    "created_at": ago(3),
                },
                {
                    "id": "MSG-007",
                    "from": "MIKA",
                    "to": "ALL AGENTS",
                    "kind": "policy",
                    "text": "Defensive Leitplanke aktiv: Browser-Lab erzeugt keine echten Netzwerkantworten.",
                    "created_at": ago(18),
                },
            ],
            "activity": [
                {
                    "id": "EVT-021",
                    "kind": "honeypot.signal",
                    "tone": "alert",
                    "text": "HP-001 hat ein simuliertes credential probe Signal eingefangen.",
                    "created_at": ago(3),
                },
                {
                    "id": "EVT-020",
                    "kind": "plan.sync",
                    "tone": "cyan",
                    "text": "ORBIT hat den Mesh-Kontext an alle Agenten verteilt.",
                    "created_at": ago(8),
                },
                {
                    "id": "EVT-019",
                    "kind": "policy",
                    "tone": "green",
                    "text": "Safe mode bestätigt: Nur lokale Simulation und defensive Beobachtung.",
                    "created_at": ago(18),
                },
            ],
        }

    def snapshot(self) -> Dict[str, Any]:
        """Return a copy safe to serialize to any connected agent."""

        with self._lock:
            state = copy.deepcopy(self._state)
            state["stats"] = self._derived_stats(state)
            state["updated_at"] = self._state.get("updated_at", iso())
            return state

    @staticmethod
    def _derived_stats(state: Dict[str, Any]) -> Dict[str, int]:
        agents = state.get("agents", [])
        plans = state.get("plans", [])
        incidents = state.get("incidents", [])
        honeypots = state.get("honeypots", [])
        logs = state.get("honeypot_logs", [])
        return {
            "online_agents": sum(1 for agent in agents if agent.get("status") == "online"),
            "total_agents": len(agents),
            "active_plans": sum(1 for plan in plans if plan.get("status") == "active"),
            "open_incidents": sum(1 for incident in incidents if incident.get("status") == "open"),
            "active_honeypots": sum(1 for pot in honeypots if pot.get("status") == "active"),
            "signals_today": len(logs),
        }

    # ------------------------------------------------------------------
    # Mutation helpers — every mutation is visible to every agent
    # ------------------------------------------------------------------
    def _new_id(self, prefix: str) -> str:
        return f"{prefix}-{secrets.token_hex(2).upper()}"

    def _activity(self, kind: str, text: str, tone: str = "cyan") -> None:
        self._state.setdefault("activity", []).insert(
            0,
            {
                "id": self._new_id("EVT"),
                "kind": _clean(kind, "event", 40),
                "tone": _clean(tone, "cyan", 16),
                "text": _clean(text, "", 220),
                "created_at": iso(),
            },
        )
        self._state["activity"] = self._state["activity"][:80]

    def _message(self, sender: str, recipient: str, text: str, kind: str = "broadcast") -> Dict[str, Any]:
        message = {
            "id": self._new_id("MSG"),
            "from": _clean(sender, "OPERATOR", 40),
            "to": _clean(recipient, "ALL AGENTS", 60),
            "kind": _clean(kind, "broadcast", 24),
            "text": _clean(text, "", 240),
            "created_at": iso(),
        }
        self._state.setdefault("messages", []).insert(0, message)
        self._state["messages"] = self._state["messages"][:80]
        return message

    def register_agent(self, name: Any, role: Any, focus: Any = "shared context") -> Dict[str, Any]:
        clean_name = _clean(name, "NEW-AGENT", 32).upper()
        clean_role = _clean(role, "defensive observer", 80)
        clean_focus = _clean(focus, "shared context", 100)
        with self._lock:
            existing = next((a for a in self._state["agents"] if a["name"] == clean_name), None)
            if existing:
                existing.update({"role": clean_role, "focus": clean_focus, "status": "online", "last_seen": iso()})
                agent = existing
            else:
                agent = {
                    "id": self._new_id("AGT"),
                    "name": clean_name,
                    "role": clean_role,
                    "focus": clean_focus,
                    "status": "online",
                    "signal": 70,
                    "last_seen": iso(),
                }
                self._state["agents"].append(agent)
            self._message(clean_name, "ALL AGENTS", f"{clean_name} ist im gemeinsamen Leitstand online.", "presence")
            self._activity("agent.presence", f"{clean_name} hat den Mesh-Kontext übernommen.", "green")
            self._save()
            return copy.deepcopy(agent)

    def create_plan(
        self,
        title: Any,
        objective: Any,
        owner: Any = "ORBIT",
        priority: Any = "normal",
        created_by: Any = "OPERATOR",
    ) -> Dict[str, Any]:
        plan = {
            "id": self._new_id("PLN"),
            "title": _clean(title, "Untitled defensive plan", 90),
            "objective": _clean(objective, "Defensive task without network action.", 240),
            "owner": _clean(owner, "ORBIT", 32).upper(),
            "status": "queued",
            "priority": _clean(priority, "normal", 16).lower(),
            "progress": 0,
            "broadcast": True,
            "created_by": _clean(created_by, "OPERATOR", 40),
            "created_at": iso(),
            "updated_at": iso(),
        }
        if plan["priority"] not in PLAN_PRIORITIES:
            plan["priority"] = "normal"
        with self._lock:
            self._state["plans"].insert(0, plan)
            self._message(
                plan["owner"],
                "ALL AGENTS",
                f"Neuer Plan {plan['id']}: {plan['title']} — Kontext ist für den Mesh sichtbar.",
                "plan",
            )
            self._activity("plan.created", f"{plan['id']} wurde an alle Agenten broadcastet.", "magenta")
            self._save()
            return copy.deepcopy(plan)

    def update_plan(self, plan_id: str, status: Any = None, progress: Any = None) -> Dict[str, Any]:
        with self._lock:
            plan = next((p for p in self._state["plans"] if p["id"] == plan_id), None)
            if not plan:
                raise KeyError(f"Plan nicht gefunden: {plan_id}")
            if status is not None:
                next_status = _clean(status, plan["status"], 16).lower()
                if next_status not in PLAN_STATUSES:
                    raise ValueError("Ungültiger Planstatus")
                plan["status"] = next_status
            if progress is not None:
                plan["progress"] = _clamp(progress, 0, 100, plan.get("progress", 0))
            if plan["status"] == "done":
                plan["progress"] = 100
            plan["updated_at"] = iso()
            self._message(
                plan.get("owner", "ORBIT"),
                "ALL AGENTS",
                f"{plan_id} aktualisiert: {plan['status']} / {plan['progress']}%.",
                "plan.update",
            )
            self._activity("plan.updated", f"{plan_id} ist jetzt {plan['status']}.", "cyan")
            self._save()
            return copy.deepcopy(plan)

    def create_honeypot(self, name: Any, service: Any, port: Any, profile: Any = "quiet archive") -> Dict[str, Any]:
        try:
            numeric_port = int(port)
        except (TypeError, ValueError):
            raise ValueError("Port muss eine Zahl sein")
        if not 1 <= numeric_port <= 65535:
            raise ValueError("Port muss zwischen 1 und 65535 liegen")
        honeypot = {
            "id": self._new_id("HP"),
            "name": _clean(name, "UNNAMED-DECOY", 40).upper(),
            "service": _clean(service, "generic decoy", 60),
            "port": numeric_port,
            "profile": _clean(profile, "quiet archive", 80),
            "status": "standby",
            "mode": "simulation",
            "signals": 0,
            "created_at": iso(),
            "last_signal": None,
        }
        with self._lock:
            self._state["honeypots"].insert(0, honeypot)
            self._message("KAI", "ALL AGENTS", f"{honeypot['id']} ist als virtuelle Deception-Zone bereit.", "honeypot")
            self._activity("honeypot.created", f"{honeypot['name']} erstellt — nur Simulation, kein Listener.", "green")
            self._save()
            return copy.deepcopy(honeypot)

    def toggle_honeypot(self, honeypot_id: str, active: Any = True) -> Dict[str, Any]:
        with self._lock:
            honeypot = next((p for p in self._state["honeypots"] if p["id"] == honeypot_id), None)
            if not honeypot:
                raise KeyError(f"Honeypot nicht gefunden: {honeypot_id}")
            is_active = bool(active)
            honeypot["status"] = "active" if is_active else "standby"
            self._activity(
                "honeypot.status",
                f"{honeypot['name']} ist jetzt {'aktiv' if is_active else 'standby'} (Simulation).",
                "green" if is_active else "cyan",
            )
            self._save()
            return copy.deepcopy(honeypot)

    def simulate_signal(
        self,
        honeypot_id: str,
        source: Any = "198.51.100.24",
        tactic: Any = "banner check",
        severity: Any = "medium",
    ) -> Dict[str, Any]:
        """Add harmless, explicit demo telemetry to a virtual honeypot."""

        severity_value = _clean(severity, "medium", 16).lower()
        if severity_value not in SEVERITIES:
            severity_value = "medium"
        with self._lock:
            honeypot = next((p for p in self._state["honeypots"] if p["id"] == honeypot_id), None)
            if not honeypot:
                raise KeyError(f"Honeypot nicht gefunden: {honeypot_id}")
            timestamp = iso()
            clean_source = _clean(source, "198.51.100.24", 64)
            clean_tactic = _clean(tactic, "banner check", 80)
            signal_number = int(honeypot.get("signals", 0)) + 1
            signal = {
                "id": self._new_id("SIG"),
                "honeypot_id": honeypot_id,
                "source": clean_source,
                "destination": f"{honeypot['name']}:{honeypot['port']}",
                "tactic": clean_tactic,
                "severity": severity_value,
                "action": "captured / no response",
                "simulated": True,
                "created_at": timestamp,
            }
            incident = {
                "id": self._new_id("INC"),
                "honeypot_id": honeypot_id,
                "source": clean_source,
                "tactic": clean_tactic,
                "severity": severity_value,
                "status": "open",
                "simulated": True,
                "created_at": timestamp,
            }
            honeypot["signals"] = signal_number
            honeypot["last_signal"] = timestamp
            self._state["honeypot_logs"].insert(0, signal)
            self._state["honeypot_logs"] = self._state["honeypot_logs"][:200]
            self._state["incidents"].insert(0, incident)
            self._state["incidents"] = self._state["incidents"][:100]
            self._message(
                "KAI",
                "ORBIT / SENTINEL",
                f"{honeypot['name']} fing Signal {signal['id']} ein. Nur Beobachtung; keine Gegenaktion.",
                "signal",
            )
            self._activity(
                "honeypot.signal",
                f"{honeypot['name']} / {clean_tactic} / {severity_value} — simuliert erfasst.",
                "alert" if severity_value in {"high", "critical"} else "yellow",
            )
            self._save()
            return {"signal": copy.deepcopy(signal), "incident": copy.deepcopy(incident), "honeypot": copy.deepcopy(honeypot)}

    def acknowledge_incident(self, incident_id: str) -> Dict[str, Any]:
        with self._lock:
            incident = next((i for i in self._state["incidents"] if i["id"] == incident_id), None)
            if not incident:
                raise KeyError(f"Incident nicht gefunden: {incident_id}")
            incident["status"] = "acknowledged"
            incident["acknowledged_at"] = iso()
            self._activity("incident.ack", f"{incident_id} von der Leitstelle bestätigt.", "green")
            self._save()
            return copy.deepcopy(incident)

    def broadcast_message(self, sender: Any, recipient: Any, text: Any, kind: Any = "broadcast") -> Dict[str, Any]:
        clean_text = _clean(text, "", 240)
        if not clean_text:
            raise ValueError("Nachricht darf nicht leer sein")
        with self._lock:
            message = self._message(sender, recipient, clean_text, kind)
            self._activity("message.broadcast", f"{message['from']} hat Kontext an {message['to']} gesendet.", "magenta")
            self._save()
            return copy.deepcopy(message)


__all__ = ["ControlPlane"]
