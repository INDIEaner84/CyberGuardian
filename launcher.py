#!/usr/bin/env python3
"""
CyberGuardian Pro - Smart Launcher
Prüft Abhängigkeiten und wählt die beste GUI-Version
"""

import subprocess
import sys
import os
import platform
import time


class Colors:
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    END = "\033[0m"
    BOLD = "\033[1m"


def print_header():
    print(f"""
{Colors.CYAN}{Colors.BOLD}
╔══════════════════════════════════════════════════════════╗
║     サイバーガーディアン PRO - CyberGuardian Pro v2.0     ║
║              SMART LAUNCHER & DEPENDENCY CHECK           ║
╚══════════════════════════════════════════════════════════╝{Colors.END}
""")


def check_command(cmd, name):
    """Check if a command exists"""
    try:
        subprocess.run([cmd, "--version"], capture_output=True, check=True)
        print(f"{Colors.GREEN}✓{Colors.END} {name} gefunden")
        return True
    except:
        print(f"{Colors.RED}✗{Colors.END} {name} nicht gefunden")
        return False


def install_system_deps():
    """Install system dependencies"""
    print(f"\n{Colors.YELLOW}[SYSTEM-ABHÄNGIGKEITEN]{Colors.END}")

    deps = {"nmap": "nmap", "tor": "tor", "macchanger": "macchanger"}

    missing = []
    for cmd, name in deps.items():
        if not check_command(cmd, name):
            missing.append(cmd)

    if missing:
        print(
            f"\n{Colors.YELLOW}Fehlende System-Tools: {', '.join(missing)}{Colors.END}"
        )

        if platform.system() == "Linux":
            print(f"{Colors.CYAN}Installiere...{Colors.END}")
            try:
                # Detect package manager
                if check_command("apt-get", "APT"):
                    subprocess.run(["sudo", "apt-get", "update", "-qq"], check=False)
                    subprocess.run(
                        ["sudo", "apt-get", "install", "-y", "-qq"] + missing,
                        check=False,
                    )
                elif check_command("pacman", "Pacman"):
                    subprocess.run(
                        ["sudo", "pacman", "-Sy", "--noconfirm"] + missing, check=False
                    )
                elif check_command("dnf", "DNF"):
                    subprocess.run(
                        ["sudo", "dnf", "install", "-y"] + missing, check=False
                    )

                print(f"{Colors.GREEN}✓ System-Tools installiert{Colors.END}")
            except Exception as e:
                print(f"{Colors.RED}✗ Installation fehlgeschlagen: {e}{Colors.END}")
        else:
            print(f"{Colors.YELLOW}Bitte manuell installieren{Colors.END}")
    else:
        print(f"{Colors.GREEN}✓ Alle System-Tools vorhanden{Colors.END}")


def install_python_deps():
    """Install Python dependencies"""
    print(f"\n{Colors.YELLOW}[PYTHON-ABHÄNGIGKEITEN]{Colors.END}")

    deps = [
        "customtkinter>=5.2.0",
        "dearpygui>=2.0.0",
        "psutil>=5.9.0",
        "scapy>=2.5.0",
        "python-nmap>=0.7.1",
        "netifaces>=0.11.0",
        "requests>=2.31.0",
        "mac-vendor-lookup>=0.1.15",
        "pyudev>=0.24.0",
    ]

    print(f"{Colors.CYAN}Installiere/aktualisiere Python-Pakete...{Colors.END}")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", "--upgrade", "pip"],
            check=False,
        )
        for dep in deps:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", dep], check=False
            )
        print(f"{Colors.GREEN}✓ Python-Pakete installiert{Colors.END}")
    except Exception as e:
        print(f"{Colors.RED}✗ Fehler: {e}{Colors.END}")


def test_dearpygui():
    """Test if Dear PyGui works"""
    print(f"\n{Colors.YELLOW}[DEAR PYGUI KOMPATIBILITÄTSTEST]{Colors.END}")

    try:
        # Try to import and create a minimal context
        import dearpygui.dearpygui as dpg

        # Test OpenGL context
        dpg.create_context()

        # If we get here, it works
        print(f"{Colors.GREEN}✓ Dear PyGui funktioniert!{Colors.END}")
        dpg.destroy_context()
        return True

    except Exception as e:
        print(f"{Colors.RED}✗ Dear PyGui Fehler: {e}{Colors.END}")
        print(f"{Colors.YELLOW}→ Fallback auf CustomTkinter{Colors.END}")
        return False


