#!/usr/bin/env python3
"""WLAN-Sicherheits-Audit Modul"""

import subprocess
import re
import platform
from typing import Dict, List, Optional


class WifiAuditor:
    """WLAN-Sicherheits-Audit Tools"""
    
    def __init__(self, logger):
        self.logger = logger
        self.os_type = platform.system()
        
    def get_current_connection(self) -> Dict:
        """Hole aktuelle WLAN-Verbindung"""
        info = {}
        
        if self.os_type == "Linux":
            try:
                result = subprocess.run(["iwconfig"], capture_output=True, text=True)
                output = result.stdout
                
                ssid_match = re.search(r'ESSID:"([^"]+)"', output)
                info["SSID"] = ssid_match.group(1) if ssid_match else "Nicht verbunden"
                
                signal_match = re.search(r'Signal level=(-?\d+)', output)
                info["Signal"] = f"{signal_match.group(1)} dBm" if signal_match else "N/A"
                
            except Exception as e:
                info["Fehler"] = str(e)
                
        elif self.os_type == "Windows":
            try:
                result = subprocess.run(
                    ["netsh", "wlan", "show", "interfaces"],
                    capture_output=True, text=True
                )
                for line in result.stdout.split('\n'):
                    if 'SSID' in line and 'BSSID' not in line:
                        info["SSID"] = line.split(':')[1].strip()
                    elif 'Signal' in line:
                        info["Signal"] = line.split(':')[1].strip()
            except Exception as e:
                info["Fehler"] = str(e)
                
        return info
        
    def scan_networks(self) -> List[Dict]:
        """Scanne verfügbare WLAN-Netzwerke"""
        networks = []
        
        if self.os_type == "Linux":
            try:
                result = subprocess.run(
                    ["nmcli", "-t", "-f", "SSID,BSSID,CHAN,SIGNAL,SECURITY", "dev", "wifi"],
                    capture_output=True, text=True
                )
                
                for line in result.stdout.strip().split('\n'):
                    if line:
                        parts = line.split(':')
                        if len(parts) >= 5:
                            networks.append({
                                "ssid": parts[0],
                                "bssid": parts[1],
                                "channel": parts[2],
                                "signal": parts[3],
                                "security": parts[4]
                            })
            except:
                pass
                
        return networks
        
    def get_saved_passwords(self) -> List[Dict]:
        """Hole gespeicherte WLAN-Passwörter (nur eigene!)"""
        passwords = []
        
        if self.os_type == "Linux":
            try:
                result = subprocess.run(
                    ["sudo", "grep", "-r", "psk=", "/etc/NetworkManager/system-connections/"],
                    capture_output=True, text=True, timeout=10
                )
                
                for line in result.stdout.strip().split('\n'):
                    if 'psk=' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            filename = parts[0].split('/')[-1]
                            psk = parts[1].replace('psk=', '').strip()
                            passwords.append({
                                "profile": filename,
                                "password": psk
                            })
            except:
                pass
                
        return passwords
        
    def check_security(self, ssid: str) -> Dict:
        """Prüfe Sicherheit eines Netzwerks"""
        result = {
            "ssid": ssid,
            "vulnerabilities": [],
            "recommendations": [],
            "score": 100
        }
        
        networks = self.scan_networks()
        target = None
        
        for net in networks:
            if net.get("ssid") == ssid:
                target = net
                break
                
        if not target:
            result["error"] = "Netzwerk nicht gefunden"
            return result
            
        security = target.get("security", "").upper()
        
        if "WEP" in security:
            result["vulnerabilities"].append("WEP-Verschlüsselung ist unsicher!")
            result["recommendations"].append("Upgrade auf WPA2/WPA3")
            result["score"] -= 50
            
        if "OPEN" in security or not security:
            result["vulnerabilities"].append("Netzwerk ist unverschlüsselt!")
            result["recommendations"].append("Verschlüsselung aktivieren")
            result["score"] -= 70
            
        if result["score"] < 0:
            result["score"] = 0
            
        return result
        
    def analyze_channels(self) -> Dict:
        """Analysiere WLAN-Kanäle"""
        channels = {i: [] for i in range(1, 15)}
        
        networks = self.scan_networks()
        for net in networks:
            try:
                ch = int(net.get("channel", 0))
                if 1 <= ch <= 14:
                    channels[ch].append(net.get("ssid", ""))
            except:
                pass
                
        best_channel = min(channels, key=lambda x: len(channels[x]))
        
        return {
            "channels": channels,
            "recommendation": f"Empfohlener Kanal: {best_channel}",
            "congested": [ch for ch, nets in channels.items() if len(nets) > 3]
        }
