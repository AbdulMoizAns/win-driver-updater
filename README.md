<p align="center">
  <img src="assets/logo.jpg" alt="Windows Driver Updater Logo" width="180" style="border-radius: 24px;"/>
</p>

<h1 align="center">Windows Driver Updater</h1>

<p align="center">
  <b>Fast, Safe, and Open-Source Driver Management for Windows 10 & 11</b><br>
  Built with Python, Microsoft Update Catalog, and Native Windows PnP APIs.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-blue" alt="Platform"/>
  <img src="https://img.shields.io/badge/Python-3.10%2B-brightgreen" alt="Python"/>
  <img src="https://img.shields.io/badge/Drivers-WHQL%20Certified-success" alt="WHQL"/>
  <img src="https://img.shields.io/badge/License-MIT-purple" alt="License"/>
</p>

---

## 🚀 Key Features

- **🔍 Full System Hardware Scanner**:
  - Leverages Windows native `pnputil.exe` and CIM/WMI to detect every hardware component.
  - Categorizes devices: Network, GPU/Display, Media/Audio, Bluetooth, System, Storage, and USB.
  - Reads precise **Hardware IDs** (`PCI\VEN_xxxx&DEV_xxxx`, `USB\VID_xxxx&PID_xxxx`).
  - Detects missing devices (e.g. Code 28 missing driver).

- **🌐 Genuine Online Updates**:
  - Live query to **Microsoft Update Catalog** and **Windows Update Agent (WUA)**.
  - Downloads genuine, WHQL-digitally-signed `.cab` packages directly from official Microsoft CDNs.
  - Zero risk of Blue Screens (BSOD) caused by unsigned or modified drivers.

- **💾 1-Click Backup & Restore**:
  - Full export of all third-party OEM drivers (`pnputil /export-driver`).
  - Safe rollback anytime if any hardware issue occurs.
  - Windows System Restore Point creation support.

- **⚡ Automated Driver Deployment**:
  - Automated download -> `.cab` expansion via native `expand.exe` -> Driver Store installation via `pnputil /add-driver ... /install`.

- **🎨 Modern Dark Mode GUI & CLI**:
  - Clean desktop interface built with native Tkinter (no heavy dependencies).
  - Search filter and category drop-down.
  - Terminal CLI mode for automation (`--scan`, `--check-updates`, `--backup`).

---

## 💻 How to Run

### Method 1: Double-Click Launcher (Easiest)
Double-click `run.bat` (or `Run_Driver_Updater.bat` on your Desktop) to automatically elevate administrator privileges and launch the GUI.

### Method 2: Command Line (CLI)
```powershell
# Launch Desktop GUI
python main.py

# Perform Terminal Hardware Scan
python main.py --scan

# Check Online Driver Updates
python main.py --check-updates

# Backup Drivers to Folder
python main.py --backup "C:\MyDriverBackups"
```

---

## 🛠️ Project Structure

```
win_driver_updater/
├── assets/
│   └── logo.jpg            # Application Logo
├── core/
│   ├── scanner.py          # PnPUtil & WMI Hardware Scanner
│   ├── fetcher.py          # Microsoft Update Catalog & WUA API Fetcher
│   ├── installer.py        # CAB extraction & pnputil installation
│   └── backup.py           # Driver export & restore point manager
├── ui/
│   └── app_gui.py          # Modern Dark Desktop GUI
├── main.py                 # Application entrypoint & CLI handlers
├── run.bat                 # 1-Click UAC auto-elevated batch launcher
├── requirements.txt        # Optional Python dependencies
└── README.md               # Documentation
```

---

## 📄 License
This project is open-source and released under the [MIT License](LICENSE).
