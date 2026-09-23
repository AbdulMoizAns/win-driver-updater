"""
Advanced Reporting & Logging Module
Generates detailed HTML/text reports and maintains operation logs.
"""

import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class ScanReport:
    """Represents a complete scan report."""
    timestamp: str
    total_devices: int
    problem_devices: int
    updatable_devices: int
    categories: Dict[str, int]
    devices: List[Dict]


@dataclass
class UpdateReport:
    """Represents an update operation report."""
    timestamp: str
    device_name: str
    device_id: str
    old_version: str
    new_version: str
    status: str  # success, failed, skipped
    error_message: str = ""
    installation_time_seconds: float = 0.0


class ReportManager:
    """Manages generation of driver scan and update reports."""

    def __init__(self, reports_dir: Optional[str] = None):
        if not reports_dir:
            reports_dir = os.path.join(
                os.path.expanduser("~"),
                "DriverUpdaterReports"
            )
        self.reports_dir = reports_dir
        os.makedirs(reports_dir, exist_ok=True)

    def generate_scan_report(
        self,
        devices: List[any],
        format: str = "json"
    ) -> str:
        """
        Generates a comprehensive scan report in JSON, HTML, or TXT format.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Aggregate statistics
        total = len(devices)
        problems = sum(1 for d in devices if d.has_problem)
        updatable = sum(1 for d in devices if d.is_updatable)

        # Group by category
        categories = {}
        for d in devices:
            cat = d.device_class
            categories[cat] = categories.get(cat, 0) + 1

        # Convert devices to dict
        device_list = []
        for d in devices:
            device_dict = {
                "name": d.name,
                "category": d.device_class,
                "manufacturer": d.manufacturer,
                "current_version": d.current_driver_version,
                "current_date": d.current_driver_date,
                "provider": d.provider_name,
                "has_problem": d.has_problem,
                "problem_code": d.problem_code if d.has_problem else None,
                "is_updatable": d.is_updatable,
                "available_update": d.available_update_version,
                "hardware_id": d.matching_device_id
            }
            device_list.append(device_dict)

        report = ScanReport(
            timestamp=timestamp,
            total_devices=total,
            problem_devices=problems,
            updatable_devices=updatable,
            categories=categories,
            devices=device_list
        )

        # Save based on format
        if format.lower() == "json":
            return self._save_json_report(report, "scan_report", timestamp)
        elif format.lower() == "html":
            return self._save_html_scan_report(report, timestamp)
        elif format.lower() == "txt":
            return self._save_txt_scan_report(report, timestamp)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _save_json_report(self, report: ScanReport, prefix: str, timestamp: str) -> str:
        filename = f"{prefix}_{timestamp}.json"
        filepath = os.path.join(self.reports_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(asdict(report), f, indent=2)

        return filepath

    def _save_html_scan_report(self, report: ScanReport, timestamp: str) -> str:
        filename = f"scan_report_{timestamp}.html"
        filepath = os.path.join(self.reports_dir, filename)

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Driver Scan Report - {timestamp}</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin: 20px 0; }}
        .stat-card {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; text-align: center; }}
        .stat-card.warning {{ background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }}
        .stat-card.success {{ background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }}
        .stat-number {{ font-size: 2.5em; font-weight: bold; }}
        .stat-label {{ font-size: 0.9em; opacity: 0.9; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #3498db; color: white; position: sticky; top: 0; }}
        tr:hover {{ background-color: #f5f5f5; }}
        .status-ok {{ color: #27ae60; font-weight: bold; }}
        .status-problem {{ color: #e74c3c; font-weight: bold; }}
        .status-update {{ color: #3498db; font-weight: bold; }}
        .category-tag {{ display: inline-block; padding: 4px 8px; background: #ecf0f1; border-radius: 4px; font-size: 0.85em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 Driver Scan Report</h1>
        <p><strong>Generated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{report.total_devices}</div>
                <div class="stat-label">Total Devices</div>
            </div>
            <div class="stat-card {'warning' if report.problem_devices > 0 else ''}">
                <div class="stat-number">{report.problem_devices}</div>
                <div class="stat-label">Problem Devices</div>
            </div>
            <div class="stat-card {'success' if report.updatable_devices > 0 else ''}">
                <div class="stat-number">{report.updatable_devices}</div>
                <div class="stat-label">Updates Available</div>
            </div>
        </div>

        <h2>📊 Categories</h2>
        <div style="display: flex; gap: 10px; flex-wrap: wrap; margin: 15px 0;">
"""

        for cat, count in report.categories.items():
            html_content += f'<span class="category-tag">{cat}: {count}</span>\n'

        html_content += """
        </div>

        <h2>📋 Device Details</h2>
        <table>
            <thead>
                <tr>
                    <th>Status</th>
                    <th>Device Name</th>
                    <th>Category</th>
                    <th>Current Version</th>
                    <th>Available Update</th>
                    <th>Provider</th>
                </tr>
            </thead>
            <tbody>
"""

        for dev in report.devices:
            if dev["has_problem"]:
                status = '<span class="status-problem">⚠️ Problem</span>'
            elif dev["is_updatable"]:
                status = '<span class="status-update">🔵 Update Ready</span>'
            else:
                status = '<span class="status-ok">✅ OK</span>'

            update_info = dev["available_update"] if dev["available_update"] else "—"

            html_content += f"""
                <tr>
                    <td>{status}</td>
                    <td>{dev["name"]}</td>
                    <td>{dev["category"]}</td>
                    <td>{dev["current_version"]} ({dev["current_date"]})</td>
                    <td>{update_info}</td>
                    <td>{dev["provider"] or "—"}</td>
                </tr>
"""

        html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

        return filepath

    def _save_txt_scan_report(self, report: ScanReport, timestamp: str) -> str:
        filename = f"scan_report_{timestamp}.txt"
        filepath = os.path.join(self.reports_dir, filename)

        lines = [
            "=" * 80,
            "DRIVER SCAN REPORT",
            "=" * 80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Devices:     {report.total_devices}",
            f"Problem Devices:   {report.problem_devices}",
            f"Updates Available: {report.updatable_devices}",
            "",
            "CATEGORIES",
            "-" * 40
        ]

        for cat, count in report.categories.items():
            lines.append(f"  {cat}: {count}")

        lines.extend([
            "",
            "DEVICE DETAILS",
            "-" * 40
        ])

        for dev in report.devices:
            status = "PROBLEM" if dev["has_problem"] else ("UPDATE" if dev["is_updatable"] else "OK")
            lines.append(f"[{status}] {dev['name']}")
            lines.append(f"       Category: {dev['category']}")
            lines.append(f"       Version: {dev['current_version']} ({dev['current_date']})")
            if dev["available_update"]:
                lines.append(f"       Update Available: {dev['available_update']}")
            lines.append("")

        lines.append("=" * 80)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

        return filepath

    def log_update_operation(self, update_report: UpdateReport) -> str:
        """
        Logs a single update operation to the update history log.
        """
        log_file = os.path.join(self.reports_dir, "update_history.json")

        # Load existing history
        history = []
        if os.path.exists(log_file):
            try:
                with open(log_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except:
                history = []

        # Add new entry
        history.append(asdict(update_report))

        # Save updated history
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

        return log_file

    def get_update_history(self, limit: int = 50) -> List[Dict]:
        """
        Retrieves recent update history.
        """
        log_file = os.path.join(self.reports_dir, "update_history.json")

        if not os.path.exists(log_file):
            return []

        try:
            with open(log_file, "r", encoding="utf-8") as f:
                history = json.load(f)
            return history[-limit:]
        except:
            return []


class OperationLogger:
    """Custom logger for driver operations with file and console output."""

    def __init__(self, log_dir: Optional[str] = None, level: int = logging.INFO):
        if not log_dir:
            log_dir = os.path.join(
                os.path.expanduser("~"),
                "DriverUpdaterLogs"
            )
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)

        # Create logger
        self.logger = logging.getLogger("DriverUpdater")
        self.logger.setLevel(level)

        # Clear existing handlers
        self.logger.handlers = []

        # File handler
        log_file = os.path.join(
            log_dir,
            f"driver_updater_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)

        # Formatter
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str):
        self.logger.error(message)

    def debug(self, message: str):
        self.logger.debug(message)

    def success(self, message: str):
        """Custom success level."""
        self.logger.info(f"✅ SUCCESS: {message}")


