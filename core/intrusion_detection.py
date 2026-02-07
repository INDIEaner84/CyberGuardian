#!/usr/bin/env python3
"""Intrusion Detection System"""

import threading
import time
from collections import defaultdict
import psutil
from datetime import datetime


class IntrusionDetection:
    """Intrusion Detection und Prevention"""
    
    def __init__(self, logger):
        self.logger = logger
        self.running = False
        self.alerts = []
        self.callbacks = []
        self.port_scan_tracker = defaultdict(list)
        self.failed_logins = defaultdict(int)
        
    def get_status(self) -> dict:
        return {"running": self.running, "alerts_count": len(self.alerts)}
        
    def start(self, options: dict = None):
        if self.running:
            return
        self.running = True
        self.logger.log("INFO", "IDS gestartet")
        
    def stop(self):
        self.running = False
        self.logger.log("INFO", "IDS gestoppt")
        
    def add_callback(self, callback):
        self.callbacks.append(callback)
        
    def _create_alert(self, alert_type: str, message: str, severity: str = "MEDIUM"):
        alert = {"timestamp": datetime.now().isoformat(), "type": alert_type, "message": message, "severity": severity}
        self.alerts.append(alert)
        self.logger.log("ALERT", f"{alert_type}: {message}")
        for callback in self.callbacks:
            try:
                callback(alert)
            except:
                pass
                
    def detect_port_scans(self) -> list:
        alerts = []
        for conn in psutil.net_connections(kind='inet'):
            if conn.status == 'SYN_SENT':
                alerts.append({"type": "POSSIBLE_SCAN", "source": conn.raddr.ip if conn.raddr else "unknown"})
        return alerts
