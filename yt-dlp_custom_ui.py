import json
import re
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path
from tkinter import filedialog, messagebox
from urllib.parse import parse_qs, urlparse
import customtkinter as ctk

# --- Configuration & Constants ---
INVALID_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|]')
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[a-zA-Z]")
NUMBER_RE = re.compile(r"(\d+(?:\.\d+)?)")
SAVE_FOLDER_PLACEHOLDER = "choose your folder"
ICON_FILENAME = "icon.ico"

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# --- Helpers for Path Handling (Script vs PyInstaller) ---
def resource_path(relative_path: str) -> Path:
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).resolve().parent

    return base_path / relative_path


def get_app_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def find_binary(name: str, app_dir: Path) -> Path | None:
    local_candidate = app_dir / name
    if local_candidate.is_file():
        return local_candidate
    found = shutil.which(name)
    return Path(found) if found else None


# --- Global State for Binaries ---
APP_DIR = get_app_dir()
YTDLP_BIN = find_binary("yt-dlp.exe" if sys.platform == "win32" else "yt-dlp", APP_DIR)
FFMPEG_BIN = find_binary("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg", APP_DIR)


# --- String & Data Processing Utils ---
def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


def sanitize_filename(name: str) -> str:
    return INVALID_FILENAME_CHARS.sub("_", name).strip().rstrip(".")


def is_valid_video_url(text: str) -> tuple[bool, str]:
    if not text or any(ch.isspace() for ch in text):
        return False, "URL cannot be empty or contain spaces."
    try:
        parsed = urlparse(text)
    except ValueError:
        return False, "Malformed URL syntax."

    if parsed.scheme not in ("http", "https"):
        return False, "URL must start with http:// or https://."
    if not parsed.netloc or "." not in parsed.netloc:
        return False, "URL is missing a valid domain."

    host = parsed.netloc.lower().removeprefix("www.")
    path = parsed.path.rstrip("/")
    query = parse_qs(parsed.query)

    if host in ("youtube.com", "m.youtube.com"):
        if path == "/watch":
            video_ids = [v.strip() for v in query.get("v", []) if v.strip()]
            if not video_ids:
                return False, "YouTube /watch URL is missing a video ID (?v=...)."
        elif path == "":
            return False, "YouTube homepage URL does not point to a specific video."

    if host == "youtu.be" and not path.lstrip("/"):
        return False, "Short youtu.be URL is missing a video ID."

    return True, ""


def format_bytes(num_bytes: int | float | None) -> str:
    if not num_bytes or num_bytes <= 0:
        return "Unknown"
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024.0:
            return f"{size:.2f} {unit}"
        size /= 1024.0
    return f"{size:.2f} PB"


def format_duration(seconds: int | float | None) -> str:
    if seconds is None or seconds < 0:
        return "Unknown"
    total_sec = int(seconds)
    hrs, rem = divmod(total_sec, 3600)
    mins, secs = divmod(rem, 60)
    if hrs > 0:
        return f"{hrs}h {mins:02d}m {secs:02d}s"
    return f"{mins:02d}m {secs:02d}s"


def parse_size_to_bytes(text: str) -> float | None:
    cleaned = strip_ansi(text).strip()
    if not cleaned or cleaned.upper() in ("N/A", "NA", "UNKNOWN", "~"):
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*([KMGTP]?i?B)", cleaned, re.IGNORECASE)
    if not match:
        return None
    val = float(match.group(1))
    unit = match.group(2).upper()
    multipliers = {
        "B": 1.0,
        "KB": 1000.0,
        "KIB": 1024.0,
        "MB": 1000.0**2,
        "MIB": 1024.0**2,
        "GB": 1000.0**3,
        "GIB": 1024.0**3,
        "TB": 1000.0**4,
        "TIB": 1024.0**4,
    }
    return val * multipliers.get(unit, 1.0)


def parse_speed_to_bps(text: str) -> float | None:
    cleaned = strip_ansi(text).strip()
    if not cleaned or cleaned.upper() in ("N/A", "NA", "UNKNOWN"):
        return None
    match = re.search(r"(\d+(?:\.\d+)?)\s*([KMGTP]?i?B)/s", cleaned, re.IGNORECASE)
    if not match:
        return None
    val = float(match.group(1))
    unit = match.group(2).upper()
    multipliers = {
        "B": 1.0,
        "KB": 1000.0,
        "KIB": 1024.0,
        "MB": 1000.0**2,
        "MIB": 1024.0**2,
        "GB": 1000.0**3,
        "GIB": 1024.0**3,
        "TB": 1000.0**4,
        "TIB": 1024.0**4,
    }
    return val * multipliers.get(unit, 1.0)