def test_customtkinter():
    """Test if CustomTkinter works"""
    print(f"\n{Colors.YELLOW}[CUSTOMTKINTER TEST]{Colors.END}")

    try:
        import customtkinter

        print(f"{Colors.GREEN}✓ CustomTkinter funktioniert!{Colors.END}")
        return True
    except Exception as e:
        print(f"{Colors.RED}✗ CustomTkinter Fehler: {e}{Colors.END}")
        return False


def launch_dearpygui():
    """Launch Dear PyGui version"""
    print(
        f"\n{Colors.CYAN}{Colors.BOLD}Starte ANIME COCKPIT EDITION (GPU-Accelerated)...{Colors.END}"
    )
    time.sleep(1)

    try:
        import main_anime

        app = main_anime.CyberGuardianAnime()
        app.run()
    except Exception as e:
        print(f"{Colors.RED}Fehler beim Start: {e}{Colors.END}")
        print(f"{Colors.YELLOW}Versuche Fallback...{Colors.END}")
        launch_customtkinter()


def launch_customtkinter():
    """Launch CustomTkinter version"""
    print(f"\n{Colors.CYAN}{Colors.BOLD}Starte CLASSIC EDITION...{Colors.END}")
    time.sleep(1)

    try:
        import main

        # main.py uses ctk.CTk, so we need to handle that differently
        # For now, just show a message
        print(f"{Colors.GREEN}✓ Classic Edition startet...{Colors.END}")
        os.system(f"{sys.executable} main.py")
    except Exception as e:
        print(f"{Colors.RED}Fehler: {e}{Colors.END}")


def main():
    print_header()

    # Check Python version
    if sys.version_info < (3, 8):
        print(f"{Colors.RED}✗ Python 3.8+ benötigt!{Colors.END}")
        sys.exit(1)

    print(f"{Colors.CYAN}Python Version: {platform.python_version()}{Colors.END}")
    print(
        f"{Colors.CYAN}Betriebssystem: {platform.system()} {platform.release()}{Colors.END}"
    )

    # Install dependencies
    install_python_deps()
    install_system_deps()

    # Test GUIs
    dearpygui_works = test_dearpygui()
    customtkinter_works = test_customtkinter()

    # Choose best version
    print(f"\n{Colors.MAGENTA}{Colors.BOLD}" + "=" * 60 + f"{Colors.END}")

    if dearpygui_works:
        print(
            f"{Colors.GREEN}{Colors.BOLD}✓ ANIME COCKPIT EDITION verfügbar{Colors.END}"
        )
        print(
            f"{Colors.CYAN}Features: GPU-Accelerated, 60 FPS, Neon Glow Effects{Colors.END}"
        )

        choice = input(
            f"\n{Colors.YELLOW}Möchtest du die ANIME COCKPIT EDITION starten? (j/N): {Colors.END}"
        ).lower()

        if choice in ["j", "ja", "y", "yes"]:
            launch_dearpygui()
        else:
            if customtkinter_works:
                launch_customtkinter()
            else:
                print(f"{Colors.RED}✗ Keine GUI verfügbar{Colors.END}")

    elif customtkinter_works:
        print(
            f"{Colors.YELLOW}ANIME COCKPIT nicht verfügbar (OpenGL Fehler){Colors.END}"
        )
        print(f"{Colors.GREEN}Starte CLASSIC EDITION...{Colors.END}")
        launch_customtkinter()

    else:
        print(f"{Colors.RED}✗ Keine GUI-Bibliothek funktioniert!{Colors.END}")
        print(f"{Colors.YELLOW}Versuche Installation zu reparieren...{Colors.END}")
        install_python_deps()
        print(f"{Colors.CYAN}Bitte erneut starten.{Colors.END}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Abgebrochen{Colors.END}")
        sys.exit(0)
    except Exception as e:
        print(f"\n{Colors.RED}Kritischer Fehler: {e}{Colors.END}")
        sys.exit(1)
