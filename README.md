# CyberGuardian Pro - Ethical Hacking & Security Suite

## ⚠️ Rechtlicher Hinweis

**DIESES TOOL DARF NUR AUF EIGENEN SYSTEMEN VERWENDET WERDEN!**

Die Nutzung auf fremden Systemen ohne ausdrückliche, schriftliche Genehmigung ist **illegal** und kann strafrechtliche Konsequenzen haben.

---

## 🚀 Installation (geklontes Repository)

```bash
# 1. Klonen
git clone https://github.com/INDIEaner84/CyberGuardian.git
cd CyberGuardian

# 2. Installations-Script ausführen (erstellt VENV + installiert alles)
./install.sh

# 3. VENV aktivieren (VOR JEDEM START!)
source venv/bin/activate

# 4. Tool starten
python3 main.py
```

**Oder manuell:**
```bash
git clone https://github.com/INDIEaner84/CyberGuardian.git
cd CyberGuardian

# VENV erstellen
python3 -m venv venv

# VENV aktivieren
source venv/bin/activate

# Python-Pakete installieren
pip install -r requirements.txt

# System-Tools installieren
sudo apt-get install nmap net-tools tor proxychains4 macchanger python3-tk

# Starten
python3 main.py
```

---

## 🔧 Für Entwicklung

```bash
# Nachdem du Änderungen gemacht hast:
git add .
git commit -m "Deine Nachricht"
git push
```

---

## 📁 Projektstruktur

```
CyberGuardian/
├── main.py              # GUI Hauptanwendung
├── install.sh           # Automatische Installation
├── requirements.txt     # Python-Abhängigkeiten
├── README.md           # Diese Datei
├── core/               # 10 Sicherheitsmodule
├── utils/              # Hilfsmodule
└── venv/               # Virtuelle Umgebung (nach Installation)
```

---

## 🔒 Sicherheit

- ✅ Logs werden **lokal** gespeichert (nicht im Internet)
- ✅ Keine Daten werden an Dritte gesendet
- ✅ Alle Aktionen werden protokolliert

Log-Speicherort: `~/.cyberguardian/logs/`

---

**WICHTIG: Vor jedem Start `source venv/bin/activate` ausführen!**
