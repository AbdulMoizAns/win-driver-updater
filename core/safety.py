"""
Advanced Safety & Verification Module
Provides driver signature verification, rollback capabilities, and safety checks.
"""

import os
import subprocess
import logging
import hashlib
from typing import Tuple, List, Optional, Dict
from datetime import datetime
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DriverSignatureInfo:
    """Stores driver signature verification results."""
    is_signed: bool
    signer_name: str
    is_whql: bool
    is_valid: bool
    error_message: str = ""


@dataclass
class RollbackPoint:
    """Represents a driver rollback checkpoint."""
    timestamp: str
    device_instance_id: str
    device_name: str
    old_driver_version: str
    new_driver_version: str
    backup_inf_path: str
    restore_point_id: Optional[str] = None


class SafetyManager:
    """Manages driver safety verification, rollback, and system integrity checks."""

    @staticmethod
    def verify_driver_signature(inf_path: str) -> DriverSignatureInfo:
        """
        Verifies if a driver package is digitally signed and WHQL certified.
        Uses PowerShell to check driver signature status.
        """
        if not os.path.exists(inf_path):
            return DriverSignatureInfo(
                is_signed=False,
                signer_name="",
                is_whql=False,
                is_valid=False,
                error_message="INF file not found"
            )

        ps_cmd = f"""
        $infPath = "{inf_path}"
        try {{
            $pnputil = pnputil.exe /enum-drivers /driver "$infPath" 2>&1
            $isSigned = $pnputil -match "Digital Signer"
            $signer = ""
            $isWHQL = $false
            
            if ($isSigned) {{
                $signerMatch = $pnputil | Select-String "Digital Signer:\\s*(.+)" 
                if ($signerMatch) {{
                    $signer = $signerMatch.Matches.Groups[1].Value.Trim()
                }}
                $isWHQL = $pnputil -match "Microsoft Windows"
            }}
            
            [PSCustomObject]@{{
                IsSigned = $isSigned
                Signer = $signer
                IsWHQL = $isWHQL
            }} | ConvertTo-Json -Compress
        }} catch {{
            [PSCustomObject]@{{
                IsSigned = $false
                Signer = ""
                IsWHQL = $false
                Error = $_.Exception.Message
            }} | ConvertTo-Json -Compress
        }}
        """

        try:
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

            import json
            data = json.loads(result.stdout.strip())

            return DriverSignatureInfo(
                is_signed=data.get("IsSigned", False),
                signer_name=data.get("Signer", ""),
                is_whql=data.get("IsWHQL", False),
                is_valid=data.get("IsSigned", False) and not data.get("Error"),
                error_message=data.get("Error", "")
            )
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return DriverSignatureInfo(
                is_signed=False,
                signer_name="",
                is_whql=False,
                is_valid=False,
                error_message=str(e)
            )

    @staticmethod
    def create_rollback_point(
        device_instance_id: str,
        device_name: str,
        old_version: str,
        new_version: str,
        backup_dir: str
    ) -> Optional[RollbackPoint]:
        """
        Creates a rollback checkpoint before driver installation.
        Saves current driver state for potential rollback.
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            rollback_folder = os.path.join(backup_dir, f"Rollback_{timestamp}")
            os.makedirs(rollback_folder, exist_ok=True)

            # Export current driver using pnputil
            cmd = ["pnputil.exe", "/export-driver", "*", rollback_folder]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

            # Find the specific driver INF for this device
            backup_inf = ""
            if result.returncode == 0:
                inf_files = [f for f in os.listdir(rollback_folder) if f.lower().endswith(".inf")]
                # Try to find matching driver (simplified - in production would match hardware ID)
                if inf_files:
                    backup_inf = os.path.join(rollback_folder, inf_files[0])

            rollback_point = RollbackPoint(
                timestamp=timestamp,
                device_instance_id=device_instance_id,
                device_name=device_name,
                old_driver_version=old_version,
                new_driver_version=new_version,
                backup_inf_path=backup_inf
            )

            # Save metadata
            metadata_file = os.path.join(rollback_folder, "rollback_metadata.json")
            import json
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump({
                    "timestamp": rollback_point.timestamp,
                    "device_instance_id": rollback_point.device_instance_id,
                    "device_name": rollback_point.device_name,
                    "old_driver_version": rollback_point.old_driver_version,
                    "new_driver_version": rollback_point.new_driver_version,
                    "backup_inf_path": rollback_point.backup_inf_path
                }, f, indent=2)

            logger.info(f"Created rollback point: {timestamp} for {device_name}")
            return rollback_point

        except Exception as e:
            logger.error(f"Failed to create rollback point: {e}")
            return None

    @staticmethod
    def execute_rollback(rollback_folder: str) -> Tuple[bool, str]:
        """
        Restores drivers from a rollback checkpoint.
        """
        if not os.path.exists(rollback_folder):
            return False, f"Rollback folder not found: {rollback_folder}"

        # Load metadata
        metadata_file = os.path.join(rollback_folder, "rollback_metadata.json")
        if not os.path.exists(metadata_file):
            return False, "Rollback metadata not found"

        import json
        try:
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
        except Exception as e:
            return False, f"Failed to read rollback metadata: {e}"

        backup_inf = metadata.get("backup_inf_path", "")
        if not backup_inf or not os.path.exists(backup_inf):
            # Try to find any INF in the folder
            inf_files = [f for f in os.listdir(rollback_folder) if f.lower().endswith(".inf")]
            if not inf_files:
                return False, "No driver backup files found in rollback folder"
            backup_inf = os.path.join(rollback_folder, inf_files[0])

        # Restore driver using pnputil
        cmd = ["pnputil.exe", "/add-driver", backup_inf, "/install", "/force"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

            if result.returncode in (0, 3010):
                reboot_note = " (Reboot required)" if result.returncode == 3010 else ""
                return True, f"Driver rolled back successfully{reboot_note}"
            else:
                return False, f"Rollback failed: {result.stderr or result.stdout}"

        except Exception as e:
            logger.error(f"Rollback execution failed: {e}")
            return False, str(e)

    @staticmethod
    def get_all_rollback_points(base_dir: str) -> List[Dict]:
        """
        Lists all available rollback points.
        """
        rollback_points = []

        if not os.path.exists(base_dir):
            return rollback_points

        for folder_name in os.listdir(base_dir):
            if folder_name.startswith("Rollback_"):
                folder_path = os.path.join(base_dir, folder_name)
                metadata_file = os.path.join(folder_path, "rollback_metadata.json")

                if os.path.exists(metadata_file):
                    try:
                        import json
                        with open(metadata_file, "r", encoding="utf-8") as f:
                            metadata = json.load(f)
                        metadata["folder_path"] = folder_path
                        rollback_points.append(metadata)
                    except:
                        pass

        # Sort by timestamp descending
        rollback_points.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return rollback_points

    @staticmethod
    def check_system_health() -> Dict[str, any]:
        """
        Performs pre-installation system health checks.
        """
        health_status = {
            "is_healthy": True,
            "disk_space_ok": True,
            "restore_points_enabled": False,
            "pending_reboot": False,
            "warnings": [],
            "errors": []
        }

        # Check disk space (require at least 500MB free)
        try:
            import shutil
            total, used, free = shutil.disk_usage("C:\\")
            free_mb = free / (1024 * 1024)
            if free_mb < 500:
                health_status["disk_space_ok"] = False
                health_status["warnings"].append(f"Low disk space: {free_mb:.0f}MB free")
        except Exception as e:
            health_status["errors"].append(f"Disk space check failed: {e}")

        # Check if restore points are enabled
        try:
            ps_cmd = "Get-ComputerRestorePoint -ErrorAction SilentlyContinue | Measure-Object | Select-Object -ExpandProperty Count"
            result = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            count = int(result.stdout.strip()) if result.stdout.strip().isdigit() else 0
            health_status["restore_points_enabled"] = count > 0
            if count == 0:
                health_status["warnings"].append("System Restore Points may be disabled")
        except Exception as e:
            health_status["errors"].append(f"Restore point check failed: {e}")

        # Check for pending reboot
        try:
            pending_reboot_keys = [
                r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Component Based Servicing\RebootPending",
                r"HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\WindowsUpdate\Auto Update\RebootRequired"
            ]
            for key in pending_reboot_keys:
                cmd = f'reg query "{key}" 2>nul'
                result = subprocess.run(cmd, shell=True, capture_output=True)
                if result.returncode == 0:
                    health_status["pending_reboot"] = True
                    health_status["warnings"].append("System reboot is pending")
                    break
        except Exception as e:
            health_status["errors"].append(f"Reboot check failed: {e}")

        # Determine overall health
        if health_status["errors"]:
            health_status["is_healthy"] = False

        return health_status

    @staticmethod
    def calculate_file_hash(file_path: str, algorithm: str = "sha256") -> str:
        """
        Calculates cryptographic hash of a driver file for integrity verification.
        """
        if not os.path.exists(file_path):
            return ""

        hash_func = getattr(hashlib, algorithm, hashlib.sha256)()

        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hash_func.update(chunk)
            return hash_func.hexdigest()
        except Exception as e:
            logger.error(f"Failed to calculate hash: {e}")
            return ""


if __name__ == "__main__":
    print("Testing Safety Manager...")

    # Test system health check
    print("\n=== System Health Check ===")
    health = SafetyManager.check_system_health()
    for key, value in health.items():
        print(f"{key}: {value}")

    # Test rollback point listing
    print("\n=== Rollback Points ===")
    temp_dir = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "DriverBackups")
    rollbacks = SafetyManager.get_all_rollback_points(temp_dir)
    if rollbacks:
        for rb in rollbacks:
            print(f"- {rb['timestamp']}: {rb['device_name']} ({rb['old_driver_version']} -> {rb['new_driver_version']})")
    else:
        print("No rollback points found.")
