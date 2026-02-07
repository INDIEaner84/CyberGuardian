#!/usr/bin/env python3
"""Datei-Integritäts-Monitor"""

import hashlib
import os
from pathlib import Path
from typing import Dict, List
from datetime import datetime


class FileIntegrityMonitor:
    """Datei-Integritäts-Überwachung"""
    
    def __init__(self, logger):
        self.logger = logger
        self.baseline_file = Path.home() / ".cyberguardian" / "baseline.json"
        self.watch_dirs = []
        self.changes = []
        
    def calculate_hash(self, filepath: Path) -> str:
        """Berechne Hash einer Datei"""
        try:
            hasher = hashlib.sha256()
            with open(filepath, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except:
            return ""
            
    def create_baseline(self, directories: List[str] = None) -> Dict:
        """Erstelle Baseline für Verzeichnisse"""
        baseline = {"created": datetime.now().isoformat(), "files": {}}
        
        dirs = directories or ["/etc", str(Path.home())]
        
        for directory in dirs:
            path = Path(directory)
            if path.exists():
                for root, dirs, files in os.walk(path):
                    for file in files:
                        filepath = Path(root) / file
                        try:
                            stat = filepath.stat()
                            baseline["files"][str(filepath)] = {
                                "hash": self.calculate_hash(filepath),
                                "size": stat.st_size,
                                "mtime": stat.st_mtime
                            }
                        except:
                            pass
                            
        with open(self.baseline_file, 'w') as f:
            import json
            json.dump(baseline, f, indent=2)
            
        self.logger.log("INFO", f"Baseline erstellt: {len(baseline['files'])} Dateien")
        return baseline
        
    def compare_baseline(self) -> List[Dict]:
        """Vergleiche aktuelle Dateien mit Baseline"""
        changes = []
        
        try:
            with open(self.baseline_file, 'r') as f:
                import json
                baseline = json.load(f)
                
            for filepath, info in baseline["files"].items():
                path = Path(filepath)
                if not path.exists():
                    changes.append({"type": "DELETED", "file": filepath})
                else:
                    current_hash = self.calculate_hash(path)
                    if current_hash != info["hash"]:
                        changes.append({"type": "MODIFIED", "file": filepath})
                        
        except Exception as e:
            self.logger.log("ERROR", f"Baseline-Vergleich fehlgeschlagen: {e}")
            
        return changes
