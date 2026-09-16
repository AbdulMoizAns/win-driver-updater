"""
Driver Backup and Restore Module
Uses pnputil /export-driver to safely backup and restore third-party drivers.
"""

import os
import subprocess
import logging
from datetime import datetime
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class DriverBackupManager:
    """Manages driver export, restoration, and Windows system restore points."""

    @staticmethod
    def create_driver_backup(target_dir: Optional[str] = None) -> Tuple[bool, str]:
        """
        Exports all 3rd-party installed drivers to target_dir using pnputil /export-driver.
        """
        if not target_dir:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target_dir = os.path.join(os.path.expanduser("~"), "DriverBackups", f"Backup_{timestamp}")

        os.makedirs(target_dir, exist_ok=True)

        cmd = ["pnputil.exe", "/export-driver", "*", target_dir]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            if res.returncode == 0 or "Exported driver package" in res.stdout:
                # Count files exported
                inf_files = [f for f in os.listdir(target_dir) if f.lower().endswith(".inf")]
                return True, f"Successfully backed up drivers to: {target_dir} ({len(inf_files)} driver packages exported)"
            else:
                return False, f"Export failed: {res.stderr or res.stdout}"
        except Exception as e:
            logger.error(f"Failed to create driver backup: {e}")
            return False, str(e)

    @staticmethod
    def restore_driver_backup(backup_dir: str) -> Tuple[bool, str]:
        """
        Installs drivers from a backup folder using pnputil /add-driver ... /subdirs /install.
        """
        if not os.path.exists(backup_dir):
            return False, f"Backup directory does not exist: {backup_dir}"

        inf_pattern = os.path.join(backup_dir, "*.inf")
        cmd = ["pnputil.exe", "/add-driver", inf_pattern, "/subdirs", "/install"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            if res.returncode in (0, 3010): # 3010 = success, reboot required
                reboot_note = " (System reboot required)" if res.returncode == 3010 else ""
                return True, f"Drivers restored successfully{reboot_note}."
            else:
                return False, f"Restore failed: {res.stderr or res.stdout}"
        except Exception as e:
            logger.error(f"Failed to restore driver backup: {e}")
            return False, str(e)

    @staticmethod
    def create_system_restore_point(description: str = "Pre-Driver-Update-Checkpoint") -> Tuple[bool, str]:
        """
        Attempts to create a Windows System Restore Point using PowerShell Checkpoint-Computer.
        Note: Requires Administrator privileges and System Protection turned on for the OS drive.
        """
        ps_cmd = (
            f"Checkpoint-Computer -Description '{description}' "
            "-RestorePointType 'DEVICE_DRIVER_INSTALL' -ErrorAction Stop"
        )
        try:
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            if res.returncode == 0:
                return True, f"Restore point '{description}' created successfully."
            else:
                return False, f"Restore point creation error: {res.stderr.strip()}"
        except Exception as e:
            return False, str(e)
