#!/usr/bin/env python3
"""Netzwerk-Scanner Modul"""

import socket
import subprocess
import threading
from typing import List, Dict, Optional
import netifaces
import nmap
from scapy.all import ARP, Ether, srp
import requests


class NetworkScanner:
    """Netzwerk-Scanner für lokales Netzwerk"""
    
    def __init__(self, logger):
        self.logger = logger
        
    def get_network_range(self) -> str:
        """Ermittle Netzwerk-Range"""
        try:
            gw = netifaces.gateways()['default'][netifaces.AF_INET]
            gateway_ip = gw[0]
            parts = gateway_ip.split('.')
            return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
        except:
            return "192.168.1.0/24"
            
    def scan_network(self, network_range: str = None) -> List[Dict]:
        """Scanne Netzwerk nach Geräten"""
        if not network_range:
            network_range = self.get_network_range()
            
        self.logger.log("INFO", f"Scanne Netzwerk: {network_range}")
        devices = []
        
        try:
            arp = ARP(pdst=network_range)
            ether = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = ether/arp
            
            result = srp(packet, timeout=3, verbose=0)[0]
            
            for sent, received in result:
                device = {
                    "ip": received.psrc,
                    "mac": received.hwsrc,
                    "hostname": self.get_hostname(received.psrc),
                    "vendor": self.get_vendor(received.hwsrc),
                    "ports": "",
                    "os": ""
                }
                devices.append(device)
                
        except Exception as e:
            self.logger.log("ERROR", f"Scan-Fehler: {e}")
            
        return devices
        
    def deep_scan(self, ip: str) -> Dict:
        """Tiefenscan eines Geräts"""
        result = {
            "ip": ip,
            "ports": [],
            "os": "",
            "services": []
        }
        
        try:
            nm = nmap.PortScanner()
            nm.scan(ip, arguments="-sV -O -T4")
            
            if ip in nm.all_hosts():
                host = nm[ip]
                
                if 'osmatch' in host and host['osmatch']:
                    result['os'] = host['osmatch'][0].get('name', 'Unknown')
                    
                for proto in host.all_protocols():
                    for port in host[proto].keys():
                        port_info = host[proto][port]
                        result['ports'].append({
                            'port': port,
                            'state': port_info['state'],
                            'service': port_info.get('name', ''),
                            'version': port_info.get('version', '')
                        })
                        
        except Exception as e:
            self.logger.log("ERROR", f"Deep Scan Fehler: {e}")
            
        return result
        
    def get_hostname(self, ip: str) -> str:
        """Hole Hostname für IP"""
        try:
            return socket.gethostbyaddr(ip)[0]
        except:
            return ""
            
    def get_vendor(self, mac: str) -> str:
        """Hole Hersteller für MAC - vereinfachte Version"""
        return "Unknown"
            
    def get_arp_table(self) -> List[Dict]:
        """Hole ARP-Tabelle"""
        entries = []
        try:
            result = subprocess.run(["arp", "-a"], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')
            
            for line in lines:
                parts = line.split()
                if len(parts) >= 3:
                    entries.append({
                        "ip": parts[0],
                        "mac": parts[1] if len(parts) > 1 else "",
                        "interface": parts[-1] if len(parts) > 2 else ""
                    })
        except:
            pass
            
        return entries