if __name__ == "__main__":
    print("Testing Report Manager...")

    # Create sample report
    from core.scanner import DeviceInfo

    sample_devices = [
        DeviceInfo(
            instance_id="PCI\\VEN_8086&DEV_1234",
            name="Intel(R) HD Graphics",
            device_class="Display",
            manufacturer="Intel",
            current_driver_version="27.20.100.8935",
            current_driver_date="01/15/2024",
            provider_name="Intel Corporation",
            has_problem=False
        ),
        DeviceInfo(
            instance_id="USB\\VID_046D&DEV_C52B",
            name="Logitech USB Receiver",
            device_class="Mouse",
            manufacturer="Logitech",
            current_driver_version="N/A",
            current_driver_date="N/A",
            provider_name="Logitech",
            has_problem=False
        )
    ]

    report_mgr = ReportManager()

    # Generate reports
    print("\nGenerating JSON report...")
    json_path = report_mgr.generate_scan_report(sample_devices, format="json")
    print(f"Saved: {json_path}")

    print("\nGenerating HTML report...")
    html_path = report_mgr.generate_scan_report(sample_devices, format="html")
    print(f"Saved: {html_path}")

    print("\nGenerating TXT report...")
    txt_path = report_mgr.generate_scan_report(sample_devices, format="txt")
    print(f"Saved: {txt_path}")

    # Test operation logger
    print("\nTesting Operation Logger...")
    op_logger = OperationLogger()
    op_logger.info("Test information message")
    op_logger.success("Test success message")
    op_logger.warning("Test warning message")
    op_logger.error("Test error message")
