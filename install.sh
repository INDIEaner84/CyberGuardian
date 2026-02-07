#!/bin/bash
"""CyberGuardian Pro - Automatisches Installations-Script"""

set -e

echo "=================================="
echo "CyberGuardian Pro - Installation"
echo "=================================="

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# VENV-Prüfung
VENV_DIR="venv"

echo ""
echo "[1/6] Virtuelle Umgebung (VENV) wird erstellt..."

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    echo -e "${GREEN}VENV erstellt: $VENV_DIR${NC}"
else
    echo -e "${YELLOW}VENV existiert bereits${NC}"
fi

# VENV aktivieren
echo ""
echo "[2/6] Aktiviere virtuelle Umgebung..."
source "$VENV_DIR/bin/activate"

#pip upgrade
echo ""
echo "[3/6] Installiere Python-Abhaengigkeiten..."
pip install --quiet --upgrade pip 2>/dev/null || true

# Installiere alle Pakete aus requirements.txt
if [ -f "requirements.txt" ]; then
    pip install --quiet -r requirements.txt
    echo -e "${GREEN}Python-Pakete installiert${NC}"
else:
    # Fallback: Einzelne Installation
    pip install --quiet customtkinter>=5.2.0
    pip install --quiet psutil>=5.9.0
    pip install --quiet scapy>=2.5.0
    pip install --quiet python-nmap>=0.7.1
    pip install --quiet netifaces>=0.11.0
    pip install --quiet requests>=2.31.0
    pip install --quiet mac-vendor-lookup>=2.1.0
    pip install --quiet pyudev>=0.24.0
fi

echo ""
echo "[4/6] Installiere System-Tools..."

# Debian/Ubuntu
if command -v apt-get &> /dev/null; then
    sudo apt-get update -qq 2>/dev/null || true
    sudo apt-get install -y -qq \
        nmap \
        net-tools \
        iproute2 \
        tor \
        proxychains4 \
        macchanger \
        python3-tk \
        2>/dev/null || true
    echo -e "${GREEN}System-Tools (apt) installiert${NC}"

# Arch
elif command -v pacman &> /dev/null; then
    sudo pacman -Sy --noconfirm \
        nmap \
        net-tools \
        tor \
        proxychains \
        macchanger \
        2>/dev/null || true
    echo -e "${GREEN}System-Tools (pacman) installiert${NC}"

# Fedora
elif command -v dnf &> /dev/null; then
    sudo dnf install -y \
        nmap \
        net-tools \
        tor \
        proxychains \
        macchanger \
        2>/dev/null || true
    echo -e "${GREEN}System-Tools (dnf) installiert${NC}"

else
    echo -e "${YELLOW}Kein bekannter Paketmanager gefunden${NC}"
fi

echo ""
echo "[5/6] Erstelle Verzeichnisstruktur..."
mkdir -p ~/.cyberguardian/{logs,backups,reports,wireguard}
mkdir -p core utils data/{backups,logs,proxies}
echo -e "${GREEN}Verzeichnisse erstellt${NC}"

echo ""
echo "[6/6] Pruefe Installation..."

# Pruefe Python-Pakete
python3 -c "import customtkinter; print('CustomTkinter: OK')" || echo -e "${RED}CustomTkinter: FEHLER${NC}"
python3 -c "import psutil; print('psutil: OK')" || echo -e "${RED}psutil: FEHLER${NC}"
python3 -c "import scapy; print('scapy: OK')" || echo -e "${RED}scapy: FEHLER${NC}"

# Pruefe System-Tools
command -v nmap &> /dev/null && echo "nmap: OK" || echo -e "${YELLOW}nmap: nicht gefunden${NC}"
command -v tor &> /dev/null && echo "tor: OK" || echo -e "${YELLOW}tor: nicht gefunden${NC}"
command -v proxychains4 &> /dev/null && echo "proxychains4: OK" || echo -e "${YELLOW}proxychains4: nicht gefunden${NC}"
command -v macchanger &> /dev/null && echo "macchanger: OK" || echo -e "${YELLOW}macchanger: nicht gefunden${NC}"

echo ""
echo "=================================="
echo -e "${GREEN}Installation abgeschlossen!${NC}"
echo "=================================="
echo ""
echo "=================================="
echo "STARTEN DES TOOLS:"
echo "=================================="
echo ""
echo "1. VENV aktivieren:"
echo "   source venv/bin/activate"
echo ""
echo "2. Tool starten:"
echo "   python3 main.py"
echo ""
echo "ODER alles auf einmal:"
echo "   source venv/bin/activate && python3 main.py"
echo ""
echo -e "${YELLOW}WICHTIG: Nur auf eigenen Systemen verwenden!${NC}"
echo ""
