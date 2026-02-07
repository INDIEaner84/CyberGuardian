#!/usr/bin/env python3
"""Router-Tools Modul"""

import subprocess
import re
from typing import Dict, List
import netifaces


class RouterTools:
    """Router-Analyse Tools"""
    
    def __init__(self, logger):
        self.logger = logger
        
    def get_router_info(self) -> Dict:
        """Hole Router-Informationen"""
        info = {}
        
        try:
            gateway = netifaces.gateways()['default'][netifaces.AF_INET]
            info["Gateway IP"] = gateway[0]
            info["Interface"] = gateway[1]
            
            for iface in netifaces.interfaces():
                addrs = netifaces.ifaddresses(iface)
                if netifaces.AF_INET in addrs:
                    for addr in addrs[netifaces.AF_INET]:
                        if 'addr' in addr:
                            info[f"{iface} IP"] = addr['addr']
                            
        except Exception as e:
            info["Fehler"] = str(e)
            
        return info
        
    def open_router_interface(self):
        """Öffne Router-Webinterface im Browser"""
        try:
            gateway = netifaces.gateways()['default'][netifaces.AF_INET][0]
            import webbrowser
            webbrowser.open(f"http://{gateway}")
        except Exception as e:
            self.logger.log("ERROR", f"Router-Interface öffnen fehlgeschlagen: {e}")
            
    def get_connected_devices(self) -> List[Dict]:
        """Hole verbundene Geräte"""
        devices = []
        try:
            result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 2:
                    devices.append({
                        "ip": parts[0],
                        "mac": parts[1]
                    })
        except:
            pass
        return devices
        
    def add_upnp_mapping(self, external_port: int, internal_port: int, protocol: str = "TCP") -> bool:
        """Füge UPnP Port-Mapping hinzu"""
        try:
            subprocess.run([
                "upnpc", "-a", "192.168.1.100", str(internal_port),
                str(external_port), protocol
            ], check=True)
            self.logger.log("INFO", f"UPnP Mapping: {external_port} -> {internal_port}")
            return True
        except Exception as e:
            self.logger.log("ERROR", f"UPnP Mapping fehlgeschlagen: {e}")
            return False
