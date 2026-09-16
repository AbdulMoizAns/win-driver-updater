"""
Windows Driver Updater - Main Entry Point
Supports both Interactive GUI mode and CLI Automation mode.
"""

import sys
import os
import argparse
import ctypes
import logging

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from core.scanner import DriverScanner
from core.fetcher import DriverFetcher
from core.backup import DriverBackupManager
from core.installer import DriverInstaller


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_elevation():
    """Relaunches the current script as Administrator if not already elevated."""
    if not is_admin():
        script = os.path.abspath(sys.argv[0])
        params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
        if ret > 32:
            sys.exit(0)


def run_cli_scan():
    print("=" * 70)
    print("        WINDOWS HARDWARE & DRIVER SCANNER")
    print("=" * 70)
    devices = DriverScanner.scan_all_devices()
    print(f"\n[+] Total devices detected: {len(devices)}\n")

    # Group by category
    categories = {}
    for d in devices:
        categories.setdefault(d.device_class, []).append(d)

    for cat, devs in sorted(categories.items()):
        print(f"\n📁 [{cat}] ({len(devs)} devices)")
        for d in devs:
            status_icon = "⚠️ [PROBLEM]" if d.has_problem else "✅"
            print(f"  {status_icon} {d.name}")
            print(f"     Driver: {d.current_driver_version} ({d.current_driver_date}) | Provider: {d.provider_name}")
            if d.matching_device_id:
                print(f"     Hardware ID: {d.matching_device_id}")

    print("\n" + "=" * 70)
    print("Scan completed successfully.")


def run_cli_backup(target_path: str):
    print(f"[*] Starting driver backup to: {target_path}...")
    ok, msg = DriverBackupManager.create_driver_backup(target_path)
    if ok:
        print(f"[+] SUCCESS: {msg}")
    else:
        print(f"[-] ERROR: {msg}")


def main():
    parser = argparse.ArgumentParser(description="Windows Driver Updater")
    parser.add_argument("--scan", action="store_true", help="Perform a hardware scan and list drivers in terminal")
    parser.add_argument("--backup", type=str, help="Export all installed third-party drivers to specified folder")
    parser.add_argument("--check-updates", action="store_true", help="Check online repositories for available updates")
    parser.add_argument("--gui", action="store_true", help="Launch the Desktop GUI interface (default)")
    parser.add_argument("--elevate", action="store_true", help="Request administrator privileges on startup")

    args = parser.parse_args()

    if args.elevate and not is_admin():
        request_elevation()

    if args.scan:
        run_cli_scan()
    elif args.backup:
        run_cli_backup(args.backup)
    elif args.check_updates:
        print("[*] Scanning system devices...")
        devs = DriverScanner.scan_all_devices()
        print(f"[+] Found {len(devs)} devices. Checking Microsoft Update Catalog for network & display adapters...")
        critical = [d for d in devs if d.device_class.lower() in ("net", "display", "media") and d.matching_device_id][:5]
        for d in critical:
            print(f"[*] Checking {d.name} ({d.matching_device_id})...")
            cand = DriverFetcher.check_updates_for_device(d.matching_device_id, d.current_driver_version, d.current_driver_date)
            if cand:
                print(f"  --> ✨ NEW UPDATE: {cand.version} ({cand.date_str}) | {cand.title}")
            else:
                print("  --> Driver is up to date.")
    else:
        # Default to GUI
        from ui.app_gui import launch_gui
        launch_gui()


if __name__ == "__main__":
    main()
