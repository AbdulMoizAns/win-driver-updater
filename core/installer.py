"""
Driver Installer Engine
Downloads driver packages (.cab), extracts them, and installs via pnputil.
"""

import os
import shutil
import subprocess
import urllib.request
import logging
from typing import Tuple, List, Callable, Optional

logger = logging.getLogger(__name__)

class DriverInstaller:
    """Manages downloading, extracting, and installing Windows drivers."""

    @staticmethod
    def download_driver(
        url: str,
        dest_dir: str,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Tuple[bool, str]:
        """
        Downloads the driver package (.cab) from Microsoft CDN or repository to dest_dir.
        """
        try:
            os.makedirs(dest_dir, exist_ok=True)
            filename = url.split("/")[-1] or "driver_package.cab"
            dest_file = os.path.join(dest_dir, filename)

            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            req = urllib.request.Request(url, headers=headers)

            with urllib.request.urlopen(req, timeout=30) as resp, open(dest_file, "wb") as out_file:
                total_size = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                block_size = 65536

                while True:
                    buffer = resp.read(block_size)
                    if not buffer:
                        break
                    downloaded += len(buffer)
                    out_file.write(buffer)
                    if progress_callback and total_size > 0:
                        progress_callback(downloaded, total_size)

            return True, dest_file
        except Exception as e:
            logger.error(f"Failed to download driver: {e}")
            return False, str(e)

    @staticmethod
    def extract_cab(cab_path: str, extract_dir: str) -> Tuple[bool, str]:
        """
        Extracts a Windows .cab archive using native expand.exe.
        """
        try:
            os.makedirs(extract_dir, exist_ok=True)
            cmd = ["expand.exe", "-F:*", cab_path, extract_dir]
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            if res.returncode == 0:
                return True, extract_dir
            else:
                return False, f"CAB extract failed: {res.stderr or res.stdout}"
        except Exception as e:
            logger.error(f"Error extracting CAB: {e}")
            return False, str(e)

    @staticmethod
    def find_inf_files(folder: str) -> List[str]:
        """
        Recursively searches for .inf setup files in an extracted folder.
        """
        inf_files = []
        for root, _, files in os.walk(folder):
            for file in files:
                if file.lower().endswith(".inf"):
                    inf_files.append(os.path.join(root, file))
        return inf_files

    @staticmethod
    def install_driver(inf_path: str) -> Tuple[bool, str]:
        """
        Installs a driver INF using pnputil.exe /add-driver <inf> /install.
        """
        if not os.path.exists(inf_path):
            return False, f"INF file not found: {inf_path}"

        cmd = ["pnputil.exe", "/add-driver", inf_path, "/install"]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            output = res.stdout + "\n" + res.stderr
            # Return code 0 = Success, 3010 = Success (Reboot required)
            if res.returncode in (0, 3010) or "Successfully added" in output:
                reboot_req = res.returncode == 3010 or "reboot" in output.lower()
                note = " (System reboot required to take full effect)" if reboot_req else ""
                return True, f"Driver installed successfully!{note}"
            else:
                return False, f"Installation failed:\n{output.strip()}"
        except Exception as e:
            logger.error(f"Driver installation error: {e}")
            return False, str(e)

    @staticmethod
    def update_from_url(
        url: str,
        staging_dir: str,
        log_callback: Optional[Callable[[str], None]] = None
    ) -> Tuple[bool, str]:
        """
        End-to-end pipeline: download -> extract -> find inf -> pnputil install.
        """
        def log(msg):
            if log_callback:
                log_callback(msg)
            logger.info(msg)

        log(f"Downloading driver from: {url}")
        ok, cab_file = DriverInstaller.download_driver(url, staging_dir)
        if not ok:
            return False, f"Download error: {cab_file}"

        extract_dir = os.path.join(staging_dir, "extracted")
        log(f"Extracting package: {os.path.basename(cab_file)}")
        ok, err = DriverInstaller.extract_cab(cab_file, extract_dir)
        if not ok:
            return False, err

        inf_files = DriverInstaller.find_inf_files(extract_dir)
        if not inf_files:
            return False, "No .inf driver file found in extracted package."

        log(f"Found {len(inf_files)} driver configuration file(s). Installing...")
        for inf in inf_files:
            log(f"Installing {os.path.basename(inf)}...")
            ok, msg = DriverInstaller.install_driver(inf)
            if ok:
                log(msg)
                return True, msg

        return False, "Could not install candidate INF files."
