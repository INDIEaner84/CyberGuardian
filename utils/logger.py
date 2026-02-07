#!/usr/bin/env python3
"""Logging Modul mit Rollback-Unterstützung"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List
import threading


class ActionLogger:
    """Action-Logger für alle Aktionen"""
    
    def __init__(self):
        self.log_dir = Path.home() / ".cyberguardian" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        self.action_log = self.log_dir / "actions.json"
        self.text_log = self.log_dir / "cyberguardian.log"
        
        self.rollback_stack = []
        self.lock = threading.Lock()
        
        self._init_log_file()
        
    def _init_log_file(self):
        """Initialisiere Log-Datei"""
        if not self.text_log.exists():
            self.text_log.touch()
            
    def log(self, level: str, message: str):
        """Logge Nachricht"""
        timestamp = datetime.now().isoformat()
        log_entry = f"[{timestamp}] [{level}] {message}\n"
        
        with self.lock:
            with open(self.text_log, 'a') as f:
                f.write(log_entry)
                
    def log_action(self, action_type: str, details: str, reversible: bool = False, 
                   rollback_data: Dict = None):
        """Logge Aktion"""
        action = {
            "id": self._generate_id(),
            "timestamp": datetime.now().isoformat(),
            "type": action_type,
            "details": details,
            "reversible": reversible,
            "rollback_data": rollback_data
        }
        
        if reversible and rollback_data:
            self.rollback_stack.append(action)
            
        with self.lock:
            actions = self._load_actions()
            actions.append(action)
            self._save_actions(actions)
            
        self.log("INFO", f"Aktion: {action_type} - {details}")
        
    def _generate_id(self) -> str:
        """Generiere eindeutige ID"""
        import hashlib
        import time
        data = f"{time.time()}{id(self)}"
        return hashlib.md5(data.encode()).hexdigest()[:8]
        
    def _load_actions(self) -> List[Dict]:
        """Lade Aktionen aus Datei"""
        if self.action_log.exists():
            with open(self.action_log, 'r') as f:
                return json.load(f)
        return []
        
    def _save_actions(self, actions: List[Dict]):
        """Speichere Aktionen"""
        with open(self.action_log, 'w') as f:
            json.dump(actions, f, indent=2)
            
    def get_recent(self, count: int = 20) -> List[Dict]:
        """Hole letzte Aktionen"""
        actions = self._load_actions()
        return actions[-count:]
        
    def get_rollback_actions(self) -> List[Dict]:
        """Hole alle reversiblen Aktionen"""
        return [a for a in self._load_actions() if a.get('reversible')]
