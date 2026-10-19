#!/usr/bin/env python3
"""Prepare/boot an opt-in, disposable QEMU cloud-image lab (no downloads)."""
from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("CYBERGUARDIAN_VM_LAB_DIR", Path.home() / ".cyberguardian" / "vm-lab"))


def need(binary):
    found = shutil.which(binary)
    if not found:
        raise SystemExit(f"Fehlt: {binary}. QEMU + cloud-image-utils zuerst auf dem Host installieren.")
    return found


def prepare(image):
    source = Path(image).expanduser().resolve()
    if not source.is_file():
        raise SystemExit("Cloud-Image nicht gefunden. Nur ein selbst beschafftes, vertrauenswürdiges Debian/Ubuntu-Cloud-Image verwenden.")
    qemu_img, cloud_localds = need("qemu-img"), need("cloud-localds")
    previous_umask = os.umask(0o077)  # the seed ISO embeds the shared lab key
    try:
        DATA.mkdir(parents=True, exist_ok=True, mode=0o700)
        DATA.chmod(0o700)
        disk, seed = DATA / "guest.qcow2", DATA / "seed.iso"
        if disk.exists() or seed.exists() or (DATA / "secret").exists():
            raise SystemExit("VM-Lab bereits vorbereitet. Bestehende Daten werden nicht überschrieben.")
        key = secrets.token_hex(32)
        key_path = DATA / "secret"
        with open(key_path, "x", encoding="ascii", opener=lambda path, flags: os.open(path, flags, 0o600)) as handle:
            handle.write(key + "\n")
        unit = (
            '[Unit]\n'
            'Description=CyberGuardian isolated guest HTTP sensor\n'
            'After=network.target\n'
            '[Service]\n'
            'Type=simple\n'
            'User=cyberguardian\n'
            'ExecStart=/usr/bin/python3 /opt/cyberguardian/guest_sensor.py\n'
            'Restart=on-failure\n'
            'NoNewPrivileges=yes\n'
            'ProtectSystem=strict\n'
            'ProtectHome=yes\n'
            'PrivateTmp=yes\n'
            'CapabilityBoundingSet=\n'
            '[Install]\n'
            'WantedBy=multi-user.target\n'
        )
        def entry(path, content, permissions, owner="root:root"):
            return {"path": path, "encoding": "b64", "content": base64.b64encode(content.encode()).decode(),
                    "permissions": permissions, "owner": owner}
        cloud_config = {
            "users": ["default", {"name": "cyberguardian", "system": True, "shell": "/usr/sbin/nologin"}],
            "ssh_pwauth": False, "disable_root": True,
            "write_files": [
                entry("/opt/cyberguardian/guest_sensor.py", (ROOT / "guest_sensor.py").read_text(), "0644"),
                entry("/etc/cyberguardian-lab.key", key + "\n", "0640", "root:cyberguardian"),
                entry("/etc/systemd/system/cyberguardian-sensor.service", unit, "0644"),
            ],
            "runcmd": [["systemctl", "daemon-reload"], ["systemctl", "enable", "--now", "cyberguardian-sensor.service"]],
        }
        user_data = DATA / "user-data"
        user_data.write_text("#cloud-config\n" + json.dumps(cloud_config) + "\n", encoding="utf-8")
        user_data.chmod(0o600)
        meta = DATA / "meta-data"
        meta.write_text("instance-id: cyberguardian-lab-v1\nlocal-hostname: guardian-lab\n", encoding="ascii")
        try:
            subprocess.run([qemu_img, "convert", "-f", "qcow2", "-O", "qcow2", str(source), str(disk)], check=True)
            subprocess.run([cloud_localds, str(seed), str(user_data), str(meta)], check=True)
        except (subprocess.CalledProcessError, OSError) as exc:
            raise SystemExit(f"Vorbereitung fehlgeschlagen: {exc}. Daten unter {DATA} manuell prüfen.") from exc
        print(f"Vorbereitet: {DATA}. Jetzt: python3 lab/vm.py run")

    finally:
        os.umask(previous_umask)


def run():
    qemu = need("qemu-system-x86_64")
    disk, seed = DATA / "guest.qcow2", DATA / "seed.iso"
    if not disk.is_file() or not seed.is_file() or not (DATA / "secret").is_file():
        raise SystemExit("VM fehlt. Zuerst: python3 lab/vm.py prepare --image /pfad/zum/cloud-image.qcow2")
    # No guest port exposed to LAN; no guest access to outside networks.
    args = [qemu, "-m", "1024", "-smp", "1", "-snapshot", "-display", "none",
            "-serial", "mon:stdio", "-drive", f"file={disk},format=qcow2,if=virtio",
            "-drive", f"file={seed},format=raw,if=virtio,readonly=on",
            "-netdev", "user,id=lab,restrict=on,hostfwd=tcp:127.0.0.1:18081-:8081",
            "-device", "virtio-net-pci,netdev=lab"]
    if Path("/dev/kvm").exists() and os.access("/dev/kvm", os.R_OK | os.W_OK):
        args.extend(["-accel", "kvm"])
    else:
        args.extend(["-accel", "tcg"])
    print("VM startet ohne Gast-Internet; Port 18081 nur auf Host-Loopback. Beenden: Ctrl+C.", flush=True)
    try:
        subprocess.run(args, check=True)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "run"])
    parser.add_argument("--image", help="Lokal bereitgestelltes qcow2 Debian/Ubuntu cloud image")
    args = parser.parse_args()
    if args.action == "prepare":
        if not args.image:
            parser.error("prepare benötigt --image")
        prepare(args.image)
    else:
        run()
