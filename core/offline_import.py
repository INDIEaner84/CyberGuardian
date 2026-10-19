"""Parse bounded Zeek notice / Suricata EVE JSON-lines into untrusted metadata.

Only fields explicitly selected below survive. No filename, payload, message,
packet content, raw line or browser-supplied path is retained or executed.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import math
from datetime import datetime, timezone
from typing import Any

MAX_IMPORT_BYTES = 48 * 1024
MAX_LINES = 100
MAX_ALERTS = 50
MAX_LINE_BYTES = 2048
FORMATS = {"suricata-eve", "zeek-notice"}


def _label(value: Any) -> str:
    if (not isinstance(value, str) or not 1 <= len(value) <= 100 or not value.isprintable()):
        raise ValueError("Alert-Signatur/Zeek-Note muss druckbarer Text mit höchstens 100 Zeichen sein")
    return value


def _ip(value: Any, required: bool = True) -> str:
    if value in (None, "") and not required:
        return "—"
    if not isinstance(value, str) or len(value) > 45:
        raise ValueError("Ungültige IP-Adresse im Offline-Log")
    try:
        return str(ipaddress.ip_address(value))
    except ValueError as exc:
        raise ValueError("Ungültige IP-Adresse im Offline-Log") from exc


def _timestamp(value: Any, source_format: str) -> str:
    if source_format == "zeek-notice":
        if type(value) not in (float, int) or not math.isfinite(value) or not 946684800 <= value <= 4102444800:
            raise ValueError("Ungültiger Zeek-Zeitstempel")
        timestamp = datetime.fromtimestamp(value, timezone.utc)
    else:
        if not isinstance(value, str) or len(value) > 40:
            raise ValueError("Ungültiger Suricata-Zeitstempel")
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("Ungültiger Suricata-Zeitstempel") from exc
        if timestamp.tzinfo is None:
            raise ValueError("Suricata-Zeitstempel benötigt Zeitzone")
        timestamp = timestamp.astimezone(timezone.utc)
        if not 2000 <= timestamp.year <= 2100:
            raise ValueError("Suricata-Zeitstempel außerhalb des erlaubten Bereichs")
    return timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize(item: dict[str, Any], source_format: str) -> dict[str, Any] | None:
    if source_format == "suricata-eve":
        if item.get("event_type") != "alert":
            return None  # Flow, DNS, TLS and payload events are never imported.
        alert = item.get("alert")
        if not isinstance(alert, dict):
            raise ValueError("Suricata-Alert ohne alert-Objekt")
        signature = _label(alert.get("signature"))
        priority = alert.get("severity")
        if type(priority) is not int or priority not in (1, 2, 3):
            raise ValueError("Suricata-Severity muss 1, 2 oder 3 sein")
        severity = {1: "high", 2: "medium", 3: "low"}[priority]
        source = _ip(item.get("src_ip"))
        destination = _ip(item.get("dest_ip"), required=False)
        timestamp = _timestamp(item.get("timestamp"), source_format)
    else:
        signature = _label(item.get("note"))
        source = _ip(item.get("src"))
        destination = _ip(item.get("dst"), required=False)
        timestamp = _timestamp(item.get("ts"), source_format)
        severity = "medium"  # Zeek notices have no standard numeric alert priority.
    identity = json.dumps([source_format, timestamp, source, destination, signature, severity], ensure_ascii=False)
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]
    return {"id": f"IMP-{digest}", "format": source_format, "signature": signature,
            "source_ip": source, "destination_ip": destination, "sensor_timestamp": timestamp,
            "severity": severity, "origin": "offline-import", "verified": False, "live": False}


def parse_import(source_format: Any, content: Any) -> dict[str, Any]:
    if not isinstance(source_format, str) or source_format not in FORMATS:
        raise ValueError("Nur suricata-eve oder zeek-notice als Offline-Format erlaubt")
    if not isinstance(content, str) or not content.strip():
        raise ValueError("Leeres oder ungültiges Offline-Log")
    try:
        encoded = content.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("Offline-Log muss gültiger UTF-8-Text sein") from exc
    if len(encoded) > MAX_IMPORT_BYTES:
        raise ValueError("Offline-Log überschreitet 48 KiB")
    lines = content.splitlines()
    if len(lines) > MAX_LINES:
        raise ValueError("Offline-Log überschreitet 100 Zeilen")
    records: list[dict[str, Any]] = []
    ignored = 0
    for number, line in enumerate(lines, 1):
        if not line.strip():
            continue
        if len(line.encode("utf-8")) > MAX_LINE_BYTES:
            raise ValueError(f"Zeile {number} überschreitet 2048 Bytes")
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Zeile {number} ist kein gültiges JSON-Objekt") from exc
        if not isinstance(item, dict):
            raise ValueError(f"Zeile {number} muss ein JSON-Objekt sein")
        try:
            entry = _normalize(item, source_format)
        except ValueError as exc:
            raise ValueError(f"Zeile {number}: {exc}") from exc
        if entry is None:
            ignored += 1
            continue
        records.append(entry)
        if len(records) > MAX_ALERTS:
            raise ValueError("Offline-Log enthält mehr als 50 Alerts")
    if not records:
        raise ValueError("Keine passenden Alert-/Notice-Ereignisse im Offline-Log")
    return {"format": source_format, "records": records, "ignored_unrelated": ignored}
