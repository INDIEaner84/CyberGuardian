#!/usr/bin/env python3
"""Forensik-Tools"""

import subprocess
import os
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class ForensicsTools:
    """Forensik-Analyse Tools"""
    
    def __init__(self, logger):
        self.logger = logger
        self.report_dir = Path.home() / ".cyberguardian" / "reports"
        self.report_dir.mkdir(parents=True, exist_ok=True)
        
    def collect_system_info(self) -> Dict:
        """Sammle System-Informationen"""
        import platform
        import psutil
        
        return {
            "os": f"{platform.system()} {platform.release()}",
            "hostname": platform.node(),
            "cpu": platform.processor(),
            "cores": psutil.cpu_count(),
            "ram": f"{psutil.virtual_memory().total // (1024**3)} GB",
            "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
        }
        
    def cleanup_temp_files(self):
        """Bereinige temporäre Dateien"""
        import tempfile
        import shutil
        
        cleaned = 0
        temp_dirs = [tempfile.gettempdir(), "/tmp"]
        
        for temp_dir in temp_dirs:
            path = Path(temp_dir)
            if path.exists():
                for item in path.iterdir():
                    try:
                        if item.is_file():
                            item.unlink()
                            cleaned += 1
                    except:
                        pass
                        
        self.logger.log("INFO", f"Bereinigt: {cleaned} temporäre Dateien")
        
    def find_deleted_files(self) -> List[Dict]:
        """Suche nach gelöschten Dateien (vereinfacht)"""
        results = []
        
        try:
            result = subprocess.run(
                ["find", "/home", "-name", "*.tmp", "-o", "-name", "*~", "-o", "-name", ".*.swp"],
                capture_output=True, text=True
            )
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    results.append({"file": line, "type": "recoverable"})
                    
        except Exception as e:
            self.logger.log("ERROR", f"Suche fehlgeschlagen: {e}")
            
        return results
        
    def analyze_malware(self, filepath: str) -> Dict:
        """Analysiere Datei auf Malware (vereinfacht)"""
        result = {
            "file": filepath,
            "suspicious_strings": [],
            "permissions": {},
            "hash": ""
        }
        
        try:
            path = Path(filepath)
            if path.exists():
                stat = path.stat()
                result["permissions"] = {
                    "mode": oct(stat.st_mode)[-3:],
                    "owner_uid": stat.st_uid
                }
                
                import hashlib
                hasher = hashlib.sha256()
                with open(filepath, 'rb') as f:
                    hasher.update(f.read())
                result["hash"] = hasher.hexdigest()
                
        except Exception as e:
            result["error"] = str(e)
            
        return result
        
    def generate_report(self) -> str:
        """Generiere vollständigen Forensik-Report"""
        report = []
        report.append("=" * 60)
        report.append("CyberGuardian Forensik Report")
        report.append(f"Datum: {datetime.now().isoformat()}")
        report.append("=" * 60)
        
        sys_info = self.collect_system_info()
        report.append("\n## System Information")
        for key, value in sys_info.items():
            report.append(f"{key}: {value}")
            
        report.append("\n## Abgeschlossen")
        
        report_path = self.report_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, 'w') as f:
            f.write('\n'.join(report))
            
        self.logger.log("INFO", f"Report erstellt: {report_path}")
        return '\n'.join(report)
