"""
Scheduler Module for Automated Driver Scans and Updates
Provides scheduled task creation and management using Windows Task Scheduler.
"""

import os
import subprocess
import logging
from typing import Optional, List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class SchedulerManager:
    """Manages Windows Task Scheduler for automated driver operations."""

    @staticmethod
    def create_daily_scan_task(
        task_name: str = "DriverUpdater_DailyScan",
        time_str: str = "09:00",
        script_path: Optional[str] = None,
        arguments: str = "--scan --auto-report"
    ) -> tuple[bool, str]:
        """
        Creates a daily scheduled task to scan for drivers.
        
        Args:
            task_name: Name of the scheduled task
            time_str: Time in HH:MM format (24-hour)
            script_path: Path to main.py (uses current script if None)
            arguments: Command line arguments
        """
        if not script_path:
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))

        python_exe = subprocess.check_output(
            ["where", "python"],
            shell=True,
            text=True
        ).strip().split("\n")[0].strip()

        # Format: schtasks /Create /TN "TaskName" /TR "command" /SC DAILY /ST HH:MM /RL HIGHEST /F
        cmd = [
            "schtasks.exe", "/Create",
            "/TN", task_name,
            "/TR", f'"{python_exe}" "{script_path}" {arguments}',
            "/SC", "DAILY",
            "/ST", time_str,
            "/RL", "HIGHEST",
            "/F"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

            if result.returncode == 0:
                return True, f"Scheduled task '{task_name}' created successfully for {time_str} daily."
            else:
                return False, f"Failed to create task: {result.stderr or result.stdout}"

        except Exception as e:
            logger.error(f"Error creating scheduled task: {e}")
            return False, str(e)

    @staticmethod
    def create_weekly_update_task(
        task_name: str = "DriverUpdater_WeeklyCheck",
        day_of_week: str = "SUNDAY",
        time_str: str = "10:00",
        script_path: Optional[str] = None,
        arguments: str = "--check-updates --auto-install"
    ) -> tuple[bool, str]:
        """
        Creates a weekly scheduled task to check and install driver updates.
        
        Args:
            task_name: Name of the scheduled task
            day_of_week: Day name (MONDAY, TUESDAY, etc.)
            time_str: Time in HH:MM format
            script_path: Path to main.py
            arguments: Command line arguments
        """
        if not script_path:
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))

        python_exe = subprocess.check_output(
            ["where", "python"],
            shell=True,
            text=True
        ).strip().split("\n")[0].strip()

        cmd = [
            "schtasks.exe", "/Create",
            "/TN", task_name,
            "/TR", f'"{python_exe}" "{script_path}" {arguments}',
            "/SC", "WEEKLY",
            "/D", day_of_week.upper(),
            "/ST", time_str,
            "/RL", "HIGHEST",
            "/F"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

            if result.returncode == 0:
                return True, f"Scheduled task '{task_name}' created successfully for every {day_of_week} at {time_str}."
            else:
                return False, f"Failed to create task: {result.stderr or result.stdout}"

        except Exception as e:
            logger.error(f"Error creating scheduled task: {e}")
            return False, str(e)

    @staticmethod
    def list_driver_tasks() -> List[Dict]:
        """
        Lists all driver-related scheduled tasks.
        """
        tasks = []

        try:
            # Query tasks with XML output for detailed info
            cmd = ["schtasks.exe", "/Query", "/FO", "CSV", "/V"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                # Skip header
                for line in lines[1:]:
                    if "DriverUpdater" in line or "Driver" in line:
                        # Parse CSV
                        parts = line.split(",")
                        if len(parts) >= 13:
                            task_info = {
                                "name": parts[0].strip('"'),
                                "status": parts[1].strip('"'),
                                "next_run": parts[7].strip('"'),
                                "last_run": parts[8].strip('"'),
                                "last_result": parts[9].strip('"'),
                                "command": parts[12].strip('"')
                            }
                            tasks.append(task_info)

        except Exception as e:
            logger.error(f"Error listing tasks: {e}")

        return tasks

    @staticmethod
    def delete_task(task_name: str) -> tuple[bool, str]:
        """
        Deletes a scheduled task.
        """
        cmd = ["schtasks.exe", "/Delete", "/TN", task_name, "/F"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

            if result.returncode == 0:
                return True, f"Task '{task_name}' deleted successfully."
            else:
                return False, f"Failed to delete task: {result.stderr or result.stdout}"

        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            return False, str(e)

    @staticmethod
    def run_task_now(task_name: str) -> tuple[bool, str]:
        """
        Triggers a scheduled task to run immediately.
        """
        cmd = ["schtasks.exe", "/Run", "/TN", task_name]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

            if result.returncode == 0:
                return True, f"Task '{task_name}' triggered successfully."
            else:
                return False, f"Failed to trigger task: {result.stderr or result.stdout}"

        except Exception as e:
            logger.error(f"Error running task: {e}")
            return False, str(e)

    @staticmethod
    def get_task_info(task_name: str) -> Optional[Dict]:
        """
        Gets detailed information about a specific task.
        """
        try:
            cmd = ["schtasks.exe", "/Query", "/TN", task_name, "/FO", "CSV", "/V"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                if len(lines) >= 2:
                    parts = lines[1].split(",")
                    if len(parts) >= 13:
                        return {
                            "name": parts[0].strip('"'),
                            "status": parts[1].strip('"'),
                            "logon_mode": parts[2].strip('"'),
                            "next_run": parts[7].strip('"'),
                            "last_run": parts[8].strip('"'),
                            "last_result": parts[9].strip('"'),
                            "folder": parts[10].strip('"'),
                            "task_to_run": parts[12].strip('"'),
                            "start_in": parts[13].strip('"') if len(parts) > 13 else ""
                        }
        except Exception as e:
            logger.error(f"Error getting task info: {e}")

        return None

    @staticmethod
    def enable_auto_updates(
        backup_first: bool = True,
        create_restore_point: bool = True
    ) -> tuple[bool, str]:
        """
        Enables fully automated update workflow with safety checks.
        Creates both backup and update tasks.
        """
        script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "main.py"))

        # Create daily backup task
        backup_args = "--backup-auto"
        if create_restore_point:
            backup_args += " --with-restore-point"

        ok1, msg1 = SchedulerManager.create_daily_scan_task(
            task_name="DriverUpdater_AutoBackup",
            time_str="08:00",
            script_path=script_path,
            arguments=backup_args
        )

        if not ok1:
            return False, f"Failed to create backup task: {msg1}"

        # Create weekly update task
        update_args = "--check-updates --auto-install-safe"
        if backup_first:
            update_args += " --backup-before-update"

        ok2, msg2 = SchedulerManager.create_weekly_update_task(
            task_name="DriverUpdater_AutoUpdate",
            day_of_week="SUNDAY",
            time_str="03:00",
            script_path=script_path,
            arguments=update_args
        )

        if not ok2:
            return False, f"Failed to create update task: {msg2}"

        return True, "Automated update workflow enabled successfully!"


if __name__ == "__main__":
    print("Testing Scheduler Manager...")

    # List existing tasks
    print("\n=== Existing Driver Tasks ===")
    tasks = SchedulerManager.list_driver_tasks()
    if tasks:
        for task in tasks:
            print(f"- {task['name']}: {task['status']} | Next Run: {task['next_run']}")
    else:
        print("No driver-related scheduled tasks found.")

    # Test creating a daily scan task
    print("\n=== Creating Daily Scan Task ===")
    ok, msg = SchedulerManager.create_daily_scan_task(
        task_name="DriverUpdater_TestScan",
        time_str="23:59",  # Set to near-midnight for testing
        arguments="--scan --quiet"
    )
    print(msg)

    # Get task info
    if ok:
        print("\n=== Task Details ===")
        info = SchedulerManager.get_task_info("DriverUpdater_TestScan")
        if info:
            for key, value in info.items():
                print(f"{key}: {value}")

        # Clean up test task
        print("\n=== Deleting Test Task ===")
        ok2, msg2 = SchedulerManager.delete_task("DriverUpdater_TestScan")
        print(msg2)
