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

# ANIME COCKPIT / HUD / SCI-FI THEME
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# Cyberpunk Anime Cockpit Colors
COLORS = {
    # Backgrounds
    "bg_primary": "#0a0a1a",
    "bg_secondary": "#0d0d2d",
    "bg_tertiary": "#12123d",
    "bg_panels": "#0a0f1a",
    # Neon Glows
    "neon_cyan": "#00ffff",
    "neon_magenta": "#ff00ff",
    "neon_pink": "#ff1493",
    "neon_purple": "#bf00ff",
    "neon_blue": "#0080ff",
    "neon_yellow": "#ffff00",
    # Status Colors
    "alert_green": "#00ff88",
    "alert_yellow": "#ffaa00",
    "alert_red": "#ff0040",
    "alert_blue": "#00aaff",
    # HUD Elements
    "hud_lines": "#1a4a6a",
    "hud_glow": "#00ffff",
    "grid_lines": "#1a3a5a",
    "panel_border": "#2a4a7a",
    # Text
    "text_bright": "#ffffff",
    "text_normal": "#aaddff",
    "text_dim": "#6699cc",
}

# Anime HUD Fonts
FONT_HUD = ("Consolas", 11)
FONT_HUD_BOLD = ("Consolas", 12, "bold")
FONT_HUD_LARGE = ("Consolas", 16, "bold")
FONT_HUD_HEADER = ("Consolas", 20, "bold")
FONT_HUD_TITLE = ("Consolas", 28, "bold")
FONT_JP = ("MS Gothic", 10)  # Japanese style font

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
        # ANIME COCKPIT HEADER
        header = ctk.CTkFrame(
            self.main_container,
            height=90,
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["neon_cyan"],
            border_width=3,
        )
        header.pack(fill="x", pady=(0, 10))
        header.pack_propagate(False)

        # HUD CORNER DECORATIONS
        corner_tl = ctk.CTkLabel(
            header,
            text="◢",
            font=FONT_HUD_LARGE,
            text_color=COLORS["neon_cyan"],
            fg_color="transparent",
        )
        corner_tl.place(x=5, y=5)

        corner_tr = ctk.CTkLabel(
            header,
            text="◣",
            font=FONT_HUD_LARGE,
            text_color=COLORS["neon_cyan"],
            fg_color="transparent",
        )
        corner_tr.place(x=1330, y=5)

        # MAIN TITLE - ANIME STYLE
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=30, pady=10)

        # Japanese style subtitle
        ctk.CTkLabel(
            title_frame,
            text="サイバーガーディアン",
            font=FONT_JP,
            text_color=COLORS["neon_magenta"],
        ).pack(anchor="w")

        # Main title with glow effect simulation
        ctk.CTkLabel(
            title_frame,
            text="◄ CYBERGUARDIAN PRO ►",
            font=FONT_HUD_TITLE,
            text_color=COLORS["neon_cyan"],
        ).pack(anchor="w")

        # Version indicator
        ctk.CTkLabel(
            title_frame,
            text="◈ SYSTEM v2.0 ◈",
            font=FONT_HUD,
            text_color=COLORS["text_dim"],
        ).pack(anchor="w")

        # STATUS PANEL (Right side - HUD Style)
        status_panel = ctk.CTkFrame(
            header,
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["hud_lines"],
            border_width=2,
            width=400,
            height=70,
        )
        status_panel.pack(side="right", padx=20, pady=10)
        status_panel.pack_propagate(False)

        # Connection status lights
        lights_frame = ctk.CTkFrame(status_panel, fg_color="transparent")
        lights_frame.pack(side="left", padx=15, pady=10)

        indicators = [
            ("NET", COLORS["alert_green"]),
            ("SEC", COLORS["neon_cyan"]),
            ("VPN", COLORS["neon_purple"]),
            ("TOR", COLORS["neon_magenta"]),
        ]

        for label, color in indicators:
            ind_frame = ctk.CTkFrame(lights_frame, fg_color="transparent")
            ind_frame.pack(side="left", padx=10)

            # Glowing indicator
            ctk.CTkLabel(
                ind_frame,
                text="●",
                font=("Arial", 20),
                text_color=color,
            ).pack()

            ctk.CTkLabel(
                ind_frame,
                text=label,
                font=FONT_HUD,
                text_color=color,
            ).pack()

        # PANIC BUTTON - EMERGENCY STYLE
        panic_btn = ctk.CTkButton(
            status_panel,
            text="ABORT",
            fg_color=COLORS["alert_red"],
            text_color=COLORS["text_bright"],
            font=FONT_HUD_BOLD,
            width=80,
            height=50,
            border_width=3,
            border_color=COLORS["neon_pink"],
            corner_radius=5,
            command=self.panic_stop,
        )
        panic_btn.pack(side="right", padx=15, pady=10)

    def create_sidebar(self):
        # ANIME COCKPIT SIDEBAR
        self.sidebar = ctk.CTkFrame(
            self.content_frame,
            width=260,
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["neon_cyan"],
            border_width=2,
        )
        self.sidebar.pack(side="left", fill="y", padx=(0, 10))
        self.sidebar.pack_propagate(False)

        # CORNER DECORATION
        corner_l = ctk.CTkLabel(
            self.sidebar,
            text="┏",
            font=FONT_HUD_LARGE,
            text_color=COLORS["neon_cyan"],
        )
        corner_l.place(x=5, y=5)

        # MODULE SELECTOR - HUD STYLE
        ctk.CTkLabel(
            self.sidebar,
            text="◄ MODULES ►",
            font=FONT_HUD_BOLD,
            text_color=COLORS["neon_magenta"],
        ).pack(pady=(20, 15), fill="x")

        nav_items = [
            ("01 ■ DASHBOARD", self.show_dashboard, COLORS["neon_cyan"]),
            ("02 ■ NETWORK", self.show_network, COLORS["neon_blue"]),
            ("03 ■ WIRELESS", self.show_wifi, COLORS["neon_purple"]),
            ("04 ■ PORTS", self.show_ports, COLORS["neon_cyan"]),
            ("05 ■ PROCESSES", self.show_processes, COLORS["neon_blue"]),
            ("06 ■ VPN", self.show_wireguard, COLORS["neon_purple"]),
            ("07 ■ ANONYM", self.show_anonymizer, COLORS["neon_magenta"]),
            ("08 ■ ROUTER", self.show_router, COLORS["neon_cyan"]),
            ("09 ■ IDS/IPS", self.show_ids, COLORS["alert_red"]),
            ("10 ■ INTEGRITY", self.show_integrity, COLORS["neon_blue"]),
            ("11 ■ FORENSICS", self.show_forensics, COLORS["neon_purple"]),
            ("12 ■ ROLLBACK", self.show_rollback, COLORS["neon_magenta"]),
            ("13 ■ LOGS", self.show_logs, COLORS["neon_cyan"]),
            ("14 ■ CONFIG", self.show_settings, COLORS["text_dim"]),
        ]

        self.nav_buttons = {}
        for text, command, color in nav_items:
            btn = ctk.CTkButton(
                self.sidebar,
                text=text,
                anchor="w",
                command=command,
                fg_color=COLORS["bg_panels"],
                text_color=color,
                hover_color=COLORS["bg_tertiary"],
                border_width=2,
                border_color=COLORS["hud_lines"],
                font=FONT_HUD,
                height=32,
                corner_radius=2,
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.nav_buttons[text] = btn

        # SYSTEM INFO PANEL - BOTTOM
        info_frame = ctk.CTkFrame(
            self.sidebar,
            fg_color=COLORS["bg_panels"],
            border_color=COLORS["hud_lines"],
            border_width=2,
        )
        info_frame.pack(side="bottom", fill="x", padx=12, pady=15)

        ctk.CTkLabel(
            info_frame,
            text="◄ SYS.INFO ►",
            font=FONT_HUD_BOLD,
            text_color=COLORS["neon_cyan"],
        ).pack(pady=(8, 5))

        sys_info = self.get_system_info()
        ctk.CTkLabel(
            info_frame,
            text=sys_info,
            justify="left",
            font=FONT_HUD,
            text_color=COLORS["text_normal"],
        ).pack(pady=5)

    def create_main_area(self):
        self.main_area = ctk.CTkFrame(
            self.content_frame,
            fg_color=COLORS["bg_primary"],
            border_color=COLORS["panel_border"],
            border_width=2,
        )
        self.main_area.pack(side="right", fill="both", expand=True)
        self.show_dashboard()

    def create_statusbar(self):
        self.statusbar = ctk.CTkFrame(
            self.main_container,
            height=30,
            fg_color=COLORS["bg_secondary"],
            border_color=COLORS["panel_border"],
            border_width=1,
        )
        self.statusbar.pack(fill="x", pady=(10, 0))

        self.status_label = ctk.CTkLabel(
            self.statusbar,
            text="> SYSTEM BEREIT",
            anchor="w",
            font=FONT_HUD,
            text_color=COLORS["neon_cyan"],
            fg_color=COLORS["bg_secondary"],
        )
        self.status_label.pack(side="left", padx=10)

        self.time_label = ctk.CTkLabel(
            self.statusbar,
            text=datetime.now().strftime("%H:%M:%S"),
            font=FONT_HUD,
            text_color=COLORS["text_dim"],
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
        self.highlight_nav("01 ■ DASHBOARD")

        # ANIME COCKPIT DASHBOARD
        dashboard = ctk.CTkScrollableFrame(
            self.main_area,
            fg_color=COLORS["bg_primary"],
        )
        dashboard.pack(fill="both", expand=True, padx=15, pady=15)

        # HEADER PANEL
        header_panel = ctk.CTkFrame(
            dashboard,
            fg_color=COLORS["bg_panels"],
            border_color=COLORS["neon_cyan"],
            border_width=2,
        )
        header_panel.pack(fill="x", pady=(0, 20))

        ctk.CTkLabel(
            header_panel,
            text="◄ MAIN CONTROL INTERFACE ►",
            font=FONT_HUD_HEADER,
            text_color=COLORS["neon_cyan"],
        ).pack(pady=15)

        # SYSTEM METRICS - HUD STYLE
        metrics_frame = ctk.CTkFrame(dashboard, fg_color="transparent")
        metrics_frame.pack(fill="x", pady=20)

        metrics = [
            ("CPU LOAD", f"{psutil.cpu_percent()}%", COLORS["neon_cyan"]),
            ("MEMORY", f"{psutil.virtual_memory().percent}%", COLORS["neon_blue"]),
            ("STORAGE", f"{psutil.disk_usage('/').percent}%", COLORS["neon_purple"]),
            ("PROCESSES", str(len(psutil.pids())), COLORS["neon_magenta"]),
        ]

        for i, (label, value, color) in enumerate(metrics):
            metric_card = ctk.CTkFrame(
                metrics_frame,
                fg_color=COLORS["bg_panels"],
                border_color=color,
                border_width=2,
                width=180,
                height=100,
            )
            metric_card.grid(row=0, column=i, padx=10, pady=5, sticky="nsew")
            metric_card.pack_propagate(False)

            # Glowing label
            ctk.CTkLabel(
                metric_card,
                text=label,
                font=FONT_HUD,
                text_color=COLORS["text_dim"],
            ).pack(pady=(10, 5))

            # Value with bright color
            ctk.CTkLabel(
                metric_card,
                text=value,
                font=FONT_HUD_LARGE,
                text_color=color,
            ).pack(pady=5)

            # Decorative line
            line = ctk.CTkFrame(metric_card, fg_color=color, height=2, width=100)
            line.pack(pady=(0, 5))

        # QUICK ACTIONS PANEL
        actions_panel = ctk.CTkFrame(
            dashboard,
            fg_color=COLORS["bg_panels"],
            border_color=COLORS["hud_lines"],
            border_width=2,
        )
        actions_panel.pack(fill="x", pady=20, padx=10)

        ctk.CTkLabel(
            actions_panel,
            text="◄ QUICK ACTIONS ►",
            font=FONT_HUD_BOLD,
            text_color=COLORS["neon_magenta"],
        ).pack(pady=10)

        actions_frame = ctk.CTkFrame(actions_panel, fg_color="transparent")
        actions_frame.pack(pady=10)

        actions = [
            ("NETWORK SCAN", self.quick_scan, COLORS["neon_cyan"]),
            ("SYSTEM CHECK", self.quick_scan, COLORS["neon_blue"]),
            ("PORT CHECK", self.quick_scan, COLORS["neon_purple"]),
        ]

        for text, cmd, color in actions:
            btn = ctk.CTkButton(
                actions_frame,
                text=text,
                command=cmd,
                fg_color=COLORS["bg_secondary"],
                text_color=color,
                border_width=2,
                border_color=color,
                font=FONT_HUD_BOLD,
                width=140,
                height=40,
                corner_radius=3,
            )
            btn.pack(side="left", padx=10)

    def quick_scan(self):
        self.output_queue.put("Quick Scan laeuft...")

    def show_network(self):
        self.clear_main_area()
        self.highlight_nav("02 ■ NETWORK")
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
        self.highlight_nav("03 ■ WIRELESS")
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
        self.highlight_nav("04 ■ PORTS")
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
        self.highlight_nav("05 ■ PROCESSES")
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
        self.highlight_nav("06 ■ VPN")
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
        self.highlight_nav("07 ■ ANONYM")
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
        self.highlight_nav("08 ■ ROUTER")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Router-Tools", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)

    def show_ids(self):
        self.clear_main_area()
        self.highlight_nav("09 ■ IDS/IPS")
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
        self.highlight_nav("10 ■ INTEGRITY")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Datei-Integritaet", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)

    def show_forensics(self):
        self.clear_main_area()
        self.highlight_nav("11 ■ FORENSICS")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Forensik", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)

    def show_rollback(self):
        self.clear_main_area()
        self.highlight_nav("12 ■ ROLLBACK")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Rollback", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)

    def show_logs(self):
        self.clear_main_area()
        self.highlight_nav("13 ■ LOGS")
        frame = ctk.CTkFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(frame, text="Logs", font=ctk.CTkFont(size=24, weight="bold")).pack(
            pady=10
        )
        self.log_text = ctk.CTkTextbox(frame, height=400)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)

    def show_settings(self):
        self.clear_main_area()
        self.highlight_nav("14 ■ CONFIG")
        frame = ctk.CTkScrollableFrame(self.main_area)
        frame.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(
            frame, text="Einstellungen", font=ctk.CTkFont(size=24, weight="bold")
        ).pack(pady=10)

    def highlight_nav(self, key):
        # ANIME COCKPIT STYLE NAVIGATION HIGHLIGHT
        for k, btn in self.nav_buttons.items():
            if k == key:
                # Active button - glowing cyan border
                btn.configure(
                    fg_color=COLORS["bg_tertiary"],
                    border_color=COLORS["neon_cyan"],
                    border_width=3,
                )
            else:
                # Inactive button - subtle styling
                btn.configure(
                    fg_color=COLORS["bg_panels"],
                    border_color=COLORS["hud_lines"],
                    border_width=2,
                )


if __name__ == "__main__":
    app = CyberGuardianApp()
    app.mainloop()
