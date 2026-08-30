#!/usr/bin/env python3
"""Allowlisted, defensive local observations for the browser cockpit.

This module is intentionally *not* a generic command runner.  It offers three
small operator workflows that are useful while defending an owned machine:

* bounded packet metadata capture, in the style of a Wireshark/tshark view;
* proxychains installation/profile inspection without sending traffic;
* MAC-address inspection and a rotation preview without changing the machine.

No shell is used, all subprocess arguments are constructed from allowlists and
packet capture is capped to a short duration and a small number of metadata
rows.  MAC changes and proxy-routed commands stay outside the browser bridge
so an accidental click cannot cut a host off the network or hide activity.
"""

from __future__ import annotations

import os
import random
import re
import shutil
import socket
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


_INTERFACE_PATTERN = re.compile(r"^[A-Za-z0-9_.:-]{1,32}$")

_CAPTURE_PRESETS = {
    "metadata": {"label": "all metadata", "bpf": []},
    "tcp": {"label": "TCP only", "bpf": ["tcp"]},
    "dns": {"label": "DNS / UDP 53", "bpf": ["udp", "port", "53"]},
    "web": {"label": "HTTP(S)", "bpf": ["tcp", "port", "80"]},
}


class DefenseOps:
    """Safe, bounded local capability adapter used by the web API."""

    def __init__(self, command_runner=None):
        self.command_runner = command_runner or subprocess.run

    # ------------------------------------------------------------------
    # Capability and interface discovery
    # ------------------------------------------------------------------
    @staticmethod
    def _which(*commands: str) -> Optional[str]:
        for command in commands:
            found = shutil.which(command)
            if found:
                return found
        return None

    def interfaces(self) -> List[str]:
        names: List[str] = []
        try:
            names.extend(name for _, name in socket.if_nameindex())
        except (AttributeError, OSError):
            pass
        if not names:
            sys_net = Path("/sys/class/net")
            if sys_net.exists():
                names.extend(item.name for item in sys_net.iterdir())
        # Keep only names that can safely be passed as one argv item.
        return sorted({name for name in names if _INTERFACE_PATTERN.fullmatch(name)}) or ["lo"]

    def capabilities(self) -> Dict[str, Any]:
        tools = {
            "tshark": bool(self._which("tshark")),
            "tcpdump": bool(self._which("tcpdump")),
            "wireshark": bool(self._which("wireshark")),
            "proxychains": bool(self._which("proxychains4", "proxychains")),
            "macchanger": bool(self._which("macchanger")),
            "ip": bool(self._which("ip")),
        }
        capture_engine = "tshark" if tools["tshark"] else "tcpdump" if tools["tcpdump"] else "simulation"
        return {
            "tools": tools,
            "capture_engine": capture_engine,
            "interfaces": self.interfaces(),
            "safe_boundary": {
                "packet_capture": "metadata only / bounded",
                "proxychains": "profile inspection only",
                "mac_changer": "preview only / no mutation",
            },
        }

    # ------------------------------------------------------------------
    # Proxychains — inspect, never route arbitrary browser commands
    # ------------------------------------------------------------------
    def proxy_status(self) -> Dict[str, Any]:
        binary = self._which("proxychains4", "proxychains")
        config_candidates = [
            Path.home() / ".proxychains" / "proxychains.conf",
            Path.home() / ".proxychains" / "proxychains4.conf",
            Path("/etc/proxychains4.conf"),
            Path("/etc/proxychains.conf"),
        ]
        configs = [str(path) for path in config_candidates if path.is_file()]
        return {
            "available": bool(binary),
            "binary": binary or "",
            "configs": configs,
            "configured": bool(binary and configs),
            "mode": "inspection only",
            "message": "Kein Browser-Command wird durch Proxychains geroutet.",
        }

    # ------------------------------------------------------------------
    # MAC identity — read current address and create a harmless preview
    # ------------------------------------------------------------------
    def _validate_interface(self, interface: Any) -> str:
        name = str(interface or "").strip()
        if not _INTERFACE_PATTERN.fullmatch(name) or name not in self.interfaces():
            raise ValueError("Unbekanntes oder ungültiges Interface")
        return name

    def mac_status(self, interface: Any) -> Dict[str, Any]:
        name = self._validate_interface(interface)
        address_path = Path("/sys/class/net") / name / "address"
        current = "unknown"
        try:
            current = address_path.read_text(encoding="ascii").strip().lower()
        except (OSError, UnicodeError):
            pass
        return {
            "interface": name,
            "current": current,
            "macchanger_available": bool(self._which("macchanger")),
            "mode": "read-only",
            "mutated": False,
        }

    def mac_preview(self, interface: Any) -> Dict[str, Any]:
        status = self.mac_status(interface)
        octets = [random.randrange(0, 256) for _ in range(6)]
        # locally administered + unicast; this is only a displayed proposal.
        octets[0] = (octets[0] & 0xFC) | 0x02
        proposed = ":".join(f"{octet:02x}" for octet in octets)
        return {
            **status,
            "proposed": proposed,
            "command_preview": f"sudo macchanger --mac={proposed} {status['interface']}",
            "warning": "Vorschau — der Browser ändert die MAC-Adresse nicht.",
        }

    # ------------------------------------------------------------------
    # Wireshark-like packet metadata capture
    # ------------------------------------------------------------------
    @staticmethod
    def _capture_args(interface: str, duration: int, limit: int, preset: str, engine: str) -> List[str]:
        spec = _CAPTURE_PRESETS[preset]
        if engine == "tshark":
            args = [
                "tshark",
                "-i", interface,
                "-a", f"duration:{duration}",
                "-c", str(limit),
                "-T", "fields",
                "-E", "separator=|",
                "-E", "occurrence=f",
                "-e", "frame.time_epoch",
                "-e", "ip.src",
                "-e", "tcp.srcport",
                "-e", "ip.dst",
                "-e", "tcp.dstport",
                "-e", "_ws.col.Protocol",
            ]
            if spec["bpf"]:
                args.extend(["-f", " ".join(spec["bpf"])])
            return args
        args = ["tcpdump", "-nn", "-l", "-tt", "-c", str(limit), "-i", interface]
        args.extend(spec["bpf"])
        return args

    @staticmethod
    def _parse_tshark(raw: str) -> List[Dict[str, Any]]:
        packets = []
        for line in raw.splitlines():
            fields = line.strip().split("|")
            if not any(field.strip() for field in fields):
                continue
            fields += [""] * (6 - len(fields))
            packets.append({
                "time": fields[0].strip(),
                "source": fields[1].strip() or "—",
                "source_port": fields[2].strip(),
                "destination": fields[3].strip() or "—",
                "destination_port": fields[4].strip(),
                "protocol": fields[5].strip() or "UNKNOWN",
                "synthetic": False,
            })
        return packets

    @staticmethod
    def _parse_tcpdump(raw: str) -> List[Dict[str, Any]]:
        packets = []
        for line in raw.splitlines():
            text = line.strip()
            if not text:
                continue
            # tcpdump output is retained as metadata only; do not attempt to
            # turn arbitrary text into a command or payload.
            packets.append({
                "time": text.split(" ", 1)[0],
                "source": "captured",
                "source_port": "",
                "destination": "metadata row",
                "destination_port": "",
                "protocol": "TCPDUMP",
                "summary": text[:180],
                "synthetic": False,
            })
        return packets

    @staticmethod
    def _synthetic_packets(interface: str, preset: str, limit: int) -> List[Dict[str, Any]]:
        # Documentation-reserved addresses keep the demo unambiguously inert.
        samples = [
            ("192.0.2.10", "192.0.2.1", "TCP", "443", "51834"),
            ("198.51.100.7", "203.0.113.5", "DNS", "53", "41201"),
            ("192.0.2.1", "192.0.2.10", "TCP", "51834", "443"),
            ("203.0.113.5", "198.51.100.7", "HTTPS", "443", "55422"),
        ]
        packets = []
        for index in range(min(limit, len(samples))):
            source, destination, protocol, destination_port, source_port = samples[index]
            if preset == "tcp" and protocol == "DNS":
                protocol = "TCP"
            if preset == "dns":
                protocol, destination_port = "DNS", "53"
            if preset == "web":
                protocol, destination_port = "HTTPS", "443"
            packets.append({
                "time": f"+{index * 0.42:.2f}s",
                "source": source,
                "source_port": source_port,
                "destination": destination,
                "destination_port": destination_port,
                "protocol": protocol,
                "interface": interface,
                "synthetic": True,
            })
        return packets

    def capture_metadata(
        self,
        interface: Any = "lo",
        duration: Any = 5,
        limit: Any = 12,
        preset: Any = "metadata",
    ) -> Dict[str, Any]:
        name = str(interface or "").strip()
        # "any" is a documented tshark/tcpdump pseudo-interface, not a shell value.
        if name != "any":
            name = self._validate_interface(name)
        try:
            seconds = max(1, min(8, int(duration)))
            packet_limit = max(1, min(30, int(limit)))
        except (TypeError, ValueError) as exc:
            raise ValueError("Capture-Dauer oder Paketlimit ungültig") from exc
        preset_name = str(preset or "metadata").lower()
        if preset_name not in _CAPTURE_PRESETS:
            raise ValueError("Unbekanntes Capture-Profil")

        tools = self.capabilities()["tools"]
        engine = "tshark" if tools["tshark"] else "tcpdump" if tools["tcpdump"] else "simulation"
        if engine == "simulation":
            return {
                "ok": True,
                "mode": "simulation",
                "engine": "synthetic",
                "interface": name,
                "preset": _CAPTURE_PRESETS[preset_name]["label"],
                "duration": seconds,
                "limit": packet_limit,
                "packets": self._synthetic_packets(name, preset_name, packet_limit),
                "notice": "tshark/tcpdump nicht gefunden — sichere Demo-Telemetrie angezeigt.",
                "command": "",
            }

        executable = self._which(engine)
        if not executable:  # capability can change between two calls
            raise RuntimeError("Capture-Engine ist nicht mehr verfügbar")
        args = self._capture_args(name, seconds, packet_limit, preset_name, engine)
        # No shell, no stdin, no unbounded process.  Packet content is never requested.
        try:
            result = self.command_runner(
                [executable] + args[1:],
                capture_output=True,
                text=True,
                timeout=seconds + 4,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "ok": False,
                "mode": "timeout",
                "engine": engine,
                "interface": name,
                "packets": [],
                "notice": "Capture wegen Zeitlimit beendet.",
                "error": str(exc),
            }
        if result.returncode != 0:
            return {
                "ok": False,
                "mode": "unavailable",
                "engine": engine,
                "interface": name,
                "packets": [],
                "notice": "Capture konnte nicht gestartet werden — oft fehlen lokale Berechtigungen.",
                "error": (result.stderr or result.stdout or "unknown capture error").strip()[:240],
            }
        packets = self._parse_tshark(result.stdout) if engine == "tshark" else self._parse_tcpdump(result.stdout)
        return {
            "ok": True,
            "mode": "live-metadata",
            "engine": engine,
            "interface": name,
            "preset": _CAPTURE_PRESETS[preset_name]["label"],
            "duration": seconds,
            "limit": packet_limit,
            "packets": packets[:packet_limit],
            "notice": "Nur Header-Metadaten erfasst; kein Payload-Content angefordert.",
            "command": " ".join(args),
        }

    def overview(self) -> Dict[str, Any]:
        capabilities = self.capabilities()
        return {
            **capabilities,
            "proxy": self.proxy_status(),
            "mac": {interface: self.mac_status(interface) for interface in capabilities["interfaces"][:8]},
        }


__all__ = ["DefenseOps"]
