"""
Modern Desktop GUI for Windows Driver Updater
Built with Tkinter / TTK with Dark Theme styling, Per-Monitor High-DPI support, and responsive threading.
"""

import sys
import os
import ctypes
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import List, Optional

from core.scanner import DriverScanner, DeviceInfo
from core.fetcher import DriverFetcher
from core.backup import DriverBackupManager
from core.installer import DriverInstaller
from core.safety import SafetyManager
from core.reporter import ReportManager, OperationLogger
from core.scheduler import SchedulerManager

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


def enable_high_dpi_awareness():
    """Enables Windows Per-Monitor High-DPI Awareness (V2) to eliminate blurry UI and fonts."""
    if sys.platform == "win32":
        # 1. Set explicit AppUserModelID so Windows Taskbar shows the app's custom icon, not python.exe
        try:
            myappid = "abdulmoizans.windriverupdater.gui.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass

        # 2. Set Per-Monitor High-DPI Awareness
        try:
            # Per-Monitor V2 (Windows 10 1703+)
            ctypes.windll.user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
        except Exception:
            try:
                # Per-Monitor V1 (Windows 8.1+)
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except Exception:
                try:
                    # System DPI Aware (Windows Vista+)
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass


def get_screen_scale_factor() -> float:
    """Returns the display scale factor (e.g., 1.25 for 125%, 1.5 for 150%)."""
    if sys.platform == "win32":
        try:
            hdc = ctypes.windll.user32.GetDC(0)
            dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)  # LOGPIXELSX
            ctypes.windll.user32.ReleaseDC(0, hdc)
            return max(1.0, dpi / 96.0)
        except Exception:
            return 1.0
    return 1.0


def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


