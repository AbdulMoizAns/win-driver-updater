"""
Online Driver Fetcher & Update Checker
Queries Microsoft Update Catalog and Windows Update Agent (WUA) API.
"""

import re
import urllib.parse
import urllib.request
import logging
from typing import List, Optional, Dict, Tuple
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

@dataclass
class DriverUpdateCandidate:
    title: str
    version: str
    date_str: str
    download_url: str
    size: str
    classification: str
    architecture: str


class DriverFetcher:
    """Fetches verified drivers from Microsoft Update Catalog and WUA."""

    CATALOG_SEARCH_URL = "https://www.catalog.update.microsoft.com/Search.aspx?q={query}"
    CATALOG_DOWNLOAD_URL = "https://www.catalog.update.microsoft.com/DownloadDialog.aspx"

    @staticmethod
    def check_updates_for_device(
        device_id: str,
        current_version: str = "0.0.0.0",
        current_date_str: str = ""
    ) -> Optional[DriverUpdateCandidate]:
        """
        Searches Microsoft Update Catalog for a hardware ID or name and returns the best newer candidate.
        """
        if not device_id or device_id == "Unknown":
            return None

        # Clean query (e.g. PCI\VEN_8086&DEV_15A2)
        query = device_id.strip()
        candidates = DriverFetcher.search_catalog(query)

        if not candidates:
            # Try searching with just Vendor & Device ID if subsystem was included
            m = re.match(r"(PCI\\VEN_[0-9A-Fa-f]{4}&DEV_[0-9A-Fa-f]{4})", query, re.IGNORECASE)
            if m and m.group(1) != query:
                candidates = DriverFetcher.search_catalog(m.group(1))

        if not candidates:
            return None

        # Filter candidates newer than current
        newer_candidates = []
        for cand in candidates:
            if DriverFetcher._is_newer(cand.version, cand.date_str, current_version, current_date_str):
                newer_candidates.append(cand)

        if newer_candidates:
            # Sort by version/date descending
            newer_candidates.sort(
                key=lambda c: (DriverFetcher._parse_date(c.date_str), DriverFetcher._parse_version(c.version)),
                reverse=True
            )
            return newer_candidates[0]

        return None

    @staticmethod
    def search_catalog(query: str) -> List[DriverUpdateCandidate]:
        """
        Queries Microsoft Update Catalog and returns parsed driver entries.
        """
        encoded_query = urllib.parse.quote(query)
        url = DriverFetcher.CATALOG_SEARCH_URL.format(query=encoded_query)

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            logger.debug(f"Catalog query failed for '{query}': {e}")
            return []

        candidates: List[DriverUpdateCandidate] = []

        # Find rows inside the table: id="headerRow" or rows with goToDownload
        row_matches = re.findall(
            r"<tr[^>]*id=['\"]?([a-f0-9\-]+_row)['\"]?[^>]*>(.*?)</tr>",
            html,
            re.DOTALL | re.IGNORECASE
        )

        for row_id, row_content in row_matches:
            # Extract title
            title_m = re.search(r"class=['\"]?resultsTitle['\"]?[^>]*>(.*?)</a>", row_content, re.DOTALL | re.IGNORECASE)
            title = re.sub(r"<[^>]+>", "", title_m.group(1)).strip() if title_m else ""

            # Extract cells
            cells = re.findall(r"<td[^>]*>(.*?)</td>", row_content, re.DOTALL | re.IGNORECASE)
            if len(cells) < 6:
                continue

            products = re.sub(r"<[^>]+>", "", cells[1]).strip()
            classification = re.sub(r"<[^>]+>", "", cells[2]).strip()
            date_str = re.sub(r"<[^>]+>", "", cells[3]).strip()
            ver_str = re.sub(r"<[^>]+>", "", cells[4]).strip()
            size_str = re.sub(r"<[^>]+>", "", cells[5]).strip()

            # Extract Update ID for download link
            update_id_m = re.search(r"goToDownload\(\s*['\"]([^'\"]+)['\"]", row_content)
            if not update_id_m:
                update_id_m = re.search(r"id=['\"]?([a-f0-9\-]+)_download['\"]?", row_content)

            update_id = update_id_m.group(1) if update_id_m else ""
            if not update_id:
                continue

            # Resolve actual download URL for the update ID
            download_url = DriverFetcher._resolve_catalog_download_url(update_id)
            if not download_url:
                continue

            arch = "x64" if "x64" in title.lower() or "amd64" in title.lower() else "any"

            candidate = DriverUpdateCandidate(
                title=title,
                version=ver_str,
                date_str=date_str,
                download_url=download_url,
                size=size_str,
                classification=classification,
                architecture=arch
            )
            candidates.append(candidate)

        return candidates

    @staticmethod
    def _resolve_catalog_download_url(update_id: str) -> Optional[str]:
        """
        Posts to DownloadDialog.aspx to get the actual .cab CDN URL.
        """
        url = DriverFetcher.CATALOG_DOWNLOAD_URL
        payload = f"updateIDs=[{{\"size\":0,\"languages\":\"\",\"uidInfo\":\"{update_id}\",\"updateID\":\"{update_id}\"}}]"
        data = payload.encode("utf-8")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        try:
            req = urllib.request.Request(url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_text = resp.read().decode("utf-8", errors="replace")
                # Look for download link
                url_m = re.search(r"(http[s]?://download\.windowsupdate\.com/[^\s\'\"]+\.cab)", resp_text, re.IGNORECASE)
                if url_m:
                    return url_m.group(1)
        except Exception as e:
            logger.debug(f"Failed to resolve download URL for {update_id}: {e}")

        return None

    @staticmethod
    def query_windows_update_drivers() -> List[Dict[str, str]]:
        """
        Uses PowerShell to query Windows Update Agent COM API directly for available driver updates.
        """
        ps_script = """
        $session = New-Object -ComObject Microsoft.Update.Session
        $searcher = $session.CreateUpdateSearcher()
        $searcher.ServerSelection = 2 # Windows Update default
        try {
            $result = $searcher.Search("IsInstalled=0 and Type='Driver'")
            $updates = @()
            foreach ($u in $result.Updates) {
                $updates += @{
                    Title = $u.Title
                    Description = $u.Description
                    DriverModel = $u.DriverModel
                    DriverVerDate = if ($u.DriverVerDate) { $u.DriverVerDate.ToString("MM/dd/yyyy") } else { "" }
                    DriverProvider = $u.DriverProvider
                }
            }
            $updates | ConvertTo-Json -Compress
        } catch {
            Write-Output "[]"
        }
        """
        import subprocess, json
        try:
            res = subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps_script],
                capture_output=True,
                text=True,
                errors="replace",
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)
            )
            out = res.stdout.strip()
            if out and out.startswith("[") or out.startswith("{"):
                parsed = json.loads(out)
                return [parsed] if isinstance(parsed, dict) else parsed
        except Exception as e:
            logger.debug(f"WUA query error: {e}")

        return []

    @staticmethod
    def _parse_version(v_str: str) -> Tuple[int, ...]:
        parts = re.findall(r"\d+", str(v_str))
        return tuple(int(p) for p in parts[:6]) if parts else (0,)

    @staticmethod
    def _parse_date(d_str: str) -> datetime:
        if not d_str or d_str == "N/A":
            return datetime.min
        for fmt in ("%m/%d/%Y", "%Y-%m-%d", "%d/%m/%Y", "%m-%d-%Y"):
            try:
                return datetime.strptime(d_str.strip(), fmt)
            except ValueError:
                continue
        return datetime.min

    @staticmethod
    def _is_newer(
        new_ver: str, new_date: str,
        curr_ver: str, curr_date: str
    ) -> bool:
        """
        Determines if candidate driver is strictly newer by date or version.
        """
        d_new = DriverFetcher._parse_date(new_date)
        d_curr = DriverFetcher._parse_date(curr_date)

        v_new = DriverFetcher._parse_version(new_ver)
        v_curr = DriverFetcher._parse_version(curr_ver)

        if d_new > d_curr and d_curr != datetime.min:
            return True
        if v_new > v_curr and v_curr != (0,):
            return True
        return False
