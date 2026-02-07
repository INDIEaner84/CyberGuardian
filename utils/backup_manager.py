#!/usr/bin/env python3
"""Backup & Restore Modul"""

import subprocess
import shutil
import os
import json
from pathlib import Path
from datetime import datetime
import tarfile


class BackupManager:
    """Backup-Verwaltung für System-Wiederherstellung"""
    
    def __init__(self):
        self.backup_dir = Path.home() / ".cyberguardian" / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def backup_firewall(self) -> str:
        """Backup Firewall-Regeln"""
        try:
            if shutil.which("ufw"):
                subprocess.run(["sudo", "ufw", "status", "numbered"], capture_output=True)
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backup_dir / f"firewall_{timestamp}.txt"
            
            if shutil.which("iptables"):
                result = subprocess.run(
                    ["sudo", "iptables-save"],
                    capture_output=True, text=True
                )
                with open(backup_path, 'w') as f:
                    f.write(result.stdout)
                    
            return str(backup_path)
            
        except Exception as e:
            return ""
            
    def backup_file(self, filepath: str) -> str:
        """Backup einzelne Datei"""
        try:
            path = Path(filepath)
            if path.exists():
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = self.backup_dir / f"{path.name}_{timestamp}"
                shutil.copy2(filepath, backup_path)
                return str(backup_path)
        except:
            pass
        return ""
        
    def create_full_backup(self) -> str:
        """Erstelle vollständiges System-Backup"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = self.backup_dir / f"full_backup_{timestamp}.tar.gz"
            
            with tarfile.open(backup_file, "w:gz") as tar:
                home = Path.home()
                tar.add(home / ".cyberguardian", arcname=".cyberguardian")
                
            return str(backup_file)
            
        except Exception as e:
            return ""
            
    def restore_all(self) -> bool:
        """Stelle alle Backups wieder her"""
        try:
            backups = sorted(self.backup_dir.glob("firewall_*.txt"))
            if backups:
                latest = backups[-1]
                if shutil.which("iptables"):
                    with open(latest, 'r') as f:
                        subprocess.run(["sudo", "iptables-restore"], input=f.read())
            return True
        except:
            return False
            
    def list_backups(self) -> list:
        """Liste verfügbare Backups"""
        return [b.name for b in sorted(self.backup_dir.glob("*")) if b.is_file()]
