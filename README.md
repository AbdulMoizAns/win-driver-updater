<p align="center">
  <img src="assets/logo.jpg" alt="Windows Driver Updater Logo" width="180" style="border-radius: 28px; box-shadow: 0 8px 24px rgba(0,0,0,0.5);"/>
</p>

<h1 align="center">Windows Driver Updater</h1>

<p align="center">
  <b>A Lightweight, Fast, and Open-Source Driver Management Suite for Windows 10 & 11</b><br>
  Scans hardware devices, queries Microsoft Update Catalog for WHQL-certified drivers, creates automatic backups, and installs updates safely.
</p>

<p align="center">
  <a href="https://github.com/AbdulMoizAns/win-driver-updater/releases"><img src="https://img.shields.io/github/v/release/AbdulMoizAns/win-driver-updater?include_prereleases&color=blue" alt="Release"/></a>
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D4?logo=windows&logoColor=white" alt="Platform"/>
  <img src="https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Driver%20Integrity-100%25%20WHQL%20Signed-success" alt="WHQL"/>
  <img src="https://img.shields.io/badge/Architecture-x64%20%7C%20x86%20%7C%20ARM64-lightgrey" alt="Architecture"/>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-purple.svg" alt="License"/></a>
</p>

---

## 📌 Table of Contents
- [Why Windows Driver Updater?](#-why-windows-driver-updater)
- [Key Features](#-key-features)
- [How It Works (Architecture)](#-how-it-works-architecture)
- [Installation & Quickstart](#-installation--quickstart)
- [CLI Command Reference](#-cli-command-reference)
- [Safety & Rollback Protection](#-safety--rollback-protection)
- [Frequently Asked Questions (FAQ)](#-frequently-asked-questions-faq)
- [Contributing](#-contributing)
- [License](#-license)

---

## 💡 Why Windows Driver Updater?

Most commercial driver updaters (e.g., Driver Booster, Driver Easy) are bloated, ad-supported, require paid subscriptions, and often bundle untested drivers from obscure sources that can trigger the dreaded **Blue Screen of Death (BSOD)**.

**Windows Driver Updater** is built with a different philosophy:
1. **100% Open-Source & Transparent**: Every line of Python code is inspectable. No telemetry, no background ads, no paywalls.
2. **Strict WHQL Signature Enforcement**: Sources official `.cab` packages directly from the **Microsoft Update Catalog** (`catalog.update.microsoft.com`) and **Windows Update Agent (WUA)**.
3. **Native Windows Integration**: Utilizes Windows native tools (`pnputil.exe`, `CIM/WMI`, `expand.exe`) without requiring bloated third-party background services.
4. **Safety First**: Full driver export and system restore point integration before any installation.

---

## 🚀 Key Features

| Feature | Description |
| :--- | :--- |
| 🔍 **Hardware & Driver Scanner** | Enumerates all physical and virtual devices, extracts exact **Hardware IDs** (`PCI\VEN_xxxx&DEV_xxxx`, `USB\VID_xxxx&PID_xxxx`), driver versions, release dates, and flags problem devices (Code 28 missing drivers, Code 10 failures). |
| 🌐 **Microsoft Update Catalog Query** | Connects directly to Microsoft's cloud catalog via HTTPS to retrieve authentic OEM drivers (Intel, Realtek, NVIDIA, AMD, Lenovo, Dell, HP). |
| 🛡️ **1-Click OEM Driver Backup** | Exports all third-party drivers (`pnputil /export-driver * <dir>`) into `.inf`, `.sys`, and `.cat` files for zero-risk recovery. |
| ⚡ **Automated Extraction & Deployment** | Downloads `.cab` archives, extracts them using native `expand.exe`, and stages them into the Windows Driver Store via `pnputil /add-driver ... /install`. |
| 🎨 **Modern Dark Mode Desktop GUI** | Built with native Python `tkinter` & `ttk`. Features real-time category filtering (Network, Display, Audio, Bluetooth), live search, and threaded non-blocking progress indicators. |
| 💻 **Automated CLI Mode** | Run audits, backups, and online update checks directly from PowerShell or Command Prompt. |

---

## 🏗️ How It Works (Architecture)

```
+-------------------------------------------------------------------------------+
|                           Windows Driver Updater                             |
+-------------------------------------------------------------------------------+
                                        |
     +----------------------------------+----------------------------------+
     |                                  |                                  |
     v                                  v                                  v
[ Desktop GUI ]                 [ CLI Engine ]                 [ Auto-UAC Batch ]
(ui/app_gui.py)                   (main.py)                        (run.bat)
     |                                  |                                  |
     +----------------------------------+----------------------------------+
                                        |
     +----------------------------------+----------------------------------+
     |                                  |                                  |
     v                                  v                                  v
[ Device Scanner ]              [ Driver Fetcher ]            [ Backup & Install ]
 (core/scanner.py)              (core/fetcher.py)            (core/backup & install)
     |                                  |                                  |
     +---> pnputil.exe                  +---> MS Update Catalog            +---> pnputil export/install
     +---> CIM/WMI Win32_PnPEntity      +---> WUA COM API                  +---> expand.exe
     +---> Hardware IDs & Versions      +---> WHQL Signed CABs             +---> Restore Points
```

---

## 💻 Installation & Quickstart

### Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit / 32-bit)
- **Python**: Version 3.10 or higher
- **Administrator Rights**: Required for driver installation and full hardware export.

### 1. Clone the Repository
```powershell
git clone https://github.com/AbdulMoizAns/win-driver-updater.git
cd win-driver-updater
```

### 2. Run the Application
Simply double-click **`run.bat`** (it will auto-detect Python and elevate Administrator privileges).

Alternatively, run directly from terminal:
```powershell
# Run GUI
python main.py

# Or with py launcher
py -3 main.py
```

---

## ⌨️ CLI Command Reference

The application can also be run entirely from the command line without opening the GUI:

### 1. Full Hardware & Driver Scan
Scans every device on the system and groups them by category:
```powershell
python main.py --scan
```
*Example Output:*
```text
📁 [Net] (6 devices)
  ✅ Intel(R) Dual Band Wireless-AC 7265
     Driver: 19.51.50.2 (11/04/2023) | Provider: Intel
     Hardware ID: PCI\VEN_8086&DEV_095B&SUBSYS_52108086
  ✅ Intel(R) Ethernet Connection I218-LM
     Driver: 12.19.2.65 (06/17/2025) | Provider: Intel
     Hardware ID: PCI\VEN_8086&DEV_15A2
```

### 2. Check Online Driver Updates
Queries Microsoft Update Catalog for critical hardware (Network, Display, Audio):
```powershell
python main.py --check-updates
```

### 3. Backup All Installed Drivers
Creates a complete standalone backup folder containing all 3rd-party `.inf`, `.sys`, and `.cat` driver packages:
```powershell
python main.py --backup "C:\MyDriverBackups"
```

---

## 🛡️ Safety & Rollback Protection

Modifying drivers carries inherent risks if done improperly. This project incorporates multiple layers of safety:

1. **WHQL Signature Verification**: Only drivers with genuine digital signatures from Microsoft Windows Hardware Compatibility Publisher are installed.
2. **Driver Store Isolation**: Installs drivers via `pnputil.exe`, ensuring Windows stages and verifies driver catalog hashes before loading them into kernel mode.
3. **Pre-Update Export**: You can export your current working drivers with one click, allowing offline re-installation via:
   ```powershell
   pnputil /add-driver "C:\MyDriverBackups\*.inf" /subdirs /install
   ```
4. **Windows Restore Point**: Integrates with PowerShell `Checkpoint-Computer` to create a `DEVICE_DRIVER_INSTALL` restore point before updating.

---

## ❓ Frequently Asked Questions (FAQ)

#### Q: Why does this app require Administrator permissions?
> **A**: Windows restricts driver installation and kernel device configuration to Administrator accounts to prevent malware from modifying low-level hardware drivers.

#### Q: Can this app cause a Blue Screen (BSOD)?
> **A**: No, because unlike commercial driver tools that distribute repackaged or custom modified drivers, this tool exclusively fetches official, digitally signed WHQL packages from Microsoft's official CDN (`download.windowsupdate.com`).

#### Q: What is a Code 28 error?
> **A**: Code 28 in Windows Device Manager means the driver for that piece of hardware is missing. The app's scanner specifically detects these devices and displays their exact Vendor and Device IDs so matching drivers can be fetched.

---

## 🤝 Contributing

Contributions are welcome! If you'd like to improve the scanner, enhance the GUI, or add additional open-source driver pack sources:
1. Fork the Project.
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the Branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for more information.

---

<p align="center">
  Developed with ❤️ by <a href="https://github.com/AbdulMoizAns"><b>Abdul Moiz Ansari</b></a>
</p>
