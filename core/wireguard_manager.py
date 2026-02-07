#!/usr/bin/env python3
"""WireGuard VPN Manager"""

import subprocess
import os
from pathlib import Path


class WireGuardManager:
    def __init__(self, logger, backup_manager):
        self.logger = logger
        self.backup = backup_manager
        self.keys_dir = Path.home() / ".cyberguardian" / "wireguard"
        self.keys_dir.mkdir(parents=True, exist_ok=True)
        
    def get_status(self) -> dict:
        result = {"connected": False, "details": {}}
        try:
            output = subprocess.run(["sudo", "wg", "show"], capture_output=True, text=True, timeout=10)
            if output.returncode == 0 and output.stdout.strip():
                result["connected"] = True
        except:
            pass
        return result
        
    def generate_keys(self) -> dict:
        try:
            private = subprocess.run(["wg", "genkey"], capture_output=True, text=True)
            public = subprocess.run(["wg", "pubkey"], input=private.stdout.strip(), capture_output=True, text=True)
            return {"private": private.stdout.strip(), "public": public.stdout.strip()}
        except:
            return {}
            
    def create_server_config(self, interface: str = "wg0", port: int = 51820) -> str:
        keys = self.generate_keys()
        if not keys:
            return ""
        return f"""[Interface]
Address = 10.0.0.1/24
ListenPort = {port}
PrivateKey = {keys['private']}
"""
        
    def start_server(self, interface: str = "wg0") -> bool:
        try:
            subprocess.run(["sudo", "wg-quick", "up", interface], check=True)
            return True
        except:
            return False
            
    def stop_server(self, interface: str = "wg0") -> bool:
        try:
            subprocess.run(["sudo", "wg-quick", "down", interface], check=True)
            return True
        except:
            return False
