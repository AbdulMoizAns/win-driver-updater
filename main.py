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

# Enable Windows Per-Monitor High-DPI Awareness (V2) & AppUserModelID for Taskbar Icon
if sys.platform == "win32":
    try:
        myappid = "abdulmoizans.windriverupdater.gui.1.0"
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
    except Exception:
        pass

    try:
        ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except Exception:
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
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
from core.safety import SafetyManager
from core.reporter import ReportManager, OperationLogger
from core.scheduler import SchedulerManager


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
    parser = argparse.ArgumentParser(description="Windows Driver Updater - Professional Edition")
    parser.add_argument("--scan", action="store_true", help="Perform a hardware scan and list drivers in terminal")
    parser.add_argument("--backup", type=str, help="Export all installed third-party drivers to specified folder")
    parser.add_argument("--check-updates", action="store_true", help="Check online repositories for available updates")
    parser.add_argument("--gui", action="store_true", help="Launch the Desktop GUI interface (default)")
    parser.add_argument("--elevate", action="store_true", help="Request administrator privileges on startup")
    
    # New advanced features
    parser.add_argument("--health-check", action="store_true", help="Run system health check before operations")
    parser.add_argument("--report", type=str, choices=["json", "html", "txt"], help="Generate scan report in specified format")
    parser.add_argument("--rollback", type=str, help="Restore driver from rollback point (provide folder path)")
    parser.add_argument("--list-rollbacks", action="store_true", help="List all available rollback points")
    parser.add_argument("--schedule-daily", type=str, metavar="HH:MM", help="Schedule daily scan at specified time")
    parser.add_argument("--schedule-weekly", nargs=2, metavar=("DAY", "HH:MM"), help="Schedule weekly update check (e.g., SUNDAY 10:00)")
    parser.add_argument("--list-tasks", action="store_true", help="List all scheduled driver tasks")
    parser.add_argument("--auto-update-enable", action="store_true", help="Enable fully automated update workflow")
    parser.add_argument("--verify-driver", type=str, help="Verify digital signature of a driver INF file")

    args = parser.parse_args()

    # Initialize logger
    logger = OperationLogger()

    if args.elevate and not is_admin():
        request_elevation()

    # Health check option
    if args.health_check:
        print("=" * 70)
        print("        SYSTEM HEALTH CHECK")
        print("=" * 70)
        health = SafetyManager.check_system_health()
        print(f"\nOverall Status: {'✅ Healthy' if health['is_healthy'] else '⚠️ Issues Detected'}")
        print(f"Disk Space OK: {'Yes' if health['disk_space_ok'] else 'No - Low Space'}")
        print(f"Restore Points Enabled: {'Yes' if health['restore_points_enabled'] else 'No'}")
        print(f"Pending Reboot: {'Yes' if health['pending_reboot'] else 'No'}")
        
        if health['warnings']:
            print("\n⚠️ Warnings:")
            for w in health['warnings']:
                print(f"  - {w}")
        
        if health['errors']:
            print("\n❌ Errors:")
            for e in health['errors']:
                print(f"  - {e}")
        
        print("\n" + "=" * 70)
        return

    # Verify driver signature
    if args.verify_driver:
        print(f"[*] Verifying driver signature: {args.verify_driver}")
        sig_info = SafetyManager.verify_driver_signature(args.verify_driver)
        print(f"\nSignature Status: {'✅ Valid' if sig_info.is_valid else '❌ Invalid/Unsigned'}")
        print(f"Is Digitally Signed: {'Yes' if sig_info.is_signed else 'No'}")
        print(f"Signer: {sig_info.signer_name or 'Unknown'}")
        print(f"WHQL Certified: {'Yes' if sig_info.is_whql else 'No'}")
        if sig_info.error_message:
            print(f"Error: {sig_info.error_message}")
        return

    # List rollback points
    if args.list_rollbacks:
        print("=" * 70)
        print("        AVAILABLE ROLLBACK POINTS")
        print("=" * 70)
        backup_dir = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "DriverBackups")
        rollbacks = SafetyManager.get_all_rollback_points(backup_dir)
        
        if rollbacks:
            for i, rb in enumerate(rollbacks, 1):
                print(f"\n{i}. Timestamp: {rb['timestamp']}")
                print(f"   Device: {rb['device_name']}")
                print(f"   Version Change: {rb['old_driver_version']} → {rb['new_driver_version']}")
                print(f"   Backup Path: {rb.get('folder_path', 'N/A')}")
        else:
            print("\nNo rollback points found.")
        print("\n" + "=" * 70)
        return

    # Execute rollback
    if args.rollback:
        if not is_admin():
            print("❌ Administrator rights required for rollback operation.")
            request_elevation()
        
        print(f"[*] Executing rollback from: {args.rollback}")
        ok, msg = SafetyManager.execute_rollback(args.rollback)
        if ok:
            print(f"[+] SUCCESS: {msg}")
        else:
            print(f"[-] ERROR: {msg}")
        return

    # Schedule daily scan
    if args.schedule_daily:
        print(f"[*] Creating daily scan task at {args.schedule_daily}...")
        ok, msg = SchedulerManager.create_daily_scan_task(time_str=args.schedule_daily)
        if ok:
            print(f"[+] {msg}")
        else:
            print(f"[-] ERROR: {msg}")
        return

    # Schedule weekly update
    if args.schedule_weekly:
        day, time = args.schedule_weekly
        print(f"[*] Creating weekly update task for {day} at {time}...")
        ok, msg = SchedulerManager.create_weekly_update_task(day_of_week=day, time_str=time)
        if ok:
            print(f"[+] {msg}")
        else:
            print(f"[-] ERROR: {msg}")
        return

    # List scheduled tasks
    if args.list_tasks:
        print("=" * 70)
        print("        SCHEDULED DRIVER TASKS")
        print("=" * 70)
        tasks = SchedulerManager.list_driver_tasks()
        
        if tasks:
            for task in tasks:
                status_icon = "✅" if task['status'] == "Ready" else "⏸️"
                print(f"\n{status_icon} {task['name']}")
                print(f"   Status: {task['status']}")
                print(f"   Next Run: {task['next_run']}")
                print(f"   Last Run: {task['last_run']} (Result: {task['last_result']})")
        else:
            print("\nNo scheduled tasks found.")
        print("\n" + "=" * 70)
        return

    # Enable auto-update workflow
    if args.auto_update_enable:
        if not is_admin():
            print("❌ Administrator rights required.")
            request_elevation()
        
        print("[*] Enabling automated update workflow...")
        ok, msg = SchedulerManager.enable_auto_updates()
        if ok:
            print(f"[+] {msg}")
        else:
            print(f"[-] ERROR: {msg}")
        return

    if args.scan:
        run_cli_scan()
    elif args.backup:
        run_cli_backup(args.backup)
    elif args.report:
        # Scan and generate report
        print("[*] Scanning devices for report generation...")
        devs = DriverScanner.scan_all_devices()
        print(f"[+] Found {len(devs)} devices. Generating {args.report.upper()} report...")
        
        report_mgr = ReportManager()
        report_path = report_mgr.generate_scan_report(devs, format=args.report)
        print(f"[+] Report saved to: {report_path}")
        
    elif args.check_updates:
        print("[*] Scanning system devices...")
        devs = DriverScanner.scan_all_devices()
        print(f"[+] Found {len(devs)} devices. Checking Microsoft Update Catalog...")
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
