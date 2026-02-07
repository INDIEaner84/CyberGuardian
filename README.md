# CyberGuardian Pro - Ethical Hacking & Security Suite

## ⚠️ Rechtlicher Hinweis

**DIESES TOOL DARF NUR AUF EIGENEN SYSTEMEN VERWENDET WERDEN!**

Die Nutzung auf fremden Systemen ohne ausdrückliche, schriftliche Genehmigung ist **illegal** und kann strafrechtliche Konsequenzen haben.

Mit der Nutzung dieses Tools bestätigen Sie, dass Sie:
1. Die volle Berechtigung haben, alle getesteten Systeme zu analysieren
2. Die Gesetze Ihres Landes bezüglich Cybersicherheit einhalten
3. Für jegliche Missachtung dieser Richtlinien selbst verantwortlich sind

---

## 🚀 Installation (3 Schritte)

### Schritt 1: VENV erstellen
```bash
python3 -m venv venv
```

### Schritt 2: Python-Abhängigkeiten installieren
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Schritt 3: System-Tools installieren
```bash
# Debian/Ubuntu
sudo apt-get install nmap net-tools tor proxychains4 macchanger python3-tk

# Arch Linux
sudo pacman -S nmap net-tools tor proxychains macchanger

# Fedora
sudo dnf install nmap net-tools tor proxychains macchanger
```

### ODER: Alles automatisch
```bash
chmod +x install.sh
./install.sh
```

---

## 🎮 Verwendung

```bash
# VENV aktivieren (vor jedem Start!)
source venv/bin/activate

# Tool starten
python3 main.py

# Oder mit sudo für vollen Funktionsumfang
sudo python3 main.py
```

---

## 📦 Anforderungen

### Python 3.8+
- customtkinter>=5.2.0
- psutil>=5.9.0
- scapy>=2.5.0
- python-nmap>=0.7.1
- netifaces>=0.11.0
- requests>=2.31.0
- mac-vendor-lookup>=2.1.0
- pyudev>=0.24.0

### System-Tools (projektspezifisch)
- nmap (Netzwerk-Scans)
- net-tools (ARP, ifconfig)
- tor (Anonymisierung)
- proxychains4 (Proxy-Kette)
- macchanger (MAC-Spoofing)
- python3-tk (GUI)

---

## 🔧 Hauptfunktionen

| Kategorie | Funktion |
|-----------|----------|
| **Dashboard** | Systemstatus auf einen Blick |
| **Netzwerk** | ARP-Scans, Port-Scans, Deep-Scans |
| **WLAN** | WLAN-Audits, Kanal-Analyse |
| **Prozesse** | Laufende Prozesse überwachen |
| **VPN** | WireGuard Konfiguration |
| **Anonymisierung** | TOR, ProxyChains, MAC-Spoofing |
| **Router** | Router-Konfiguration |
| **IDS/IPS** | Einbruchserkennung |
| **Integrität** | Dateiänderungen erkennen |
| **Forensik** | System-Analyse, Malware-Erkennung |

---

## 📁 Projektstruktur

```
Guardian Indieaner/
├── main.py              # GUI Hauptanwendung
├── install.sh           # Automatische Installation
├── requirements.txt     # Python-Abhängigkeiten
├── README.md           # Diese Datei
├── core/               # Sicherheitsmodule
│   ├── network_scanner.py
│   ├── wifi_auditor.py
│   ├── port_manager.py
│   ├── process_monitor.py
│   ├── wireguard_manager.py
│   ├── anonymizer.py
│   ├── router_tools.py
│   ├── intrusion_detection.py
│   ├── file_integrity.py
│   └── forensics.py
├── utils/              # Hilfsmodule
│   ├── logger.py       # Logging mit Rollback
│   ├── backup_manager.py
│   └── config.py
└── data/               # Daten-Verzeichnis
    ├── backups/
    ├── logs/
    └── proxies/
```

---

## 📋 Standard-Projekt-Vorlage

Bei allen Python-Projekten werden ab jetzt folgende 3 Punkte dokumentiert:

### 1. VENV-Erstellung
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Python-Abhängigkeiten
```bash
pip install -r requirements.txt
```

### 3. System-Tools (projektspezifisch)
```bash
# Beispiel für CyberGuardian
sudo apt-get install nmap tor proxychains macchanger
```

---

## 🔒 Sicherheit

- ✅ Alle Logs werden **lokal** gespeichert (nicht im Internet)
- ✅ Keine Daten werden an Dritte gesendet
- ✅ Firewall-Backups vor Änderungen
- ✅ Rollback-Manager für reversible Aktionen
- ✅ Vollständiges Aktivitäts-Logging

### Log-Speicherort:
```
~/.cyberguardian/logs/
├── cyberguardian.log   # Text-Log
└── actions.json        # Aktionen (JSON)
```

---

## ⚡ Quick Commands

```bash
# Installation
./install.sh

# Starten
source venv/bin/activate && python3 main.py

# Netzwerk scannen
source venv/bin/activate
python3 main.py -> Netzwerk-Scan

# TOR aktivieren
source venv/bin/activate
python3 main.py -> Anonymisierung -> TOR starten
```

---

## 📝 Lizenz

Dieses Projekt ist ausschließlich für **Bildungszwecke** und **legitime Sicherheitsanalysen** gedacht.

---

## ⚠️ Haftungsausschluss

Die Autoren übernehmen keine Haftung für:
- Missbrauch dieses Tools
- Rechtliche Konsequenzen
- Systemschäden
- Datenverlust

**Verwenden Sie dieses Tool verantwortungsvoll!**

---

*CyberGuardian Pro - Ihre Sicherheit ist unsere Priorität*
