#!/usr/bin/env python3
"""Process Monitor Modul"""

import psutil
import subprocess
from typing import List, Dict
import re


class ProcessMonitor:
    """Prozess-Überwachung"""
    
    def __init__(self, logger):
        self.logger = logger
        
    def get_all_processes(self) -> List[Dict]:
        """Hole alle Prozesse"""
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 
                                         'memory_percent', 'status', 'username']):
            try:
                info = proc.info
                connections = self.get_process_connections(info['pid'])
                risk = self.assess_risk(info['name'], connections)
                
                processes.append({
                    'pid': info['pid'],
                    'name': info['name'],
                    'cpu': info['cpu_percent'],
                    'ram': info['memory_percent'],
                    'status': info['status'],
                    'username': info.get('username', ''),
                    'connections': connections,
                    'risk': risk
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
                
        return sorted(processes, key=lambda x: x['cpu'], reverse=True)
        
    def get_process_connections(self, pid: int) -> List[Dict]:
        """Hole Netzwerk-Verbindungen eines Prozesses"""
        connections = []
        try:
            proc = psutil.Process(pid)
            for conn in proc.net_connections(kind='inet'):
                connections.append({
                    'local_ip': conn.laddr.ip,
                    'local_port': conn.laddr.port,
                    'remote_ip': conn.raddr.ip if conn.raddr else '',
                    'remote_port': conn.raddr.port if conn.raddr else '',
                    'status': conn.status
                })
        except:
            pass
        return connections
        
    def assess_risk(self, process_name: str, connections: List[Dict]) -> str:
        """Bewerte Prozess-Risiko"""
        suspicious_names = [
            'nc', 'netcat', 'ncat', 'socat',
            'python.*-c', 'perl.*-e', 'ruby.*-e',
            'msfconsole', 'msfvenom', 'metasploit',
            'aircrack', 'wifite', 'ettercap',
            'john', 'johnny', 'hashcat',
            'nmap', 'zenmap', 'masscan'
        ]
        
        name_lower = process_name.lower()
        
        for sus in suspicious_names:
            if re.search(sus, name_lower):
                return "HIGH"
                
        return "LOW"
        
    def find_suspicious(self) -> List[Dict]:
        """Finde verdächtige Prozesse"""
        suspicious = []
        processes = self.get_all_processes()
        
        for proc in processes:
            if proc['risk'] == "HIGH":
                suspicious.append(proc)
                
        return suspicious
        
    def kill_process(self, pid: int) -> bool:
        """Beende Prozess"""
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            self.logger.log("INFO", f"Prozess {pid} beendet")
            return True
        except Exception as e:
            self.logger.log("ERROR", f"Prozess beenden fehlgeschlagen: {e}")
            return False
            
    def search_processes(self, pattern: str) -> List[Dict]:
        """Suche Prozesse nach Muster"""
        results = []
        pattern_lower = pattern.lower()
        
        for proc in self.get_all_processes():
            if (pattern_lower in proc['name'].lower() or 
                pattern_lower in str(proc['pid'])):
                results.append(proc)
                
        return results
