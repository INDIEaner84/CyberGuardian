"""Bounded, offline classification of already stored defensive events.

This is NOT a sensor, Sigma interpreter, import endpoint or live detection.
No caller-provided patterns, files, targets or commands are executed.
"""
from __future__ import annotations

from typing import Any

MAX_ROWS_PER_SOURCE = 100
RULES = (
    {"id": "VM-PATH-01", "title": "VM-Pfad-Erkundung", "source": "vm", "field": "rule", "value": "path-discovery", "severity": "medium"},
    {"id": "VM-LOGIN-01", "title": "VM-Login-Wiederholungen", "source": "vm", "field": "rule", "value": "login-retries", "severity": "high"},
    {"id": "HP-CRED-01", "title": "Simulierter Credential-Probe", "source": "honeypot", "field": "tactic", "value": "credential probe", "severity": "high"},
    {"id": "HP-PATH-01", "title": "Simulierte Pfad-Erkundung", "source": "honeypot", "field": "tactic", "value": "path discovery", "severity": "medium"},
)


def rule_catalog() -> list[dict[str, str]]:
    """Expose only the fixed, explainable rule metadata (never executable code)."""
    return [{"id": rule["id"], "title": rule["title"], "source": rule["source"],
             "severity": rule["severity"], "condition": f"{rule['field']} == {rule['value']}"}
            for rule in RULES]


def replay(state: dict[str, Any], source: str = "all", limit: int = 40) -> dict[str, Any]:
    if not isinstance(source, str) or source not in {"all", "vm", "honeypot"}:
        raise ValueError("Replay-Quelle muss all, vm oder honeypot sein")
    if type(limit) is not int or not 1 <= limit <= MAX_ROWS_PER_SOURCE:
        raise ValueError("Replay-Limit muss eine Zahl zwischen 1 und 100 sein")
    if not isinstance(state, dict):
        raise ValueError("Ungültiger lokaler Zustand")

    inputs = []
    if source in {"all", "vm"}:
        inputs.append(("vm", state.get("vm_alerts", [])))
    if source in {"all", "honeypot"}:
        inputs.append(("honeypot", state.get("honeypot_logs", [])))
    matches: list[dict[str, Any]] = []
    evaluated = 0
    truncated = False
    for name, rows in inputs:
        if not isinstance(rows, list):
            raise ValueError("Ungültige lokale Ereignisliste")
        truncated |= len(rows) > limit
        for event in rows[:limit]:
            evaluated += 1
            if not isinstance(event, dict):
                continue
            # Never relabel synthetic telemetry as observed (or vice versa).
            if event.get("simulated") is not (name == "honeypot"):
                continue
            for rule in RULES:
                if rule["source"] != name or event.get(rule["field"]) != rule["value"]:
                    continue
                event_id = event.get("id")
                if not isinstance(event_id, str) or not event_id or len(event_id) > 80:
                    break
                run_id = event.get("run_id", "") if name == "vm" else ""
                if not isinstance(run_id, str) or len(run_id) != 32 or any(c not in "0123456789abcdef" for c in run_id):
                    run_id = ""
                matches.append({"rule_id": rule["id"], "title": rule["title"],
                                "severity": rule["severity"], "event_id": event_id,
                                "source": name, "simulated": name == "honeypot", "run_id": run_id,
                                "explanation": f"Gespeichertes Feld {rule['field']} entspricht {rule['value']}."})
                break
    return {"mode": "offline-replay", "live_detection": False, "source": source,
            "limit_per_source": limit, "evaluated": evaluated, "match_count": len(matches),
            "truncated": truncated, "matches": matches,
            "notice": "Nur vorhandene Ereignisse neu eingeordnet; keine neue Sensor-Erkennung und keine Gegenmaßnahme."}
