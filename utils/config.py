#!/usr/bin/env python3
"""Konfigurations-Modul"""

import json
from pathlib import Path
from typing import Any, Dict


class Config:
    """Konfigurations-Verwaltung"""
    
    def __init__(self):
        self.config_dir = Path.home() / ".cyberguardian"
        self.config_file = self.config_dir / "config.json"
        self._load()
        
    def _load(self):
        """Lade Konfiguration"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = self._default_config()
            self._save()
            
    def _save(self):
        """Speichere Konfiguration"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w') as f:
            json.dump(self.data, f, indent=2)
            
    def _default_config(self) -> Dict:
        """Standard-Konfiguration"""
        return {
            "theme": "dark",
            "auto_start_ids": False,
            "auto_start_integrity": False,
            "notify_sound": True,
            "notify_desktop": True,
            "log_level": "INFO",
            "default_scan_range": "192.168.1.0/24"
        }
        
    def get(self, key: str, default=None) -> Any:
        """Hole Wert"""
        return self.data.get(key, default)
        
    def set(self, key: str, value: Any):
        """Setze Wert"""
        self.data[key] = value
        self._save()
        
    def update(self, updates: Dict):
        """Update mehrere Werte"""
        self.data.update(updates)
        self._save()
