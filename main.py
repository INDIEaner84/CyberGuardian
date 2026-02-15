#!/usr/bin/env python3
"""CyberGuardian Pro - Main Application"""

import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import json
import os
import sys
import time
import socket
import psutil
import platform
from datetime import datetime
from pathlib import Path
import queue
import netifaces

# Retro Terminal / Akira / IBM Green Theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

# Custom Colors - Retro Terminal Green
COLORS = {
    "bg_dark": "#0a0a0a",
    "bg_medium": "#0d1b0d",
    "bg_light": "#132413",
    "fg_main": "#00ff41",
    "fg_dim": "#00aa2a",
    "fg_bright": "#33ff66",
    "accent": "#00ff41",
    "warning": "#ffaa00",
    "error": "#ff3333",
    "border": "#00aa2a",
}

# Custom Font
FONT_TERM = ("Courier", 12)
FONT_BOLD = ("Courier", 14, "bold")
FONT_HEADER = ("Courier", 18, "bold")
FONT_LARGE = ("Courier", 24, "bold")

try:
    from core.network_scanner import NetworkScanner
    from core.wifi_auditor import WifiAuditor
    from core.port_manager import PortManager
    from core.process_monitor import ProcessMonitor
    from core.wireguard_manager import WireGuardManager
    from core.anonymizer import Anonymizer
    from core.router_tools import RouterTools
    from core.intrusion_detection import IntrusionDetection
    from core.file_integrity import FileIntegrityMonitor
    from core.forensics import ForensicsTools
    from utils.logger import ActionLogger
    from utils.backup_manager import BackupManager
    from utils.config import Config

    MODULES_AVAILABLE = True
except ImportError as e:
    MODULES_AVAILABLE = False
    print(f"Module nicht verfuegbar: {e}")


class CyberGuardianApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CyberGuardian Pro - Security Suite")
        self.geometry("1400x900")
        self.minsize(1200, 800)

        self.output_queue = queue.Queue()

        if MODULES_AVAILABLE:
            self.config = Config()
            self.logger = ActionLogger()
            self.backup_manager = BackupManager()
            self.init_modules()

        self.create_ui()
        self.start_background_tasks()
        self.show_legal_notice()

    def init_modules(self):
        self.network_scanner = NetworkScanner(self.logger)
        self.wifi_auditor = WifiAuditor(self.logger)
        self.port_manager = PortManager(self.logger, self.backup_manager)
        self.process_monitor = ProcessMonitor(self.logger)
        self.wireguard = WireGuardManager(self.logger, self.backup_manager)
        self.anonymizer = Anonymizer(self.logger, self.backup_manager)
        self.router_tools = RouterTools(self.logger)
        self.ids = IntrusionDetection(self.logger)
        self.file_integrity = FileIntegrityMonitor(self.logger)
        self.forensics = ForensicsTools(self.logger)

    def create_ui(self):
        self.main_container = ctk.CTkFrame(self)
        self.main_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.create_header()
        self.content_frame = ctk.CTkFrame(self.main_container)
        self.content_frame.pack(fill="both", expand=True, pady=(10, 0))

        self.create_sidebar()
        self.create_main_area()
        self.create_statusbar()

    def create_header(self):
        header = ctk.CTkFrame(
            self.main_container,
            height=80,
            fg_color=COLORS["bg_medium"],
            border_color=COLORS["border"],
            border_width=2,
        )
        header.pack(fill="x", pady=(0, 10))
        header.pack_propagate(False)

        # ASCII Art Header
        header_text = "▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓\n  █ CYBERGUARDIAN PRO v2.0 █\n▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓"

        ctk.CTkLabel(
            header,
            text=header_text,
            font=("Courier", 10),
            text_color=COLORS["fg_main"],
            fg_color=COLORS["bg_dark"],
        ).pack(side="left", padx=20, pady=10)

        quick_frame = ctk.CTkFrame(header, fg_color="transparent")
        quick_frame.pack(side="right", padx=20)

        ctk.CTkButton(
            quick_frame,
            text="[ PANIC ]",
            fg_color=COLORS["error"],
            text_color=COLORS["bg_dark"],
            font=FONT_BOLD,
            width=120,
            border_width=2,
            border_color=COLORS["error"],
            command=self.panic_stop,
        ).pack(side="right", padx=5)

    def create_sidebar(self):
        self.sidebar = ctk.CTkFrame(
            self.content_frame,
            width=250,
            fg_color=COLORS["bg_dark"],
            border_color=COLORS["border"],
            border_width=2,
        )
        self.sidebar.pack(side="left", fill="y", padx=(0, 10))
        self.sidebar.pack_propagate(False)

        # Sidebar Header
        ctk.CTkLabel(
            self.sidebar,
            text="[ MENU ]",
            font=FONT_BOLD,
            text_color=COLORS["fg_main"],
            fg_color=COLORS["bg_medium"],
        ).pack(pady=(15, 10), fill="x")

        nav_items = [
            ("[D] Dashboard", self.show_dashboard),
            ("[N] Netzwerk-Scan", self.show_network),
            ("[W] WLAN-Audit", self.show_wifi),
            ("[P] Port-Manager", self.show_ports),
            ("[S] Prozesse", self.show_processes),
            ("[V] WireGuard VPN", self.show_wireguard),
            ("[A] Anonymisierung", self.show_anonymizer),
            ("[R] Router-Tools", self.show_router),
            ("[I] IDS/IPS", self.show_ids),
            ("[F] Datei-Integritaet", self.show_integrity),
            ("[X] Forensik", self.show_forensics),
            ("[B] Rollback", self.show_rollback),
            ("[L] Logs", self.show_logs),
            ("[C] Einstellungen", self.show_settings),
        ]

        self.nav_buttons = {}
        for text, command in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                anchor="w",
                command=command,
                fg_color=COLORS["bg_medium"],
                text_color=COLORS["fg_dim"],
                hover_color=COLORS["bg_light"],
                border_width=1,
                border_color=COLORS["border"],
                font=FONT_TERM,
                height=35,
            )
            btn.pack(fill="x", padx=10, pady=3)
            self.nav_buttons[text] = btn

        info_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color=COLORS["bg_medium"],
            border_color=COLORS["border"],
            border_width=1,
        )
        info_frame.pack(side="bottom", fill="x", padx=10, pady=10)

        ctk.CTkLabel(
            info_frame,
            text="[ SYSTEM ]",
            font=FONT_TERM,
            text_color=COLORS["fg_main"],
        ).pack(pady=5)
        ctk.CTkLabel(
            info_frame,
            text=self.get_system_info(),
            justify="left",
            font=("Courier", 9),
            text_color=COLORS["fg_dim"],
        ).pack(pady=5)

    def create_main_area(self):
        self.main_area = ctk.CTkFrame(
            self.content_frame,
            fg_color=COLORS["bg_dark"],
            border_color=COLORS["border"],
            border_width=2,
        )
        self.main_area.pack(side="right", fill="both", expand=True)
        self.show_dashboard()

    def create_statusbar(self):
        self.statusbar = ctk.CTkFrame(
            self.main_container,
            height=30,
            fg_color=COLORS["bg_medium"],
            border_color=COLORS["border"],
            border_width=1,
        )
        self.statusbar.pack(fill="x", pady=(10, 0))

        self.status_label = ctk.CTkLabel(
            self.statusbar,
            text="> SYSTEM BEREIT",
            anchor="w",
            font=FONT_TERM,
            text_color=COLORS["fg_main"],
            fg_color=COLORS["bg_medium"],
        )
        self.status_label.pack(side="left", padx=10)

        self.time_label = ctk.CTkLabel(
            self.statusbar,
            text=datetime.now().strftime("%H:%M:%S"),
            font=FONT_TERM,
            text_color=COLORS["fg_dim"],
        )
        self.time_label.pack(side="right", padx=10)
        self.update_time()

    def clear_main_area(self):
        for widget in self.main_area.winfo_children():
            widget.destroy()

    def get_system_info(self):
        return f"OS: {platform.system()}\nHost: {socket.gethostname()}\nCPU: {psutil.cpu_count()} cores"

    def update_time(self):
        self.time_label.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.after(1000, self.update_time)

    def show_legal_notice(self):
        messagebox.showinfo(
            "Rechtlicher Hinweis",
            "CyberGuardian Pro\n\nNur fuer eigene Systeme verwenden!\nNutzung auf fremden Systemen ist ILLEGAL.",
        )

    def start_background_tasks(self):
        self.process_output_queue()

    def process_output_queue(self):
        try:
            while True:
                msg = self.output_queue.get_nowait()
                self.status_label.configure(text=msg)
        except queue.Empty:
            pass
        self.after(100, self.process_output_queue)

    def panic_stop(self):
        if messagebox.askyesno("PANIC", "Alle Operationen stoppen?"):
            self.status_label.configure(text="PANIC: Gestoppt")

    def show_dashboard(self):
        self.clear_main_area()
        self.highlight_nav("Dashboard")
        dashboard = ctk.CTkScrollableFrame(self.main_area)
        dashboard.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            dashboard,
            text="Security Dashboard",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack(pady=10)

        # Rahmen für Karten erstellen
        cards_frame = ctk.CTkFrame(dashboard)
        cards_frame.pack(fill="x", pady=10)

        cards = [
            ("CPU", f"{psutil.cpu_percent()}%"),
            ("RAM", f"{psutil.virtual_memory().percent}%"),
            ("Disk", f"{psutil.disk_usage('/').percent}%"),
            ("Prozesse", str(len(psutil.pids()))),
        ]

        for i, (title, value) in enumerate(cards):
            card = ctk.CTkFrame(cards_frame, width=150, height=80)
            card.grid(row=0, column=i, padx=10, pady=5, sticky="nsew")
            ctk.CTkLabel(card, text=title).pack(pady=(10, 5))
            ctk.CTkLabel(
                card, text=value, font=ctk.CTkFont(size=18, weight="bold")
            ).pack(pady=5)

        ctk.CTkButton(dashboard, text="Quick Scan", command=self.quick_scan).pack(
            pady=20
        )

    def quick_scan(self):
        self.output_queue.put("Quick Scan laeuft...")

    def show_network(self):
        self.clear_main_area()
        self.highlight_nav("Netzwerk-Scan")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Netzwerk-Scanner", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)
        ctk.CTkButton(
            frame, text="Netzwerk scannen", command=self.start_network_scan
        ).pack(pady=10)
        self.network_tree = ttk.Treeview(
            frame, columns=("IP", "MAC", "Hostname"), show="headings"
        )
        for col in ("IP", "MAC", "Hostname"):
            self.network_tree.heading(col, text=col)
        self.network_tree.pack(fill="both", expand=True, pady=10)

    def start_network_scan(self):
        if MODULES_AVAILABLE:
            threading.Thread(target=self._scan_network, daemon=True).start()

    def _scan_network(self):
        devices = self.network_scanner.scan_network()
        self.after(0, lambda: self._update_tree(devices))

    def _update_tree(self, devices):
        for item in self.network_tree.get_children():
            self.network_tree.delete(item)
        for d in devices:
            self.network_tree.insert(
                "",
                "end",
                values=(d.get("ip", ""), d.get("mac", ""), d.get("hostname", "")),
            )

    def show_wifi(self):
        self.clear_main_area()
        self.highlight_nav("WLAN-Audit")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="WLAN-Audit", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)
        ctk.CTkButton(frame, text="Netzwerke scannen", command=self.scan_wifi).pack(
            pady=10
        )

    def scan_wifi(self):
        if MODULES_AVAILABLE:
            nets = self.wifi_auditor.scan_networks()
            self.output_queue.put(f"{len(nets)} Netzwerke gefunden")

    def show_ports(self):
        self.clear_main_area()
        self.highlight_nav("Port-Manager")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Port-Manager", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)
        ctk.CTkButton(frame, text="Ports anzeigen", command=self.load_ports).pack(
            pady=10
        )
        self.port_tree = ttk.Treeview(
            frame, columns=("Port", "PID", "Prozess"), show="headings"
        )
        for col in ("Port", "PID", "Prozess"):
            self.port_tree.heading(col, text=col)
        self.port_tree.pack(fill="both", expand=True)

    def load_ports(self):
        if MODULES_AVAILABLE:
            ports = self.port_manager.get_open_ports()
            for p in ports[:30]:
                self.port_tree.insert(
                    "", "end", values=(p["port"], p["pid"], p["process"])
                )

    def show_processes(self):
        self.clear_main_area()
        self.highlight_nav("Prozesse")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Prozesse", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)
        self.proc_tree = ttk.Treeview(
            frame, columns=("PID", "Name", "CPU"), show="headings"
        )
        for col in ("PID", "Name", "CPU"):
            self.proc_tree.heading(col, text=col)
        self.proc_tree.pack(fill="both", expand=True)
        self.refresh_procs()

    def refresh_procs(self):
        if MODULES_AVAILABLE:
            procs = self.process_monitor.get_all_processes()
            for p in procs[:30]:
                self.proc_tree.insert(
                    "", "end", values=(p["pid"], p["name"], f"{p['cpu']:.1f}")
                )

    def show_wireguard(self):
        self.clear_main_area()
        self.highlight_nav("WireGuard VPN")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="WireGuard VPN", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)
        ctk.CTkButton(frame, text="Keys generieren", command=self.gen_keys).pack(
            pady=10
        )

    def gen_keys(self):
        if MODULES_AVAILABLE:
            k = self.wireguard.generate_keys()
            self.output_queue.put("Keys generiert")

    def show_anonymizer(self):
        self.clear_main_area()
        self.highlight_nav("Anonymisierung")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Anonymisierung", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)
        ctk.CTkButton(frame, text="TOR starten", command=self.start_tor).pack(pady=10)

    def start_tor(self):
        if MODULES_AVAILABLE:
            self.anonymizer.start_anonsurf()
            self.output_queue.put("TOR gestartet")

    def show_router(self):
        self.clear_main_area()
        self.highlight_nav("Router-Tools")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Router-Tools", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)

    def show_ids(self):
        self.clear_main_area()
        self.highlight_nav("IDS/IPS")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="IDS/IPS", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)
        ctk.CTkButton(frame, text="IDS starten", command=self.ids_start).pack(pady=10)

    def ids_start(self):
        if MODULES_AVAILABLE:
            self.ids.start()
            self.output_queue.put("IDS gestartet")

    def show_integrity(self):
        self.clear_main_area()
        self.highlight_nav("Datei-Integritaet")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Datei-Integritaet", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)

    def show_forensics(self):
        self.clear_main_area()
        self.highlight_nav("Forensik")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Forensik", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)

    def show_rollback(self):
        self.clear_main_area()
        self.highlight_nav("Rollback")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Rollback", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)

    def show_logs(self):
        self.clear_main_area()
        self.highlight_nav("Logs")
        frame = ctk.CTkFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(frame, text="Logs", font=ctk.CTkFont(size=24, weight="bold")).pack(
            pady=10
        )
        self.log_text = ctk.CTkTextbox(frame, height=400)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

    def show_settings(self):
        self.clear_main_area()
        self.highlight_nav("Einstellungen")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Einstellungen", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)

    def highlight_nav(self, key):
        for k, btn in self.nav_buttons.items():
            btn.configure(fg_color=("gray75", "gray25") if k == key else "transparent")


if __name__ == "__main__":
    app = CyberGuardianApp()
    app.mainloop()
