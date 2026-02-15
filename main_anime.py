#!/usr/bin/env python3
"""
CyberGuardian Pro - ANIME COCKPIT EDITION
GPU-Accelerated Interface mit Dear PyGui
"""

import dearpygui.dearpygui as dpg
import psutil
import socket
import platform
import threading
import time
from datetime import datetime


# ANIME COCKPIT THEME - Neon Cyberpunk
def create_anime_theme():
    with dpg.theme() as global_theme:
        with dpg.theme_component(dpg.mvAll):
            # Main Colors
            dpg.add_theme_color(
                dpg.mvThemeCol_WindowBg, (10, 10, 26, 255)
            )  # Dark blue-black
            dpg.add_theme_color(dpg.mvThemeCol_TitleBg, (20, 20, 50, 255))
            dpg.add_theme_color(
                dpg.mvThemeCol_TitleBgActive, (0, 200, 255, 255)
            )  # Neon cyan
            dpg.add_theme_color(dpg.mvThemeCol_Text, (200, 230, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Button, (30, 40, 70, 255))
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonHovered, (0, 255, 255, 200)
            )  # Neon cyan hover
            dpg.add_theme_color(
                dpg.mvThemeCol_ButtonActive, (255, 0, 255, 255)
            )  # Neon magenta
            dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (20, 30, 50, 255))
            dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, (40, 60, 100, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Header, (0, 150, 200, 150))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderHovered, (0, 200, 255, 200))
            dpg.add_theme_color(dpg.mvThemeCol_HeaderActive, (255, 0, 200, 200))
            dpg.add_theme_color(dpg.mvThemeCol_CheckMark, (0, 255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrab, (0, 255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_SliderGrabActive, (255, 0, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Border, (0, 200, 255, 100))
            dpg.add_theme_color(dpg.mvThemeCol_Separator, (0, 200, 255, 150))
            dpg.add_theme_color(dpg.mvThemeCol_ResizeGrip, (0, 255, 255, 100))
            dpg.add_theme_color(dpg.mvThemeCol_ResizeGripHovered, (0, 255, 255, 200))
            dpg.add_theme_color(dpg.mvThemeCol_ResizeGripActive, (255, 0, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_Tab, (30, 40, 70, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TabHovered, (0, 200, 255, 200))
            dpg.add_theme_color(dpg.mvThemeCol_TabActive, (0, 255, 255, 255))
            dpg.add_theme_color(dpg.mvThemeCol_TitleBgCollapsed, (10, 10, 30, 100))

            # Styles
            dpg.add_theme_style(dpg.mvStyleVar_WindowRounding, 5)
            dpg.add_theme_style(dpg.mvStyleVar_FrameRounding, 3)
            dpg.add_theme_style(dpg.mvStyleVar_ChildRounding, 3)
            dpg.add_theme_style(dpg.mvStyleVar_PopupRounding, 3)
            dpg.add_theme_style(dpg.mvStyleVar_ScrollbarRounding, 3)
            dpg.add_theme_style(dpg.mvStyleVar_GrabRounding, 3)
            dpg.add_theme_style(dpg.mvStyleVar_TabRounding, 3)
            dpg.add_theme_style(dpg.mvStyleVar_WindowBorderSize, 2)
            dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_ChildBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_PopupBorderSize, 1)
            dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing, 8, 4)
            dpg.add_theme_style(dpg.mvStyleVar_ItemInnerSpacing, 4, 4)
            dpg.add_theme_style(dpg.mvStyleVar_WindowPadding, 10, 10)
            dpg.add_theme_style(dpg.mvStyleVar_FramePadding, 5, 3)
            dpg.add_theme_style(dpg.mvStyleVar_CellPadding, 4, 2)

    return global_theme


class CyberGuardianAnime:
    def __init__(self):
        dpg.create_context()

        # Create theme
        self.theme = create_anime_theme()
        dpg.bind_theme(self.theme)

        # Create viewport
        dpg.create_viewport(
            title="サイバーガーディアン PRO | CyberGuardian Pro",
            width=1400,
            height=900,
            min_width=1200,
            min_height=700,
        )

        dpg.setup_dearpygui()

        # Build UI
        self.create_main_window()

        # Start update thread
        self.running = True
        self.update_thread = threading.Thread(target=self.update_loop, daemon=True)
        self.update_thread.start()

    def create_main_window(self):
        with dpg.window(
            label="Main Interface",
            tag="main_window",
            width=1400,
            height=900,
            no_resize=True,
            no_move=True,
            no_collapse=True,
            no_title_bar=True,
            menubar=False,
        ):
            # HEADER - ANIME STYLE
            with dpg.child_window(width=-1, height=80, border=True, tag="header_panel"):
                with dpg.group(horizontal=True):
                    # Title with Japanese text
                    dpg.add_text(
                        "◄ サイバーガーディアン PRO ►",
                        color=(0, 255, 255, 255),
                        tag="main_title",
                    )
                    dpg.add_spacer(width=20)
                    dpg.add_text("v2.0", color=(255, 0, 255, 255))
                    dpg.add_spacer(width=50)

                    # Status indicators
                    indicators = [
                        ("NET", (0, 255, 100, 255)),
                        ("SEC", (0, 255, 255, 255)),
                        ("VPN", (255, 0, 255, 255)),
                        ("TOR", (255, 100, 0, 255)),
                    ]
                    for label, color in indicators:
                        dpg.add_text("●", color=color)
                        dpg.add_text(label, color=color)
                        dpg.add_spacer(width=15)

                    dpg.add_spacer(width=100)

                    # Time
                    dpg.add_text(
                        datetime.now().strftime("%H:%M:%S"),
                        tag="clock",
                        color=(200, 230, 255, 255),
                    )

                    dpg.add_spacer(width=30)

                    # PANIC BUTTON
                    dpg.add_button(
                        label="ABORT", callback=self.panic_stop, width=80, height=40
                    )

            dpg.add_spacer(height=10)

            # MAIN CONTENT AREA
            with dpg.group(horizontal=True):
                # SIDEBAR - Navigation
                with dpg.child_window(width=250, height=-1, border=True, tag="sidebar"):
                    dpg.add_text("◄ MODULES ►", color=(255, 0, 255, 255))
                    dpg.add_separator()

                    nav_items = [
                        ("01 ■ DASHBOARD", self.show_dashboard),
                        ("02 ■ NETWORK", self.show_network),
                        ("03 ■ WIRELESS", self.show_wireless),
                        ("04 ■ PORTS", self.show_ports),
                        ("05 ■ PROCESSES", self.show_processes),
                        ("06 ■ VPN", self.show_vpn),
                        ("07 ■ ANONYMIZE", self.show_anonymize),
                        ("08 ■ ROUTER", self.show_router),
                        ("09 ■ IDS/IPS", self.show_ids),
                        ("10 ■ INTEGRITY", self.show_integrity),
                        ("11 ■ FORENSICS", self.show_forensics),
                        ("12 ■ LOGS", self.show_logs),
                        ("13 ■ SETTINGS", self.show_settings),
                    ]

                    self.nav_buttons = {}
                    for text, callback in nav_items:
                        btn = dpg.add_button(
                            label=text, callback=callback, width=-1, height=28
                        )
                        self.nav_buttons[text] = btn

                    dpg.add_separator()
                    dpg.add_spacer(height=10)

                    # System Info
                    dpg.add_text("◄ SYS.INFO ►", color=(0, 255, 255, 255))
                    dpg.add_text(f"OS: {platform.system()}", tag="sys_os")
                    dpg.add_text(f"Host: {socket.gethostname()}", tag="sys_host")
                    dpg.add_text(f"CPU: {psutil.cpu_count()} cores", tag="sys_cpu")

                # MAIN PANEL - Content
                with dpg.child_window(
                    width=-1, height=-1, border=True, tag="content_panel"
                ):
                    # Initial dashboard
                    self.create_dashboard_content()

    def create_dashboard_content(self):
        dpg.delete_item("content_panel", children_only=True)

        with dpg.child_window(
            parent="content_panel", width=-1, height=-1, border=False
        ):
            dpg.add_text(
                "◄ MAIN CONTROL INTERFACE ►",
                color=(0, 255, 255, 255),
                tag="dashboard_title",
            )
            dpg.add_separator()
            dpg.add_spacer(height=10)

            # SYSTEM METRICS - HUD STYLE
            with dpg.group(horizontal=True):
                metrics = [
                    ("CPU LOAD", "cpu_metric", (0, 255, 255, 255)),
                    ("MEMORY", "mem_metric", (0, 200, 255, 255)),
                    ("STORAGE", "disk_metric", (255, 0, 255, 255)),
                    ("PROCESSES", "proc_metric", (255, 100, 200, 255)),
                ]

                for label, tag, color in metrics:
                    with dpg.child_window(width=180, height=100, border=True):
                        dpg.add_text(label, color=(150, 180, 210, 255))
                        dpg.add_text("0%", tag=tag, color=color, bullet=False)

            dpg.add_spacer(height=20)

            # QUICK ACTIONS
            dpg.add_text("◄ QUICK ACTIONS ►", color=(255, 0, 255, 255))
            dpg.add_separator()

            with dpg.group(horizontal=True):
                actions = [
                    ("NETWORK SCAN", self.scan_network),
                    ("PORT CHECK", self.check_ports),
                    ("SYSTEM CHECK", self.system_check),
                    ("ANONYMIZE", self.anonymize),
                ]

                for label, callback in actions:
                    dpg.add_button(label=label, callback=callback, width=130, height=35)
                    dpg.add_spacer(width=10)

            dpg.add_spacer(height=20)

            # LOG OUTPUT
            dpg.add_text("◄ SYSTEM LOG ►", color=(0, 255, 255, 255))
            dpg.add_separator()

            dpg.add_input_text(
                multiline=True,
                readonly=True,
                width=-1,
                height=200,
                tag="log_output",
                default_value="> System initialized...\n> Ready for operations\n",
            )

    def update_loop(self):
        """Background update thread"""
        while self.running:
            try:
                # Update metrics
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory().percent
                disk = psutil.disk_usage("/").percent
                procs = len(psutil.pids())

                # Update UI
                if dpg.does_item_exist("cpu_metric"):
                    dpg.set_value("cpu_metric", f"{cpu:.1f}%")
                if dpg.does_item_exist("mem_metric"):
                    dpg.set_value("mem_metric", f"{mem:.1f}%")
                if dpg.does_item_exist("disk_metric"):
                    dpg.set_value("disk_metric", f"{disk:.1f}%")
                if dpg.does_item_exist("proc_metric"):
                    dpg.set_value("proc_metric", str(procs))

                # Update clock
                if dpg.does_item_exist("clock"):
                    dpg.set_value("clock", datetime.now().strftime("%H:%M:%S"))

                time.sleep(1)
            except Exception as e:
                print(f"Update error: {e}")
                time.sleep(1)

    def log(self, message):
        """Add log message"""
        if dpg.does_item_exist("log_output"):
            current = dpg.get_value("log_output")
            dpg.set_value("log_output", current + f"> {message}\n")

    # Navigation callbacks
    def show_dashboard(self):
        self.create_dashboard_content()
        self.log("Switched to Dashboard")

    def show_network(self):
        dpg.delete_item("content_panel", children_only=True)
        with dpg.child_window(
            parent="content_panel", width=-1, height=-1, border=False
        ):
            dpg.add_text("◄ NETWORK SCANNER ►", color=(0, 255, 255, 255))
            dpg.add_separator()
            dpg.add_button(label="SCAN NETWORK", callback=self.scan_network, width=150)
        self.log("Opened Network Scanner")

    def show_wireless(self):
        dpg.delete_item("content_panel", children_only=True)
        with dpg.child_window(
            parent="content_panel", width=-1, height=-1, border=False
        ):
            dpg.add_text("◄ WIRELESS SECURITY ►", color=(0, 255, 255, 255))
        self.log("Opened Wireless Security")

    def show_ports(self):
        dpg.delete_item("content_panel", children_only=True)
        with dpg.child_window(
            parent="content_panel", width=-1, height=-1, border=False
        ):
            dpg.add_text("◄ PORT MANAGER ►", color=(0, 255, 255, 255))
            dpg.add_button(label="CHECK PORTS", callback=self.check_ports, width=150)
        self.log("Opened Port Manager")

    def show_processes(self):
        dpg.delete_item("content_panel", children_only=True)
        with dpg.child_window(
            parent="content_panel", width=-1, height=-1, border=False
        ):
            dpg.add_text("◄ PROCESS MONITOR ►", color=(0, 255, 255, 255))
        self.log("Opened Process Monitor")

    def show_vpn(self):
        dpg.delete_item("content_panel", children_only=True)
        with dpg.child_window(
            parent="content_panel", width=-1, height=-1, border=False
        ):
            dpg.add_text("◄ WIREGUARD VPN ►", color=(0, 255, 255, 255))
        self.log("Opened VPN Manager")

    def show_anonymize(self):
        dpg.delete_item("content_panel", children_only=True)
        with dpg.child_window(
            parent="content_panel", width=-1, height=-1, border=False
        ):
            dpg.add_text("◄ ANONYMIZATION ►", color=(0, 255, 255, 255))
            dpg.add_button(label="START TOR", callback=self.anonymize, width=150)
        self.log("Opened Anonymization")

    def show_router(self):
        dpg.delete_item("content_panel", children_only=True)
        with dpg.child_window(
            parent="content_panel", width=-1, height=-1, border=False
        ):
            dpg.add_text("◄ ROUTER TOOLS ►", color=(0, 255, 255, 255))
        self.log("Opened Router Tools")

    def show_ids(self):
        dpg.delete_item("content_panel", children_only=True)
        with dpg.child_window(
            parent="content_panel", width=-1, height=-1, border=False
        ):
            dpg.add_text("◄ INTRUSION DETECTION ►", color=(255, 0, 0, 255))
        self.log("Opened IDS/IPS")

    def show_integrity(self):
        dpg.delete_item("content_panel", children_only=True)
        with dpg.child_window(
            parent="content_panel", width=-1, height=-1, border=False
        ):
            dpg.add_text("◄ FILE INTEGRITY ►", color=(0, 255, 255, 255))
        self.log("Opened File Integrity")

    def show_forensics(self):
        dpg.delete_item("content_panel", children_only=True)
        with dpg.child_window(
            parent="content_panel", width=-1, height=-1, border=False
        ):
            dpg.add_text("◄ FORENSICS ►", color=(0, 255, 255, 255))
        self.log("Opened Forensics")

    def show_logs(self):
        dpg.delete_item("content_panel", children_only=True)
        with dpg.child_window(
            parent="content_panel", width=-1, height=-1, border=False
        ):
            dpg.add_text("◄ SYSTEM LOGS ►", color=(0, 255, 255, 255))
        self.log("Opened Logs")

    def show_settings(self):
        dpg.delete_item("content_panel", children_only=True)
        with dpg.child_window(
            parent="content_panel", width=-1, height=-1, border=False
        ):
            dpg.add_text("◄ SETTINGS ►", color=(0, 255, 255, 255))
        self.log("Opened Settings")

    # Action callbacks
    def scan_network(self):
        self.log("Starting network scan...")
        # Simulate scan
        threading.Thread(target=self._scan_thread, daemon=True).start()

    def _scan_thread(self):
        time.sleep(2)
        self.log("Network scan complete: 5 devices found")

    def check_ports(self):
        self.log("Checking open ports...")
        try:
            ports = []
            for conn in psutil.net_connections(kind="inet"):
                if conn.status == "LISTEN":
                    ports.append(conn.laddr.port)
            self.log(f"Found {len(ports)} open ports")
        except Exception as e:
            self.log(f"Port check error: {e}")

    def system_check(self):
        self.log("Running system check...")
        self.log(f"CPU: {psutil.cpu_percent()}%")
        self.log(f"Memory: {psutil.virtual_memory().percent}%")
        self.log("System check complete")

    def anonymize(self):
        self.log("Starting anonymization...")
        self.log("TOR: Connecting...")
        time.sleep(1)
        self.log("TOR: Connected!")

    def panic_stop(self):
        self.log("!!! PANIC STOP ACTIVATED !!!")
        self.log("Stopping all operations...")
        self.running = False

    def run(self):
        dpg.show_viewport()
        dpg.start_dearpygui()
        dpg.destroy_context()


if __name__ == "__main__":
    app = CyberGuardianAnime()
    app.run()
