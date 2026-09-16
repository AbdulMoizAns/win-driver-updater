"""
Windows Device & Driver Scanner
Scans connected hardware devices, current driver versions, and problem devices.
"""

import subprocess
import re
import json
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

@dataclass
class DeviceInfo:
    instance_id: str
    name: str = "Unknown Device"
    device_class: str = "Other"
    manufacturer: str = "Unknown"
    status: str = "Unknown"
    current_driver_name: str = ""
    current_driver_version: str = "N/A"
    current_driver_date: str = "N/A"
    provider_name: str = ""
    matching_device_id: str = ""
    hardware_ids: List[str] = field(default_factory=list)
    has_problem: bool = False
    problem_code: int = 0
    available_update_version: Optional[str] = None
    available_update_date: Optional[str] = None
    download_url: Optional[str] = None
    update_title: Optional[str] = None

    @property
    def is_updatable(self) -> bool:
        return bool(self.available_update_version and self.available_update_version != self.current_driver_version)


class DriverScanner:
    """Scans Windows devices and drivers using pnputil and PowerShell."""

    @staticmethod
    def scan_all_devices() -> List[DeviceInfo]:
        """
        Executes pnputil /enum-devices /drivers and parses the output into DeviceInfo objects.
        """
        devices = DriverScanner._parse_pnputil_devices()
        
        # Enrich with problem status from CIM / WMI
        try:
            problem_map = DriverScanner._get_problem_devices()
            for dev in devices:
                if dev.instance_id in problem_map:
                    dev.has_problem = True
                    dev.problem_code = problem_map[dev.instance_id].get("code", 0)
                    if dev.name == "Unknown Device" or not dev.name:
                        dev.name = problem_map[dev.instance_id].get("name", dev.name)
        except Exception as e:
            logger.warning(f"Could not query problem devices: {e}")

        return devices

    @staticmethod
    def _parse_pnputil_devices() -> List[DeviceInfo]:
        cmd = ["pnputil.exe", "/enum-devices", "/drivers"]
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            raw_text = result.stdout
        except Exception as e:
            logger.error(f"Failed to execute pnputil: {e}")
            return []

        devices: List[DeviceInfo] = []
        raw_blocks = re.split(r"\n\s*(?=Instance ID:\s*)", raw_text)

        for block in raw_blocks:
            if not block.strip() or "Instance ID:" not in block:
                continue

            instance_id = DriverScanner._extract_field(block, r"Instance ID:\s*(.+)")
            if not instance_id:
                continue

            name = DriverScanner._extract_field(block, r"Device Description:\s*(.+)") or "Unknown Device"
            class_name = DriverScanner._extract_field(block, r"Class Name:\s*(.+)") or "Other"
            manufacturer = DriverScanner._extract_field(block, r"Manufacturer Name:\s*(.+)") or "Unknown"
            status = DriverScanner._extract_field(block, r"Status:\s*(.+)") or "Unknown"
            driver_name = DriverScanner._extract_field(block, r"Driver Name:\s*(.+)")

            # Parse installed/best-ranked driver section
            version_str = "N/A"
            date_str = "N/A"
            provider = ""
            matching_id = ""

            # Check Driver Version: MM/DD/YYYY XX.XX.XX.XX
            ver_match = re.search(r"Driver Version:\s*(\d{1,2}/\d{1,2}/\d{4})\s+([\d\.]+)", block)
            if ver_match:
                date_str = ver_match.group(1)
                version_str = ver_match.group(2)
            else:
                single_ver = re.search(r"Driver Version:\s*([^\r\n]+)", block)
                if single_ver:
                    version_str = single_ver.group(1).strip()

            provider_match = re.search(r"Provider Name:\s*([^\r\n]+)", block)
            if provider_match:
                provider = provider_match.group(1).strip()

            matching_id_match = re.search(r"Matching Device ID:\s*([^\r\n]+)", block)
            if matching_id_match:
                matching_id = matching_id_match.group(1).strip()

            hardware_ids = []
            if matching_id:
                hardware_ids.append(matching_id)
            if instance_id and ("PCI\\" in instance_id or "USB\\" in instance_id or "HDAUDIO\\" in instance_id):
                parts = instance_id.split("\\")
                if len(parts) >= 2:
                    clean_id = f"{parts[0]}\\{parts[1]}"
                    if clean_id not in hardware_ids:
                        hardware_ids.append(clean_id)

            dev = DeviceInfo(
                instance_id=instance_id,
                name=name,
                device_class=class_name,
                manufacturer=manufacturer,
                status=status,
                current_driver_name=driver_name,
                current_driver_version=version_str,
                current_driver_date=date_str,
                provider_name=provider,
                matching_device_id=matching_id,
                hardware_ids=hardware_ids
            )
            devices.append(dev)

        return devices

    @staticmethod
    def _extract_field(text: str, pattern: str) -> str:
        m = re.search(pattern, text)
        return m.group(1).strip() if m else ""

    @staticmethod
    def _get_problem_devices() -> Dict[str, dict]:
        ps_cmd = (
            "Get-CimInstance Win32_PnPEntity | "
            "Where-Object { $_.ConfigManagerErrorCode -ne 0 } | "
            "Select-Object DeviceID, Caption, ConfigManagerErrorCode | "
            "ConvertTo-Json -Compress"
        )
        try:
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_cmd],
                capture_output=True,
                text=True,
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            data_str = res.stdout.strip()
            if not data_str:
                return {}
            data = json.loads(data_str)
            if isinstance(data, dict):
                data = [data]
            problems = {}
            for item in data:
                dev_id = item.get("DeviceID")
                if dev_id:
                    problems[dev_id] = {
                        "name": item.get("Caption", "Unknown Device"),
                        "code": item.get("ConfigManagerErrorCode", 0)
                    }
            return problems
        except Exception as e:
            logger.debug(f"Error querying problem devices via PowerShell: {e}")
            return {}


if __name__ == "__main__":
    print("Testing device scan...")
    devs = DriverScanner.scan_all_devices()
    print(f"Total devices scanned: {len(devs)}")
    for d in devs[:10]:
        print(f"[{d.device_class}] {d.name} | Driver: {d.current_driver_version} ({d.current_driver_date}) | ID: {d.matching_device_id}")
