#!/usr/bin/env python3
"""Port-Manager Modul"""

import subprocess
import socket
import psutil
from typing import List, Dict, Tuple
import platform
import nmap


class PortManager:
    """Port-Verwaltung und Scanning"""
    
    def __init__(self, logger, backup_manager):
        self.logger = logger
        self.backup = backup_manager
        self.os_type = platform.system()
        
    def get_open_ports(self) -> List[Dict]:
        """Hole alle offenen Ports auf diesem System"""
        ports = []
        
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'LISTEN':
                try:
                    proc = psutil.Process(conn.pid) if conn.pid else None
                    ports.append({
                        "port": conn.laddr.port,
                        "protocol": "TCP",
                        "status": conn.status,
                        "pid": conn.pid or "",
                        "process": proc.name() if proc else "",
                        "address": conn.laddr.ip
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    ports.append({
                        "port": conn.laddr.port,
                        "protocol": "TCP",
                        "status": conn.status,
                        "pid": conn.pid or "",
                        "process": "N/A",
                        "address": conn.laddr.ip
                    })
                    
        return sorted(ports, key=lambda x: x['port'])
        
    def scan_ports(self, target: str, port_range: str = "1-1024") -> List[Dict]:
        """Scanne Ports eines Ziels"""
        self.logger.log("INFO", f"Port-Scan: {target} ({port_range})")
        results = []
        
        try:
            nm = nmap.PortScanner()
            nm.scan(target, port_range, arguments="-sV -T4")
            
            if target in nm.all_hosts():
                for proto in nm[target].all_protocols():
                    for port in nm[target][proto].keys():
                        port_info = nm[target][proto][port]
                        results.append({
                            "port": port,
                            "protocol": proto.upper(),
                            "state": port_info['state'],
                            "service": port_info.get('name', ''),
                            "version": port_info.get('version', '')
                        })
        except Exception as e:
            self.logger.log("ERROR", f"Port-Scan Fehler: {e}")
            
        return results
        
    def quick_scan(self, target: str = "127.0.0.1") -> List[Dict]:
        """Schneller Scan der wichtigsten Ports"""
        common_ports = "21,22,23,25,53,80,110,143,443,445,993,995,3306,3389,5432,8080,8443"
        return self.scan_ports(target, common_ports)
        
    def open_port(self, port: int, protocol: str = "TCP") -> bool:
        """Öffne Port in Firewall"""
        self.backup.backup_firewall()
        self.logger.log("INFO", f"Öffne Port {port}/{protocol}")
        
        try:
            if self.os_type == "Linux":
                subprocess.run(
                    ["sudo", "ufw", "allow", f"{port}/{protocol.lower()}"],
                    check=True
                )
            elif self.os_type == "Windows":
                subprocess.run([
                    "netsh", "advfirewall", "firewall", "add", "rule",
                    f"name=CyberGuardian_Port_{port}",
                    "dir=in", "action=allow",
                    f"protocol={protocol}",
                    f"localport={port}"
                ], check=True)
                
            self.logger.log_action("OPEN_PORT", f"{port}/{protocol}", reversible=True)
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.log("ERROR", f"Port öffnen fehlgeschlagen: {e}")
            return False
            
    def close_port(self, port: int, protocol: str = "TCP") -> bool:
        """Schließe Port in Firewall"""
        self.backup.backup_firewall()
        self.logger.log("INFO", f"Schließe Port {port}/{protocol}")
        
        try:
            if self.os_type == "Linux":
                subprocess.run(
                    ["sudo", "ufw", "deny", f"{port}/{protocol.lower()}"],
                    check=True
                )
            elif self.os_type == "Windows":
                subprocess.run([
                    "netsh", "advfirewall", "firewall", "delete", "rule",
                    f"name=CyberGuardian_Port_{port}"
                ], check=True)
                
            self.logger.log_action("CLOSE_PORT", f"{port}/{protocol}", reversible=True)
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.log("ERROR", f"Port schließen fehlgeschlagen: {e}")
            return False
