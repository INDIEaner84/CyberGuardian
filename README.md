# CyberGuardian Pro

## Defensives Agenten-Leitpult · Single Source of Do · Honeypot-Simulation

CyberGuardian ist eine lokale Security-Suite mit einem neuen Browser-Cockpit für defensive Zusammenarbeit. Der zentrale **Control Plane** ist die Single Source of Truth: Agenten und Operatoren sehen dieselben Vorhaben, Besitzer, Statusänderungen, Übergaben und Signale. Ein Plan wird einmal angelegt und an den gesamten Agent Mesh gebroadcastet — kein verlorener Kontext zwischen Chats oder einzelnen Agenten.

> **Wichtig:** Das Browser-Labor ist ausdrücklich defensiv und simulation-only. Es öffnet keine Ports, antwortet keinem Netzwerk-Client, führt keine Payloads aus und startet keine Gegenangriffe. Ein Honeypot im Cockpit ist ein virtuelles Testobjekt. Produktive Sicherheitsaktionen dürfen ausschließlich auf eigenen oder ausdrücklich autorisierten Systemen stattfinden.

## Was ist neu?

- **Startmenü mit vier Prototypen:** Command Deck, Agent Constellation, Honeypot Lab und Signal Drift.
- **Cyberpunk-/Neo-Tokyo-Interface:** animiertes HUD mit rotem Sun-Core, Scanlines, Signalpartikeln, Agenten-Knoten und responsivem Layout — inspiriert von der Stimmung klassischer Cyberpunk-Anime, ohne fremde Assets zu verwenden.
- **Single Source of Do:** Pläne anlegen, Owner und Priorität setzen, Status durch den Workflow bewegen und jede Änderung im Mesh sichtbar machen.
- **Agent-to-Agent-Handoffs:** Presence, Broadcast-Nachrichten und Kontextübergaben landen gemeinsam im lokalen Audit Trail.
- **Defensives Honeypot-Lab:** virtuelle Decoys konfigurieren, aktivieren/deaktivieren, synthetische Testsignale einspeisen und zugehörige Incidents quittieren.
- **Defense Ops:** ein begrenzter Packet Observatory im Stil einer Wireshark/tshark-Metadatenansicht, Proxychains-Installationscheck und MAC-Rotationsvorschau. Alles ist allowlisted, zeitlich begrenzt und erklärt die Grenze sichtbar.
- **Persistenz ohne Zusatzdienst:** atomare JSON-Schreibvorgänge nach `~/.cyberguardian/control_plane.json`; der Browser spricht ausschließlich mit der lokalen Control Plane.
- **Dependency-free Web-Start:** Das Cockpit läuft mit Python-Standardbibliothek. Die ältere CustomTkinter-/Dear-PyGui-Oberfläche bleibt für lokale Desktop-Workflows erhalten.

## Schnellstart: Browser-Cockpit

```bash
cd CyberGuardian
python3 server.py
# alternativ: python3 launcher.py --browser
```

Danach im Browser öffnen: <http://localhost:4173>

Für die Arena-/Container-Vorschau oder einen Zugriff im lokalen Netz:

```bash
python3 server.py --host 0.0.0.0 --port 4173
```

Der Server akzeptiert den Preview-Host, verwendet relative API-URLs und bindet standardmäßig auf `0.0.0.0`. Mit `Ctrl+C` beenden.

### Control-Plane-API

| Methode | Endpoint | Zweck |
| --- | --- | --- |
| `GET` | `/api/state` | Vollständiger gemeinsamer Kontext |
| `GET` | `/api/health` | Health- und Safety-Status |
| `POST` | `/api/plans` | Defensiven Plan an alle Agenten broadcasten |
| `PATCH` | `/api/plans/<id>` | Status oder Fortschritt aktualisieren |
| `POST` | `/api/agents` | Agent registrieren / online melden |
| `POST` | `/api/messages` | Kontextübergabe an einen Agenten oder den Mesh |
| `POST` | `/api/honeypots` | Virtuellen Decoy erstellen |
| `POST` | `/api/honeypots/<id>/toggle` | Decoy in Simulation aktivieren/pausieren |
| `POST` | `/api/honeypots/<id>/simulate` | Klar markiertes, synthetisches Testsignal erfassen |
| `POST` | `/api/incidents/<id>/ack` | Defensive Beobachtung quittieren |
| `GET` | `/api/ops/overview` | Lokale Tool- und Interface-Fähigkeiten lesen |
| `POST` | `/api/ops/capture` | Bounded Packet-Metadaten-Capture oder sichere Demo |
| `POST` | `/api/ops/proxy-check` | Proxychains-Binary/Config prüfen, keine Route starten |
| `GET` | `/api/ops/mac?interface=<name>` | MAC-Adresse read-only lesen |
| `POST` | `/api/ops/mac-preview` | MAC-Rotation nur als Vorschau erzeugen |

Die API führt keine beliebigen Shell-Befehle aus. Packet Capture ist auf wenige Sekunden und Metadatenzeilen begrenzt; MAC- und Proxychains-Aktionen verändern bzw. routen das System nicht. Der Speicherort kann für Tests überschrieben werden:

```bash
CYBERGUARDIAN_STATE_FILE=/tmp/cyberguardian-state.json python3 server.py
```

## Projektstruktur

```text
CyberGuardian/
├── server.py               # Dependency-free Webserver + JSON-API
├── web/
│   ├── index.html          # Startmenü, Cockpit und Projektbrief
│   ├── styles.css          # Cyberpunk-HUD, Animationen, responsive Layout
│   └── app.js              # Interaktionen, Rendering und API-Client
├── core/
│   ├── control_plane.py    # Single Source of Do / atomare Zustandsablage
│   ├── defense_ops.py      # allowlisted Capture-, Proxy- und MAC-Inspektion
│   └── ...                  # bestehende defensive Sicherheitsmodule
├── main.py                 # bisherige CustomTkinter-Oberfläche
├── main_anime.py           # bisherige Dear-PyGui-Oberfläche
├── launcher.py             # Desktop-Abhängigkeitscheck und Fallback
└── utils/                  # Logging, Backups und Konfiguration
```

## Desktop-Edition (optional)

Die bestehenden Python-Abhängigkeiten werden weiterhin über `requirements.txt` installiert:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 launcher.py
```

`launcher.py` prüft die Desktop-GUIs und wählt die Anime- oder Classic-Edition. Für das neue Browser-Cockpit sind `customtkinter`, Dear PyGui und Systemtools nicht erforderlich.

## Sicherheits- und Ethik-Leitplanken

- Nur eigene oder ausdrücklich freigegebene Systeme beobachten.
- Keine Angriffsautomatisierung, Exploits, Credential-Tests oder Gegenmaßnahmen aus dem Browser-Labor.
- Synthetische Beispielquellen nutzen dokumentations-reservierte IP-Bereiche (`192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24`).
- Logs bleiben lokal und sind als `simulated`/`synthetic` gekennzeichnet.
- Für produktive Sensorik sind Authentifizierung, Rollenrechte, Verschlüsselung, Rotation und ein separat gehärteter Collector erforderlich; das Demo-Cockpit ersetzt keinen produktiven SIEM- oder Honeypot-Dienst.