# --- Main Application Class ---
class YTdlpCustomUIApp(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("YT-DLP MP4 Downloader")
        self.geometry("740x500")
        self.minsize(680, 460)

        # --- Set Application Icon ---
        # This utilizes resource_path to find icon.ico in both script and exe mode
        icon_path = resource_path(ICON_FILENAME)
        if icon_path.exists() and sys.platform == "win32":
            try:
                self.iconbitmap(str(icon_path))
            except Exception as e:
                print(f"Could not set icon: {e}")
        elif not icon_path.exists():
             print(f"Icon file not found at: {icon_path}. Ensure icon.ico is in project folder.")

        # --- App State ---
        self.is_busy = False
        self.url_verified = False
        self.process: subprocess.Popen | None = None
        self._fetch_after_id: str | None = None
        self._last_fetched_url: str = ""
        self._fetched_safe_title: str = ""
        self.output_dir_var = ctk.StringVar(value="")

        # Smooth progress-bar animation state
        self._target_progress: float = 0.0
        self._displayed_progress: float = 0.0
        self._anim_after_id: str | None = None

        # Live download ETA & heartbeat state
        self._download_start_time: float | None = None
        self._heartbeat_after_id: str | None = None
        self._latest_pct: float = 0.0
        self._latest_eta_text: str = "Calculating..."
        self._latest_speed_text: str = "—"
        self._latest_dl_size_text: str = "—"
        self._is_merging_phase: bool = False

        # --- Build UI ---
        self._build_ui()
        self._sync_download_button_state()
        self.refresh_folder_stats()

    # --- Internal Helpers ---
    def _get_effective_output_dir(self) -> Path:
        raw = self.output_dir_var.get().strip()
        if not raw or raw.lower() == SAVE_FOLDER_PLACEHOLDER.lower():
            return APP_DIR
        return Path(raw)

    def _validate_save_folder(self) -> Path | None:
        raw = self.output_dir_var.get().strip()
        if not raw or raw.lower() == SAVE_FOLDER_PLACEHOLDER.lower():
            self.status_label.configure(
                text="Warning: Save folder is empty. Please choose a folder first."
            )
            messagebox.showwarning(
                "Missing Save Folder",
                "Save Folder cannot be empty. Please choose or enter a folder before downloading.",
            )
            return None
        return Path(raw)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Top bar (Title & Theme switch)
        top_bar = ctk.CTkFrame(self, fg_color="transparent")
        top_bar.grid(row=0, column=0, padx=16, pady=(12, 4), sticky="ew")
        top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_bar,
            text="MP4 Video Downloader",
            font=ctk.CTkFont(size=18, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, sticky="w")

        self.theme_switch = ctk.CTkSegmentedButton(
            top_bar,
            values=["Dark", "Light"],
            command=self._on_theme_change,
        )
        self.theme_switch.set("Dark")
        self.theme_switch.grid(row=0, column=1, sticky="e")

        # Main Tabs
        self.tabs = ctk.CTkTabview(self, command=self._on_tab_changed)
        self.tabs.grid(row=1, column=0, padx=16, pady=(4, 16), sticky="nsew")

        self.download_tab = self.tabs.add("Downloader")
        self.library_tab = self.tabs.add("Folder MP4s")

        self._build_download_tab()
        self._build_library_tab()

    def _on_theme_change(self, mode: str) -> None:
        ctk.set_appearance_mode(mode)

    def _on_tab_changed(self) -> None:
        if self.tabs.get() == "Folder MP4s":
            self.refresh_folder_stats()

    def _build_download_tab(self) -> None:
        tab = self.download_tab
        tab.grid_columnconfigure(1, weight=1)

        # Row 0: Save Folder
        ctk.CTkLabel(tab, text="Save Folder:", anchor="w").grid(
            row=0, column=0, padx=(10, 8), pady=(10, 6), sticky="w"
        )
        self.folder_entry = ctk.CTkEntry(
            tab,
            textvariable=self.output_dir_var,
            placeholder_text=SAVE_FOLDER_PLACEHOLDER,
        )
        self.folder_entry.grid(row=0, column=1, padx=(0, 8), pady=(10, 6), sticky="ew")

        self.browse_btn = ctk.CTkButton(
            tab, text="Browse...", width=100, command=self.choose_folder
        )
        self.browse_btn.grid(row=0, column=2, padx=(0, 10), pady=(10, 6), sticky="e")

        # Row 1: URL
        ctk.CTkLabel(tab, text="Video URL:", anchor="w").grid(
            row=1, column=0, padx=(10, 8), pady=6, sticky="w"
        )
        self.url_var = ctk.StringVar()
        # Bind keystrokes/changes to trigger auto-fetch
        self.url_var.trace_add("write", self._on_url_changed)

        self.url_entry = ctk.CTkEntry(
            tab,
            textvariable=self.url_var,
            placeholder_text="Paste a valid video URL (e.g. https://www.youtube.com/watch?v=...)...",
        )
        self.url_entry.grid(row=1, column=1, padx=(0, 8), pady=6, sticky="ew")

        self.fetch_btn = ctk.CTkButton(
            tab,
            text="Re-Fetch",
            width=100,
            command=lambda: self.start_fetch_info(force=True),
        )
        self.fetch_btn.grid(row=1, column=2, padx=(0, 10), pady=6, sticky="e")

        # Row 2: Original Name (Read-only)
        ctk.CTkLabel(tab, text="Original File Name:", anchor="w").grid(
            row=2, column=0, padx=(10, 8), pady=6, sticky="w"
        )
        self.orig_name_entry = ctk.CTkEntry(tab, placeholder_text="Auto-fetched from URL...")
        self.orig_name_entry.configure(state="disabled")
        self.orig_name_entry.grid(
            row=2, column=1, columnspan=2, padx=(0, 10), pady=6, sticky="ew"
        )

        # Row 3: Custom Name (Optional)
        ctk.CTkLabel(tab, text="New File Name (Optional):", anchor="w").grid(
            row=3, column=0, padx=(10, 8), pady=6, sticky="w"
        )
        self.new_name_entry = ctk.CTkEntry(
            tab, placeholder_text="Optional: leave blank to keep original title..."
        )
        self.new_name_entry.grid(
            row=3, column=1, columnspan=2, padx=(0, 10), pady=6, sticky="ew"
        )

        # Row 4: Video Info Card
        ctk.CTkLabel(tab, text="Video Info:", anchor="w").grid(
            row=4, column=0, padx=(10, 8), pady=6, sticky="nw"
        )
        info_card = ctk.CTkFrame(tab, corner_radius=8)
        info_card.grid(row=4, column=1, columnspan=2, padx=(0, 10), pady=6, sticky="ew")
        info_card.grid_columnconfigure(0, weight=1)

        self.info_label = ctk.CTkLabel(
            info_card,
            text="Resolution: —  |  Duration: —  |  Est. Size: —  |  Saved Size: —",
            anchor="w",
            justify="left",
        )
        self.info_label.grid(row=0, column=0, padx=10, pady=8, sticky="ew")

        # Row 5: Progress Bar
        ctk.CTkLabel(tab, text="Progress:", anchor="w").grid(
            row=5, column=0, padx=(10, 8), pady=6, sticky="w"
        )
        self.progress_bar = ctk.CTkProgressBar(tab, height=18)
        self.progress_bar.set(0)
        self.progress_bar.grid(
            row=5, column=1, columnspan=2, padx=(0, 10), pady=6, sticky="ew"
        )

        # Row 6: Status Label
        ctk.CTkLabel(tab, text="Est. Time & Status:", anchor="w").grid(
            row=6, column=0, padx=(10, 8), pady=6, sticky="w"
        )
        self.status_label = ctk.CTkLabel(
            tab, text="Enter a valid video URL to enable download.", anchor="w"
        )
        self.status_label.grid(
            row=6, column=1, columnspan=2, padx=(0, 10), pady=6, sticky="ew"
        )

        # Row 7: Download Button
        self.download_btn = ctk.CTkButton(
            tab, text="Download MP4", height=36, command=self.start_download
        )
        self.download_btn.grid(
            row=7, column=1, columnspan=2, padx=(0, 10), pady=(10, 8), sticky="e"
        )

    def _build_library_tab(self) -> None:
        tab = self.library_tab
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # Header
        header = ctk.CTkFrame(tab, corner_radius=8)
        header.grid(row=0, column=0, padx=10, pady=(10, 6), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        folder = self._get_effective_output_dir()
        self.library_path_label = ctk.CTkLabel(
            header, text=f"Folder: {folder}", anchor="w"
        )
        self.library_path_label.grid(row=0, column=0, padx=12, pady=(8, 2), sticky="ew")

        self.library_summary_label = ctk.CTkLabel(
            header,
            text="MP4 Count: 0  |  Total MP4 Size: 0.00 B",
            font=ctk.CTkFont(size=14, weight="bold"),
            anchor="w",
        )
        self.library_summary_label.grid(row=1, column=0, padx=12, pady=(2, 8), sticky="ew")

        self.refresh_btn = ctk.CTkButton(
            header, text="Refresh", width=95, command=self.refresh_folder_stats
        )
        self.refresh_btn.grid(row=0, column=1, rowspan=2, padx=(0, 12), pady=8, sticky="e")

        # File List
        ctk.CTkLabel(tab, text="Downloaded MP4 Files:", anchor="w").grid(
            row=1, column=0, padx=12, pady=(4, 2), sticky="w"
        )

        self.file_list_box = ctk.CTkTextbox(tab, state="disabled")
        self.file_list_box.grid(row=2, column=0, padx=10, pady=(2, 10), sticky="nsew")

    # --- Progress animation & live heartbeat helpers ---
    def _reset_progress_bar(self) -> None:
        if self._anim_after_id is not None:
            self.after_cancel(self._anim_after_id)
            self._anim_after_id = None
        self._target_progress = 0.0
        self._displayed_progress = 0.0
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self.progress_bar.set(0.0)

    def _start_smooth_glide(self) -> None:
        if self._anim_after_id is not None:
            return
        self._glide_step()

    def _glide_step(self) -> None:
        diff = self._target_progress - self._displayed_progress
        if abs(diff) < 0.002:
            self._displayed_progress = self._target_progress
            self.progress_bar.set(self._displayed_progress)
            self._anim_after_id = None
            return

        self._displayed_progress += diff * 0.18
        self.progress_bar.set(max(0.0, min(1.0, self._displayed_progress)))
        self._anim_after_id = self.after(20, self._glide_step)

    def _set_target_progress(self, fraction: float) -> None:
        self.progress_bar.stop()
        self.progress_bar.configure(mode="determinate")
        self._target_progress = max(0.0, min(1.0, fraction))
        self._start_smooth_glide()

    def _start_indeterminate_bar(self) -> None:
        if self._anim_after_id is not None:
            self.after_cancel(self._anim_after_id)
            self._anim_after_id = None
        self.progress_bar.configure(mode="indeterminate")
        self.progress_bar.start()

    def _start_heartbeat(self) -> None:
        self._stop_heartbeat()
        self._download_start_time = time.monotonic()
        self._tick_heartbeat()

    def _stop_heartbeat(self) -> None:
        if self._heartbeat_after_id is not None:
            self.after_cancel(self._heartbeat_after_id)
            self._heartbeat_after_id = None

    def _tick_heartbeat(self) -> None:
        if not self.is_busy or self._download_start_time is None:
            self._heartbeat_after_id = None
            return

        elapsed_str = format_duration(time.monotonic() - self._download_start_time)
        if self._is_merging_phase:
            self.status_label.configure(
                text=f"Converting / merging to MP4 via FFmpeg...  |  Elapsed: {elapsed_str} (still working)"
            )
        else:
            self.status_label.configure(
                text=f"{self._latest_pct:.1f}%  |  Est. Remaining: {self._latest_eta_text}  |  Speed: {self._latest_speed_text}  |  Downloaded: {self._latest_dl_size_text}  |  Elapsed: {elapsed_str}"
            )

        self._heartbeat_after_id = self.after(1000, self._tick_heartbeat)

    # --- Folder & library helpers ---
    def choose_folder(self) -> None:
        if self.is_busy:
            return
        current = self._get_effective_output_dir()
        # Set initial dir for dialog, fallback to app dir if current isn't valid
        initial_dir = str(current if current.exists() else APP_DIR)
        selected = filedialog.askdirectory(title="Select Output Folder", initialdir=initial_dir)
        if selected:
            self.output_dir_var.set(selected)
            self.refresh_folder_stats()

    def refresh_folder_stats(self) -> None:
        folder = self._get_effective_output_dir()
        self.library_path_label.configure(text=f"Folder: {folder}")

        if not folder.exists() or not folder.is_dir():
            self.library_summary_label.configure(
                text="MP4 Count: 0  |  Total MP4 Size: Folder does not exist"
            )
            self._set_file_list_text("Folder does not exist yet.")
            return

        # List MP4s, sort by name
        mp4_files = sorted(
            [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == ".mp4"],
            key=lambda p: p.name.lower(),
        )
        total_bytes = 0
        lines: list[str] = []
        for mp4 in mp4_files:
            try:
                sz = mp4.stat().st_size
            except OSError:
                sz = 0
            total_bytes += sz
            lines.append(f"• {mp4.name}  —  {format_bytes(sz)}")

        self.library_summary_label.configure(
            text=f"MP4 Count: {len(mp4_files)}  |  Total MP4 Size: {format_bytes(total_bytes)}"
        )
        self._set_file_list_text(
            "\n".join(lines) if lines else "No .mp4 files found in this folder."
        )

    def _set_file_list_text(self, content: str) -> None:
        self.file_list_box.configure(state="normal")
        self.file_list_box.delete("1.0", "end")
        self.file_list_box.insert("1.0", content)
        self.file_list_box.configure(state="disabled")

    # --- URL validation & metadata auto-fetch ---
    def _sync_download_button_state(self) -> None:
        url = self.url_var.get().strip()
        valid_syntax, _ = is_valid_video_url(url)
        # Enabled only if not busy, syntax is ok, and fetch succeeded
        can_download = (not self.is_busy) and valid_syntax and self.url_verified
        self.download_btn.configure(state="normal" if can_download else "disabled")

    def _clear_fetched_preview(self) -> None:
        self._last_fetched_url = ""
        self._fetched_safe_title = ""
        self._set_orig_name("")
        self.info_label.configure(
            text="Resolution: —  |  Duration: —  |  Est. Size: —  |  Saved Size: —"
        )

    def _on_url_changed(self, *_args: object) -> None:
        if self._fetch_after_id is not None:
            self.after_cancel(self._fetch_after_id)
            self._fetch_after_id = None

        url = self.url_var.get().strip()
        self.url_verified = False

        if not url:
            self._clear_fetched_preview()
            self._sync_download_button_state()
            if not self.is_busy:
                self.status_label.configure(text="Enter a valid video URL to enable download.")
            return

        valid_syntax, reason = is_valid_video_url(url)
        if not valid_syntax:
            self._clear_fetched_preview()
            self._sync_download_button_state()
            if not self.is_busy:
                self.status_label.configure(text=f"Error: {reason} Download disabled.")
            return

        self._sync_download_button_state()
        # Small delay before auto-fetching (debounce)
        if not self.is_busy:
            self._fetch_after_id = self.after(600, lambda u=url: self.start_fetch_info(url=u))

    def _set_busy(self, busy: bool) -> None:
        self.is_busy = busy
        state = "disabled" if busy else "normal"
        for widget in (
            self.browse_btn,
            self.fetch_btn,
            self.folder_entry,
            self.url_entry,
            self.new_name_entry,
        ):
            widget.configure(state=state)
        self._sync_download_button_state()

    def _set_orig_name(self, text: str) -> None:
        self.orig_name_entry.configure(state="normal")
        self.orig_name_entry.delete(0, "end")
        self.orig_name_entry.insert(0, text)
        self.orig_name_entry.configure(state="disabled")

    def _check_binaries(self, silent: bool = False) -> bool:
        ytdlp = find_binary("yt-dlp.exe" if sys.platform == "win32" else "yt-dlp", APP_DIR)
        ffmpeg = find_binary("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg", APP_DIR)
        global YTDLP_BIN, FFMPEG_BIN
        YTDLP_BIN = ytdlp
        FFMPEG_BIN = ffmpeg

        if YTDLP_BIN is None:
            if not silent:
                messagebox.showerror(
                    "Missing yt-dlp",
                    f"yt-dlp was not found in:\n{APP_DIR}\n\nor in your system PATH.",
                )
            return False
        if FFMPEG_BIN is None and not silent:
            messagebox.showwarning(
                "FFmpeg Not Found",
                f"ffmpeg was not found in:\n{APP_DIR}\n\nor in your system PATH. Merging or MP4 conversion may fail.",
            )
        return True

    def start_fetch_info(self, url: str | None = None, force: bool = False) -> None:
        if self.is_busy:
            return
        target_url = (url if url is not None else self.url_var.get()).strip()
        valid_syntax, reason = is_valid_video_url(target_url)
        if not valid_syntax:
            self.url_verified = False
            self._clear_fetched_preview()
            self._sync_download_button_state()
            self.status_label.configure(text=f"Error: {reason} Download disabled.")
            if force:
                messagebox.showerror("Invalid URL", f"{reason}\n\nDownload button is disabled.")
            return

        if not self._check_binaries(silent=not force):
            self.url_verified = False
            self._sync_download_button_state()
            return

        self._set_busy(True)
        self.status_label.configure(text="Validating URL and fetching video info...")
        threading.Thread(
            target=self._fetch_info_worker, args=(target_url, force), daemon=True
        ).start()

    def _fetch_info_worker(self, url: str, show_popup_on_error: bool) -> None:
        assert YTDLP_BIN is not None
        cmd = [
            str(YTDLP_BIN),
            "--no-playlist",
            "--no-color",
            "--dump-single-json",
            "--no-warnings",
            url,
        ]
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
            if proc.returncode != 0 or not proc.stdout.strip():
                err_lines = strip_ansi(proc.stderr.strip()).splitlines()
                short_err = err_lines[-1] if err_lines else "Unable to extract video metadata."
                self.after(
                    0, lambda msg=short_err, pop=show_popup_on_error: self._on_fetch_error(msg, pop)
                )
                return

            data = json.loads(proc.stdout.splitlines()[-1])

            formats = data.get("formats") or []
            has_direct_url = bool(data.get("url"))
            if not formats and not has_direct_url:
                self.after(
                    0,
                    lambda pop=show_popup_on_error: self._on_fetch_error(
                        "No downloadable media stream found at this URL.", pop
                    ),
                )
                return

            title = (data.get("title") or "").strip()
            if not title or title.lower() in ("youtube", "watch"):
                self.after(
                    0,
                    lambda pop=show_popup_on_error: self._on_fetch_error(
                        "URL does not point to a valid video item.", pop
                    ),
                )
                return

            safe_title = sanitize_filename(title) or "downloaded_video"

            width = data.get("width")
            height = data.get("height")
            if width and height:
                resolution = f"{width}x{height} ({height}p)"
            elif height:
                resolution = f"{height}p"
            else:
                resolution = "Unknown"

            duration_str = format_duration(data.get("duration"))
            est_bytes = data.get("filesize") or data.get("filesize_approx")
            est_size_str = format_bytes(est_bytes)

            self.after(
                0,
                lambda u=url, t=title, st=safe_title, r=resolution, d=duration_str, es=est_size_str: (
                    self._on_fetch_success(u, t, st, r, d, es)
                ),
            )
        except Exception as exc:
            self.after(
                0,
                lambda msg=str(exc), pop=show_popup_on_error: self._on_fetch_error(msg, pop),
            )

    def _on_fetch_success(
        self,
        url: str,
        original_title: str,
        safe_title: str,
        resolution: str,
        duration_str: str,
        est_size_str: str,
    ) -> None:
        self._last_fetched_url = url
        self._fetched_safe_title = safe_title
        self.url_verified = True
        self._set_orig_name(f"{original_title}.mp4")
        # Clear custom name entry on new successful fetch
        self.new_name_entry.delete(0, "end")
        self.info_label.configure(
            text=f"Resolution: {resolution}  |  Duration: {duration_str}  |  Est. Size: {est_size_str}  |  Saved Size: Pending"
        )
        self.status_label.configure(
            text="Valid video URL — ready to download MP4 (rename is optional)."
        )
        self._set_busy(False)

    def _on_fetch_error(self, detail: str = "", show_popup: bool = True) -> None:
        self.url_verified = False
        self._clear_fetched_preview()
        self.status_label.configure(
            text="Error: Invalid or non-video URL. Download button disabled."
        )
        self._set_busy(False)
        if show_popup:
            messagebox.showerror(
                "Invalid URL",
                f"Invalid or unsupported video URL:\n{detail}\n\nDownload has been disabled.",
            )

    # --- Download & MP4 conversion ---
    def start_download(self) -> None:
        if self.is_busy or not self._check_binaries():
            return

        # Double check URL integrity before starting
        url = self.url_var.get().strip()
        valid_syntax, reason = is_valid_video_url(url)
        if not valid_syntax or not self.url_verified or url != self._last_fetched_url:
            self.url_verified = False
            self._sync_download_button_state()
            msg = reason or "URL is not a verified playable video link."
            self.status_label.configure(text=f"Error: {msg} Download disabled.")
            messagebox.showerror("Invalid URL", f"{msg}\n\nDownload button is disabled.")
            return

        out_dir = self._validate_save_folder()
        if out_dir is None:
            return

        raw_new_name = self.new_name_entry.get().strip()
        # Remove .mp4 if user typed it
        if raw_new_name.lower().endswith(".mp4"):
            raw_new_name = raw_new_name[:-4].strip()

        clean_name = sanitize_filename(raw_new_name)
        # Fallback to original title if custom name is empty
        effective_stem = clean_name if clean_name else self._fetched_safe_title

        out_dir.mkdir(parents=True, exist_ok=True)

        if effective_stem:
            candidate_mp4 = out_dir / f"{effective_stem}.mp4"
            if candidate_mp4.exists():
                proceed = messagebox.askyesno(
                    "Duplicate File Name Warning",
                    f"A file named '{candidate_mp4.name}' already exists in:\n{out_dir}\n\nDo you want to overwrite it?",
                )
                if not proceed:
                    self.status_label.configure(
                        text="Download cancelled due to duplicate file name."
                    )
                    return

        self._latest_pct = 0.0
        self._latest_eta_text = "Calculating..."
        self._latest_speed_text = "—"
        self._latest_dl_size_text = "—"
        self._is_merging_phase = False

        self._reset_progress_bar()
        self.status_label.configure(
            text="Starting download...  |  Est. Remaining: Calculating...  |  Elapsed: 00m 00s"
        )
        self._set_busy(True)
        self._start_heartbeat()

        # Start download in background thread
        threading.Thread(
            target=self._download_worker, args=(url, effective_stem, out_dir), daemon=True
        ).start()

    def _download_worker(self, url: str, target_stem: str, out_dir: Path) -> None:
        assert YTDLP_BIN is not None
        output_template = str(out_dir / f"{target_stem}.%(ext)s")
        progress_tpl = (
            "download:"
            "%(progress._percent_str)s|"
            "%(progress._eta_str)s|"
            "%(progress._speed_str)s|"
            "%(progress._downloaded_bytes_str)s|"
            "%(progress._total_bytes_estimate_str)s"
        )
        cmd = [
            str(YTDLP_BIN),
            "--no-playlist",
            "--no-color",
            "--newline",
            "--progress-template",
            progress_tpl,
            "--print",
            "after_move:filepath",
            "--merge-output-format",
            "mp4",
            "--remux-video",
            "mp4",
            "-o",
            output_template,
            url,
        ]
        if FFMPEG_BIN is not None:
            cmd.extend(["--ffmpeg-location", str(FFMPEG_BIN.parent)])

        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        final_filepath_str = ""

        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )
            assert self.process.stdout is not None

            for raw_line in self.process.stdout:
                line = strip_ansi(raw_line).strip()
                if not line:
                    continue
                if line.startswith("download:"):
                    payload = line.removeprefix("download:")
                    parts = payload.split("|")
                    pct_raw = parts[0].strip() if len(parts) > 0 else ""
                    eta_raw = parts[1].strip() if len(parts) > 1 else ""
                    speed_raw = parts[2].strip() if len(parts) > 2 else ""
                    dl_raw = parts[3].strip() if len(parts) > 3 else ""
                    total_raw = parts[4].strip() if len(parts) > 4 else ""

                    pct_match = NUMBER_RE.search(pct_raw)
                    pct_val = (
                        max(0.0, min(100.0, float(pct_match.group(1))))
                        if pct_match
                        else self._latest_pct
                    )

                    # Handle ETA N/A
                    eta_display = (
                        eta_raw if eta_raw and eta_raw.upper() not in ("N/A", "NA", "UNKNOWN") else ""
                    )
                    if not eta_display:
                        dl_b = parse_size_to_bytes(dl_raw)
                        tot_b = parse_size_to_bytes(total_raw)
                        spd_bps = parse_speed_to_bps(speed_raw)
                        if (
                            dl_b is not None
                            and tot_b is not None
                            and spd_bps
                            and spd_bps > 0
                            and tot_b > dl_b
                        ):
                            eta_display = format_duration((tot_b - dl_b) / spd_bps)
                        else:
                            eta_display = "Calculating..."

                    speed_display = (
                        speed_raw
                        if speed_raw and speed_raw.upper() not in ("N/A", "NA", "UNKNOWN")
                        else "—"
                    )
                    dl_display = (
                        f"{dl_raw} / {total_raw}"
                        if dl_raw
                        and total_raw
                        and total_raw.upper() not in ("N/A", "NA", "UNKNOWN")
                        else (dl_raw or "—")
                    )

                    self.after(
                        0,
                        lambda p=pct_val, e=eta_display, s=speed_display, d=dl_display: (
                            self._update_progress(p, e, s, d)
                        ),
                    )
                elif "[Merger]" in line or "[VideoRemuxer]" in line or "Converting" in line:
                    self.after(0, self._on_merging_start)
                elif line.lower().endswith(".mp4") and not line.startswith("["):
                    final_filepath_str = line

            rc = self.process.wait()
            self.process = None

            if rc == 0:
                resolved_path = (
                    Path(final_filepath_str)
                    if final_filepath_str
                    else out_dir / f"{target_stem}.mp4"
                )
                self.after(0, lambda p=resolved_path: self._on_download_complete(p))
            else:
                self.after(0, lambda: self._on_download_failed(rc))
        except Exception as exc:
            self.process = None
            self.after(0, lambda: self._on_download_failed(-1, str(exc)))

    def _update_progress(self, pct: float, eta: str, speed: str, dl_size: str) -> None:
        self._is_merging_phase = False
        self._latest_pct = pct
        self._latest_eta_text = eta
        self._latest_speed_text = speed
        self._latest_dl_size_text = dl_size
        self._set_target_progress(pct / 100.0)

        elapsed_str = (
            format_duration(time.monotonic() - self._download_start_time)
            if self._download_start_time is not None
            else "00m 00s"
        )
        self.status_label.configure(
            text=f"{pct:.1f}%  |  Est. Remaining: {eta}  |  Speed: {speed}  |  Downloaded: {dl_size}  |  Elapsed: {elapsed_str}"
        )

    def _on_merging_start(self) -> None:
        self._is_merging_phase = True
        self._start_indeterminate_bar()
        elapsed_str = (
            format_duration(time.monotonic() - self._download_start_time)
            if self._download_start_time is not None
            else "00m 00s"
        )
        self.status_label.configure(
            text=f"Converting / merging to MP4 via FFmpeg...  |  Elapsed: {elapsed_str} (still working)"
        )

    def _on_download_complete(self, out_path: Path) -> None:
        self._stop_heartbeat()
        self._set_target_progress(1.0)
        elapsed_str = (
            format_duration(time.monotonic() - self._download_start_time)
            if self._download_start_time is not None
            else "Unknown"
        )
        saved_size_str = format_bytes(out_path.stat().st_size) if out_path.exists() else "Unknown"

        # Update info card with actual size
        current_info = self.info_label.cget("text")
        if "Saved Size:" in current_info:
            base_part = current_info.split("Saved Size:")[0]
            self.info_label.configure(text=f"{base_part}Saved Size: {saved_size_str}")

        self.status_label.configure(
            text=f"Completed in {elapsed_str}: {out_path.name} ({saved_size_str})"
        )
        self.refresh_folder_stats()
        self._set_busy(False)
        messagebox.showinfo(
            "Done",
            f"MP4 saved to:\n{out_path}\n\nSaved Size: {saved_size_str}\nTotal Time: {elapsed_str}",
        )

    def _on_download_failed(self, code: int, detail: str = "") -> None:
        self._stop_heartbeat()
        self._reset_progress_bar()
        self.status_label.configure(text=f"Failed (exit code {code}).")
        self._set_busy(False)
        msg = detail or "Download or MP4 conversion failed. Verify URL and yt-dlp."
        messagebox.showerror("Error", msg)


# --- Main Entry Point ---
def main() -> int:
    app = YTdlpCustomUIApp()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())