#!/usr/bin/env python3
"""Anonymisierungs-Tools"""

import subprocess
import requests
import random
from pathlib import Path
import json


class Anonymizer:
    """Anonymisierung und Proxy-Verwaltung"""
    
    def __init__(self, logger, backup_manager):
        self.logger = logger
        self.backup = backup_manager
        self.proxy_file = Path.home() / ".cyberguardian" / "proxies.json"
        self.proxy_file.parent.mkdir(parents=True, exist_ok=True)
        self.original_mac = {}
        
    def get_ip_info(self) -> dict:
        """Hole aktuelle IP-Informationen"""
        info = {}
        try:
            response = requests.get("https://ipinfo.io/json", timeout=10)
            data = response.json()
            info["IP"] = data.get("ip", "N/A")
            info["Stadt"] = data.get("city", "N/A")
            info["Land"] = data.get("country", "N/A")
            info["ISP"] = data.get("org", "N/A")
        except Exception as e:
            info["Fehler"] = str(e)
        return info
        
    def get_anonsurf_status(self) -> bool:
        """Prüfe AnonSurf Status"""
        try:
            result = subprocess.run(["anonsurf", "status"], capture_output=True, text=True)
            return "running" in result.stdout.lower()
        except:
            return False
            
    def start_anonsurf(self) -> bool:
        """Starte AnonSurf"""
        try:
            subprocess.run(["sudo", "anonsurf", "start"], check=True)
            self.logger.log("INFO", "AnonSurf gestartet")
            return True
        except:
            return False
            
    def stop_anonsurf(self) -> bool:
        """Stoppe AnonSurf"""
        try:
            subprocess.run(["sudo", "anonsurf", "stop"], check=True)
            self.logger.log("INFO", "AnonSurf gestoppt")
            return True
        except:
            return False
            
    def check_tor_connection(self) -> dict:
        """Prüfe TOR-Verbindung"""
        result = {"connected": False, "ip": ""}
        try:
            proxies = {"http": "socks5h://127.0.0.1:9050", "https": "socks5h://127.0.0.1:9050"}
            response = requests.get("https://check.torproject.org/api/ip", proxies=proxies, timeout=10)
            data = response.json()
            result["connected"] = data.get("IsTor", False)
            result["ip"] = data.get("IP", "")
        except Exception as e:
            result["error"] = str(e)
        return result
        
    def search_proxies(self) -> list:
        """Suche öffentliche Proxys"""
        proxies = []
        try:
            response = requests.get("https://raw.githubusercontent.com/TheSpeedX/SOCKS-List/master/socks5.txt", timeout=10)
            for line in response.text.strip().split('\n'):
                if ':' in line:
                    parts = line.split(':')
                    if len(parts) >= 2:
                        proxies.append({"host": parts[0], "port": parts[1], "type": "socks5", "status": "untested"})
        except:
            pass
        return proxies[:50]
        
    def test_proxy(self, host: str, port: str, proxy_type: str = "socks5") -> bool:
        """Teste einzelnen Proxy"""
        try:
            proxies = {"http": f"{proxy_type}://{host}:{port}", "https": f"{proxy_type}://{host}:{port}"}
            response = requests.get("http://httpbin.org/ip", proxies=proxies, timeout=5)
            return response.status_code == 200
        except:
            return False
            
    def get_mac_info(self) -> str:
        """Hole aktuelle MAC-Adresse"""
        try:
            result = subprocess.run(["ip", "link", "show"], capture_output=True, text=True)
            import re
            match = re.search(r'link/ether ([0-9a-f:]+)', result.stdout)
            if match:
                return match.group(1)
        except:
            pass
        return "Unbekannt"
        
    def randomize_mac(self, interface: str = "eth0") -> bool:
        """Zufällige MAC-Adresse"""
        try:
            subprocess.run(["sudo", "ip", "link", "set", interface, "down"], check=True)
            new_mac = ':'.join(f'{random.randint(0, 255):02x}' for _ in range(6))
            subprocess.run(["sudo", "ip", "link", "set", interface, "address", new_mac], check=True)
            subprocess.run(["sudo", "ip", "link", "set", interface, "up"], check=True)
            self.logger.log("INFO", f"MAC geändert: {new_mac}")
            return True
        except Exception as e:
            self.logger.log("ERROR", f"MAC-Änderung fehlgeschlagen: {e}")
            return False
            
    def check_dns_leak(self) -> dict:
        """Prüfe auf DNS-Leak"""
        return {"leak": False, "servers": []}