class DriverUpdaterApp(tk.Tk):
    """Main application window with crisp High-DPI rendering."""

    def __init__(self):
        # Enable High-DPI awareness before Tk initialization
        enable_high_dpi_awareness()
        super().__init__()

        self.scale = get_screen_scale_factor()

        # Set True high-dpi font scaling in Tk
        try:
            self.tk.call("tk", "scaling", (96.0 * self.scale) / 72.0)
        except Exception:
            pass

        self.title("Windows Driver Updater - Open Source & WHQL Manager")

        # Responsive window dimensions based on DPI
        win_w = int(1180 * min(self.scale, 1.25))
        win_h = int(760 * min(self.scale, 1.25))
        self.geometry(f"{win_w}x{win_h}")
        self.minsize(int(960 * min(self.scale, 1.2)), int(620 * min(self.scale, 1.2)))

        self.devices: List[DeviceInfo] = []
        self.filtered_devices: List[DeviceInfo] = []
        self.selected_device: Optional[DeviceInfo] = None
        self.is_scanning = False
        self.logo_img = None
        self.icon_img = None

        self._configure_theme()
        self._load_app_icons()
        self._build_ui()
        self._check_admin_banner()

    def _load_app_icons(self):
        """Loads and sets the window icon and header logo with native Windows taskbar integration."""
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        ico_path = os.path.join(assets_dir, "logo.ico")
        jpg_path = os.path.join(assets_dir, "logo.jpg")

        # 1. Native Windows .ico for taskbar and titlebar
        if os.path.exists(ico_path):
            try:
                self.iconbitmap(default=ico_path)
            except Exception:
                try:
                    self.wm_iconbitmap(ico_path)
                except Exception:
                    pass

        # 2. High-DPI PIL icon and header logo
        if HAS_PIL and os.path.exists(jpg_path):
            try:
                pil_img = Image.open(jpg_path)
                # Taskbar / Window icon (48x48)
                icon_size = (int(48 * self.scale), int(48 * self.scale))
                self.icon_img = ImageTk.PhotoImage(pil_img.resize(icon_size, Image.Resampling.LANCZOS))
                self.iconphoto(True, self.icon_img)

                # Header logo (44x44)
                hdr_size = (int(44 * self.scale), int(44 * self.scale))
                self.logo_img = ImageTk.PhotoImage(pil_img.resize(hdr_size, Image.Resampling.LANCZOS))
            except Exception:
                pass

    def _configure_theme(self):
        self.style = ttk.Style(self)
        self.style.theme_use("clam")

        self.bg_color = "#12131c"
        self.card_bg = "#1d1e2c"
        self.card_light = "#282a3e"
        self.card_hover = "#343752"
        self.text_color = "#ffffff"
        self.text_muted = "#9ca3af"
        self.accent_color = "#3b82f6"  # modern electric blue
        self.accent_green = "#10b981"
        self.accent_amber = "#f59e0b"
        self.accent_red = "#ef4444"

        self.configure(bg=self.bg_color)

        # High-DPI font sizing
        f_size_sm = max(9, int(9 * min(self.scale, 1.15)))
        f_size_base = max(10, int(10 * min(self.scale, 1.15)))
        f_size_lg = max(15, int(15 * min(self.scale, 1.15)))

        self.style.configure(".", background=self.bg_color, foreground=self.text_color)
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("Card.TFrame", background=self.card_bg, relief="flat")
        self.style.configure("TLabel", background=self.bg_color, foreground=self.text_color, font=("Segoe UI", f_size_base))
        self.style.configure("Header.TLabel", font=("Segoe UI", f_size_lg, "bold"), foreground="#60a5fa")
        self.style.configure("SubHeader.TLabel", font=("Segoe UI", f_size_sm), foreground=self.text_muted)
        self.style.configure("Status.TLabel", font=("Segoe UI", f_size_sm, "bold"), foreground=self.accent_green)

        # Crisp Modern Buttons
        btn_pad_x = int(14 * min(self.scale, 1.2))
        btn_pad_y = int(7 * min(self.scale, 1.2))

        self.style.configure(
            "Primary.TButton",
            font=("Segoe UI", f_size_base, "bold"),
            background="#2563eb",
            foreground="#ffffff",
            padding=(btn_pad_x, btn_pad_y),
            borderwidth=0,
            focuscolor="none"
        )
        self.style.map("Primary.TButton", background=[("active", "#1d4ed8"), ("pressed", "#1e40af")])

        self.style.configure(
            "Secondary.TButton",
            font=("Segoe UI", f_size_base),
            background=self.card_light,
            foreground=self.text_color,
            padding=(btn_pad_x - 2, btn_pad_y),
            borderwidth=0,
            focuscolor="none"
        )
        self.style.map("Secondary.TButton", background=[("active", self.card_hover)])

        # High-DPI Treeview
        row_height = int(34 * self.scale)
        self.style.configure(
            "Treeview",
            background=self.card_bg,
            foreground=self.text_color,
            fieldbackground=self.card_bg,
            rowheight=row_height,
            font=("Segoe UI", f_size_base),
            borderwidth=0
        )
        self.style.configure(
            "Treeview.Heading",
            background=self.card_light,
            foreground="#f3f4f6",
            font=("Segoe UI", f_size_base, "bold"),
            padding=(int(6 * self.scale), int(6 * self.scale))
        )
        self.style.map("Treeview", background=[("selected", "#2563eb")])

    def _build_ui(self):
        pad_x = int(18 * min(self.scale, 1.2))
        pad_y = int(10 * min(self.scale, 1.2))

        # 1. Header Frame with crisp Logo
        header_frame = ttk.Frame(self, padding=(pad_x, pad_y, pad_x, 4))
        header_frame.pack(fill="x")

        title_box = ttk.Frame(header_frame)
        title_box.pack(side="left", fill="y")

        if self.logo_img:
            logo_lbl = tk.Label(title_box, image=self.logo_img, bg=self.bg_color)
            logo_lbl.pack(side="left", padx=(0, 12))

        txt_box = ttk.Frame(title_box)
        txt_box.pack(side="left", fill="y")
        ttk.Label(txt_box, text="Windows Driver Updater", style="Header.TLabel").pack(anchor="w")
        ttk.Label(txt_box, text="Hardware Scanner & WHQL Driver Deployment Tool", style="SubHeader.TLabel").pack(anchor="w")

        # Admin Badge
        self.admin_badge_var = tk.StringVar(value="Checking privileges...")
        self.admin_badge_lbl = ttk.Label(
            header_frame,
            textvariable=self.admin_badge_var,
            font=("Segoe UI", max(9, int(9 * min(self.scale, 1.15))), "bold")
        )
        self.admin_badge_lbl.pack(side="right", padx=10)

        # 2. Action Toolbar
        toolbar = ttk.Frame(self, padding=(pad_x, int(8 * min(self.scale, 1.2))))
        toolbar.pack(fill="x")

        ttk.Button(toolbar, text="🔍 Scan Drivers", style="Primary.TButton", command=self.start_scan).pack(side="left", padx=4)
        ttk.Button(toolbar, text="🌐 Check Updates Online", style="Secondary.TButton", command=self.start_online_check).pack(side="left", padx=4)
        ttk.Button(toolbar, text="💾 Backup All Drivers", style="Secondary.TButton", command=self.start_backup).pack(side="left", padx=4)
        ttk.Button(toolbar, text="🛡️ Restore Drivers", style="Secondary.TButton", command=self.start_restore).pack(side="left", padx=4)
        ttk.Button(toolbar, text="⚡ Update Selected", style="Primary.TButton", command=self.update_selected_driver).pack(side="left", padx=4)
        ttk.Button(toolbar, text="📂 Device Manager", style="Secondary.TButton", command=self.open_device_manager).pack(side="right", padx=4)

        # 3. Filter & Search Bar
        filter_bar = ttk.Frame(self, padding=(pad_x, 6))
        filter_bar.pack(fill="x")

        f_size_base = max(10, int(10 * min(self.scale, 1.15)))

        ttk.Label(filter_bar, text="Category:", foreground=self.text_muted).pack(side="left", padx=(0, 8))
        self.category_var = tk.StringVar(value="All")
        categories = ["All", "Net", "Display", "MEDIA", "Bluetooth", "System", "Mouse", "Keyboard", "Errors / Missing"]
        cat_combo = ttk.Combobox(
            filter_bar,
            textvariable=self.category_var,
            values=categories,
            state="readonly",
            width=16,
            font=("Segoe UI", f_size_base)
        )
        cat_combo.pack(side="left", padx=(0, 20))
        cat_combo.bind("<<ComboboxSelected>>", lambda e: self.apply_filters())

        ttk.Label(filter_bar, text="Search:", foreground=self.text_muted).pack(side="left", padx=(0, 8))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.apply_filters())
        search_entry = tk.Entry(
            filter_bar,
            textvariable=self.search_var,
            bg=self.card_bg,
            fg=self.text_color,
            insertbackground=self.text_color,
            relief="flat",
            highlightthickness=1,
            highlightcolor=self.accent_color,
            highlightbackground=self.card_light,
            font=("Segoe UI", f_size_base),
            width=32
        )
        search_entry.pack(side="left")

        self.stats_lbl = ttk.Label(filter_bar, text="0 Devices found", foreground=self.text_muted)
        self.stats_lbl.pack(side="right")

        # 4. Device Table
        table_frame = ttk.Frame(self, padding=(pad_x, 6))
        table_frame.pack(fill="both", expand=True)

        cols = ("status", "name", "category", "version", "date", "update", "provider")
        self.tree = ttk.Treeview(table_frame, columns=cols, show="headings", selectmode="browse")

        self.tree.heading("status", text="Status")
        self.tree.heading("name", text="Device Description")
        self.tree.heading("category", text="Category")
        self.tree.heading("version", text="Installed Version")
        self.tree.heading("date", text="Driver Date")
        self.tree.heading("update", text="Available Update")
        self.tree.heading("provider", text="Provider")

        # High-DPI scaled column widths
        w_factor = self.scale
        self.tree.column("status", width=int(100 * w_factor), anchor="center")
        self.tree.column("name", width=int(320 * w_factor))
        self.tree.column("category", width=int(100 * w_factor), anchor="center")
        self.tree.column("version", width=int(130 * w_factor), anchor="center")
        self.tree.column("date", width=int(110 * w_factor), anchor="center")
        self.tree.column("update", width=int(140 * w_factor), anchor="center")
        self.tree.column("provider", width=int(140 * w_factor))

        # Colored status tags
        self.tree.tag_configure("problem", foreground="#f87171")
        self.tree.tag_configure("update_ready", foreground="#60a5fa")
        self.tree.tag_configure("ok", foreground="#f1f5f9")

        self.tree.bind("<<TreeviewSelect>>", self.on_device_selected)

        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # 5. Bottom Console / Progress
        bottom_frame = ttk.Frame(self, padding=(pad_x, 6, pad_x, int(14 * min(self.scale, 1.2))))
        bottom_frame.pack(fill="x")

        self.progress_bar = ttk.Progressbar(bottom_frame, mode="indeterminate")
        self.progress_bar.pack(fill="x", pady=(0, 8))

        f_size_code = max(9, int(9.5 * min(self.scale, 1.15)))
        self.log_text = tk.Text(
            bottom_frame,
            height=4,
            bg=self.card_bg,
            fg="#94a3b8",
            insertbackground="white",
            relief="flat",
            font=("Consolas", f_size_code),
            highlightthickness=1,
            highlightbackground=self.card_light
        )
        self.log_text.pack(fill="x")
        self.log("Ready. Click 'Scan Drivers' to inspect this Windows system.")

    def log(self, message: str):
        self.log_text.insert("end", f"> {message}\n")
        self.log_text.see("end")

    def _check_admin_banner(self):
        if is_admin():
            self.admin_badge_var.set("🟢 Administrator Mode")
            self.admin_badge_lbl.configure(foreground=self.accent_green)
        else:
            self.admin_badge_var.set("🟡 Standard User (Run as Admin for Updates)")
            self.admin_badge_lbl.configure(foreground=self.accent_amber)

    def start_scan(self):
        if self.is_scanning:
            return
        self.is_scanning = True
        self.progress_bar.start(10)
        self.log("Scanning hardware devices via pnputil and Windows CIM...")

        threading.Thread(target=self._run_scan_thread, daemon=True).start()

    def _run_scan_thread(self):
        try:
            devs = DriverScanner.scan_all_devices()
            self.devices = devs
            self.after(0, self._on_scan_complete)
        except Exception as e:
            self.after(0, lambda: self.log(f"Error scanning: {e}"))
            self.after(0, self._stop_progress)

    def _on_scan_complete(self):
        self._stop_progress()
        self.log(f"Scan complete. Detected {len(self.devices)} devices.")
        self.apply_filters()

    def _stop_progress(self):
        self.is_scanning = False
        self.progress_bar.stop()

    def apply_filters(self):
        cat = self.category_var.get()
        search = self.search_var.get().lower().strip()

        filtered = []
        for d in self.devices:
            if cat == "Errors / Missing":
                if not d.has_problem and d.status.lower() != "error":
                    continue
            elif cat != "All" and cat.lower() not in d.device_class.lower():
                continue

            if search:
                name_match = search in d.name.lower()
                id_match = search in d.matching_device_id.lower()
                prov_match = search in d.provider_name.lower()
                if not (name_match or id_match or prov_match):
                    continue

            filtered.append(d)

        self.filtered_devices = filtered
        self._populate_tree()

    def _populate_tree(self):
        self.tree.delete(*self.tree.get_children())
        for dev in self.filtered_devices:
            if dev.has_problem:
                status_text = "⚠️ Code " + str(dev.problem_code)
                tag = "problem"
            elif dev.available_update_version:
                status_text = "🔵 Update"
                tag = "update_ready"
            else:
                status_text = "🟢 OK"
                tag = "ok"

            update_text = dev.available_update_version or "—"

            self.tree.insert(
                "",
                "end",
                values=(
                    status_text,
                    dev.name,
                    dev.device_class,
                    dev.current_driver_version,
                    dev.current_driver_date,
                    update_text,
                    dev.provider_name or dev.manufacturer
                ),
                tags=(tag,)
            )

        self.stats_lbl.configure(text=f"{len(self.filtered_devices)} / {len(self.devices)} Devices")

    def on_device_selected(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            self.selected_device = None
            return
        idx = self.tree.index(selected_items[0])
        if idx < len(self.filtered_devices):
            self.selected_device = self.filtered_devices[idx]
            self.log(f"Selected: {self.selected_device.name} (ID: {self.selected_device.matching_device_id})")

    def start_online_check(self):
        if not self.devices:
            messagebox.showinfo("Scan Required", "Please scan the system first before checking online.")
            return

        self.progress_bar.start(10)
        self.log("Querying Microsoft Update Catalog for driver updates...")

        targets = [
            d for d in self.devices
            if d.device_class.lower() in ("net", "display", "media", "bluetooth")
            and d.matching_device_id
        ]

        threading.Thread(target=self._run_online_check_thread, args=(targets,), daemon=True).start()

    def _run_online_check_thread(self, targets: List[DeviceInfo]):
        updates_found = 0
        total = min(len(targets), 15)
        for i, dev in enumerate(targets[:total]):
            self.after(0, lambda d=dev, curr=i+1, tot=total: self.log(f"Checking [{curr}/{tot}] {d.name}..."))
            candidate = DriverFetcher.check_updates_for_device(
                dev.matching_device_id,
                dev.current_driver_version,
                dev.current_driver_date
            )
            if candidate:
                dev.available_update_version = candidate.version
                dev.available_update_date = candidate.date_str
                dev.download_url = candidate.download_url
                dev.update_title = candidate.title
                updates_found += 1
                self.after(0, lambda d=dev, c=candidate: self.log(f"✨ Update found for {d.name}: {c.version} ({c.date_str})"))

        self.after(0, lambda: self._on_online_check_finished(updates_found))

    def _on_online_check_finished(self, count: int):
        self._stop_progress()
        self.log(f"Online update check finished. {count} update(s) found.")
        self.apply_filters()
        if count > 0:
            messagebox.showinfo("Updates Available", f"Found {count} driver update(s) ready to install!")
        else:
            messagebox.showinfo("Up to date", "All checked devices are running the latest certified drivers.")

    def start_backup(self):
        dest_folder = filedialog.askdirectory(title="Select Driver Backup Destination Folder")
        if not dest_folder:
            return

        self.progress_bar.start(10)
        self.log(f"Backing up all OEM drivers to: {dest_folder}...")

        def _backup_worker():
            ok, msg = DriverBackupManager.create_driver_backup(dest_folder)
            self.after(0, self._stop_progress)
            self.after(0, lambda: self.log(msg))
            if ok:
                self.after(0, lambda: messagebox.showinfo("Backup Successful", msg))
            else:
                self.after(0, lambda: messagebox.showerror("Backup Failed", msg))

        threading.Thread(target=_backup_worker, daemon=True).start()

    def start_restore(self):
        backup_folder = filedialog.askdirectory(title="Select Driver Backup Folder to Restore From")
        if not backup_folder:
            return

        if not messagebox.askyesno("Confirm Restore", "Are you sure you want to reinstall drivers from this backup?"):
            return

        self.progress_bar.start(10)
        self.log(f"Restoring drivers from: {backup_folder}...")

        def _restore_worker():
            ok, msg = DriverBackupManager.restore_driver_backup(backup_folder)
            self.after(0, self._stop_progress)
            self.after(0, lambda: self.log(msg))
            if ok:
                self.after(0, lambda: messagebox.showinfo("Restore Finished", msg))
            else:
                self.after(0, lambda: messagebox.showerror("Restore Failed", msg))

        threading.Thread(target=_restore_worker, daemon=True).start()

    def update_selected_driver(self):
        if not self.selected_device:
            messagebox.showwarning("Select Device", "Please select a device from the list first.")
            return

        dev = self.selected_device
        if not dev.download_url:
            self.progress_bar.start(10)
            self.log(f"Searching online update for: {dev.name}...")

            def _search_single():
                candidate = DriverFetcher.check_updates_for_device(
                    dev.matching_device_id,
                    dev.current_driver_version,
                    dev.current_driver_date
                )
                self.after(0, self._stop_progress)
                if candidate:
                    dev.available_update_version = candidate.version
                    dev.available_update_date = candidate.date_str
                    dev.download_url = candidate.download_url
                    dev.update_title = candidate.title
                    self.after(0, self.apply_filters)
                    self.after(0, lambda: self._prompt_install(dev))
                else:
                    self.after(0, lambda: messagebox.showinfo("No Updates", f"No newer drivers found for '{dev.name}'."))

            threading.Thread(target=_search_single, daemon=True).start()
            return

        self._prompt_install(dev)

    def _prompt_install(self, dev: DeviceInfo):
        if not is_admin():
            messagebox.showwarning(
                "Administrator Rights Required",
                "Installing drivers requires Administrator privileges.\nPlease restart this app by right-clicking and selecting 'Run as administrator'."
            )
            return

        confirm = messagebox.askyesno(
            "Install Driver Update",
            f"Device: {dev.name}\n"
            f"Current Version: {dev.current_driver_version}\n"
            f"New Version: {dev.available_update_version}\n\n"
            f"Do you want to download and install this certified driver now?"
        )
        if not confirm:
            return

        self.progress_bar.start(10)
        staging_dir = os.path.join(os.environ.get("TEMP", "C:\\Temp"), "DriverUpdateStage")

        def _install_worker():
            ok, msg = DriverInstaller.update_from_url(
                dev.download_url,
                staging_dir,
                log_callback=lambda m: self.after(0, lambda msg=m: self.log(msg))
            )
            self.after(0, self._stop_progress)
            if ok:
                self.after(0, lambda: messagebox.showinfo("Success", f"{dev.name} updated successfully!\n{msg}"))
                self.after(0, self.start_scan)
            else:
                self.after(0, lambda: messagebox.showerror("Installation Failed", msg))

        threading.Thread(target=_install_worker, daemon=True).start()

    def open_device_manager(self):
        try:
            subprocess.Popen(["devmgmt.msc"], shell=True)
        except Exception as e:
            self.log(f"Could not open Device Manager: {e}")


def launch_gui():
    enable_high_dpi_awareness()
    app = DriverUpdaterApp()
    app.mainloop()


if __name__ == "__main__":
    launch_gui()
