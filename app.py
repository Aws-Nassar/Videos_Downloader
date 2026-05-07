"""
MediaFlow Pro - desktop media downloader.

Built with CustomTkinter + yt-dlp.
"""

import customtkinter as ctk
import threading
import json
import os
import subprocess
import sys
import time
import re
import io
import urllib.request
import ctypes
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None
    ImageOps = None

# ── yt-dlp import ────────────────────────────────────────────────────────────
try:
    import yt_dlp
except ImportError:
    import tkinter.messagebox as mb
    mb.showerror("Missing Dependency",
        "yt-dlp is not installed.\n\nRun:\n  pip install yt-dlp")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════════════════════
#  Constants & Defaults
# ═══════════════════════════════════════════════════════════════════════════════
APP_NAME     = "MediaFlow Pro"
VERSION      = "2.1"
APP_DIR      = Path(__file__).resolve().parent
CONFIG_FILE  = Path.home() / ".ytflow2_config.json"
HISTORY_FILE = Path.home() / ".ytflow2_history.json"
THUMBNAIL_SIZE = (128, 72)
ICON_FILE = "mediaflow.ico"
ICON_PNG_FILE = "mediaflow.png"

DEFAULT_CONFIG = {
    "theme":       "dark",
    "output_dir":  str(Path.home() / "Downloads"),
    "max_history": 100,
    "ffmpeg_path": "",
    "concurrent":  "1",
    "cookie_file": "",
    "browser_cookies": "None",
}

SUPPORTED_SOURCE_HINTS = [
    "YouTube", "Facebook", "Instagram", "TikTok", "X/Twitter",
    "Vimeo", "SoundCloud", "Google Drive", "Twitch", "Reddit",
]
BROWSER_COOKIE_SOURCES = ["None", "Chrome", "Edge", "Firefox", "Brave", "Opera", "Vivaldi", "Chromium"]

VIDEO_FORMATS   = ["mp4", "mkv", "webm", "avi", "mov", "flv"]
AUDIO_FORMATS   = ["mp3", "m4a", "aac", "opus", "flac", "wav", "ogg"]
VIDEO_QUALITIES = [
    "Best Available", "4320p (8K)", "2160p (4K)", "1440p (2K)",
    "1080p (FHD)", "720p (HD)", "480p", "360p", "240p", "144p", "Worst"
]
AUDIO_QUALITIES = ["Best", "320 kbps", "256 kbps", "192 kbps",
                   "128 kbps", "96 kbps", "64 kbps", "Worst"]

# ── Dark palette ─────────────────────────────────────────────────────────────
BG_ROOT  = "#1A1D23"
BG_PANEL = "#21252E"
BG_CARD  = "#282D38"
BG_INPUT = "#1E2229"
TXT_PRI  = "#E8ECF4"
TXT_SEC  = "#8891A4"
TXT_DIM  = "#4D5568"
BORDER   = "#2E3441"
ACCENT   = "#2B7DE9"
SUCCESS  = "#22C55E"
ERROR    = "#F43F5E"
WARN     = "#F59E0B"


# ═══════════════════════════════════════════════════════════════════════════════
#  Persistence helpers
# ═══════════════════════════════════════════════════════════════════════════════
def load_config():
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, encoding="utf-8") as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
    except Exception:
        pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception:
        pass

def load_history():
    try:
        if HISTORY_FILE.exists():
            with open(HISTORY_FILE, encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return []

def save_history(h):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(h, f, indent=2)
    except Exception:
        pass


def resource_path(*parts):
    base = Path(getattr(sys, "_MEIPASS", APP_DIR))
    return base.joinpath(*parts)


def clean_error_text(msg):
    msg = str(msg).strip()
    msg = re.sub(r"\x1b\[[0-9;]*m", "", msg)
    msg = re.sub(r"^ERROR:\s*", "", msg, flags=re.IGNORECASE)
    msg = re.sub(r"\s+", " ", msg)
    return msg or "The downloader could not complete this request."


def classify_error(msg):
    lower = msg.lower()
    if "errno 22" in lower or "invalid argument" in lower or "filename" in lower:
        return (
            "Windows could not create the output file",
            "The media title contains characters that are not valid in a Windows filename. "
            "MediaFlow now uses safer filenames; try the download again.",
            ["Retry the download", "Choose a shorter save folder path", "Update yt-dlp if the issue continues"],
        )
    if "unsupported url" in lower or "no suitable extractor" in lower:
        return (
            "This link is not supported",
            "yt-dlp does not have an extractor for this URL, or the page is not a direct media link.",
            ["Open the link in your browser and copy the media post URL", "Check that the post is public"],
        )
    if "private" in lower or "login" in lower or "cookies" in lower or "permission" in lower:
        return (
            "This media needs access permission",
            "The site is asking for a logged-in session or the link is private.",
            ["In Settings, select your browser under Use Browser Cookies", "Or provide a cookies.txt file", "Confirm the link opens in your browser"],
        )
    if "not a video" in lower or "no video" in lower or "requested format is not available" in lower:
        return (
            "No downloadable video was found",
            "The page loaded, but yt-dlp could not find a media stream matching your selected options.",
            ["Try Audio mode if the source is audio-only", "Try Best Available", "Confirm the URL points to a playable media page"],
        )
    if "ffmpeg" in lower:
        return (
            "FFmpeg is missing or unavailable",
            "FFmpeg is required for merging streams, extracting audio, and converting formats.",
            ["Install FFmpeg and add it to PATH", "Or set the FFmpeg folder in Settings"],
        )
    if "network" in lower or "timed out" in lower or "connection" in lower:
        return (
            "Network problem",
            "The site did not respond reliably while MediaFlow was fetching the media.",
            ["Check your internet connection", "Retry in a moment", "Open the link in your browser"],
        )
    return (
        "Download failed",
        "MediaFlow could not process this link.",
        ["Check the URL", "Try cookies for restricted sites", "Try another format or quality"],
    )


class ErrorDialog(ctk.CTkToplevel):
    def __init__(self, parent, title, message, details="", suggestions=None):
        super().__init__(parent)
        self.title(title)
        self.configure(fg_color=BG_ROOT)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        suggestions = suggestions or []

        card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=10)
        card.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)
        card.grid_columnconfigure(1, weight=1)

        icon = ctk.CTkFrame(card, width=42, height=42, fg_color="#3A1F2B", corner_radius=21)
        icon.grid(row=0, column=0, padx=(16, 12), pady=(16, 8), sticky="n")
        icon.grid_propagate(False)
        ctk.CTkLabel(icon, text="!", font=ctk.CTkFont("Segoe UI", 20, weight="bold"),
                     text_color=ERROR).place(relx=.5, rely=.48, anchor="center")

        ctk.CTkLabel(card, text=title, font=ctk.CTkFont("Segoe UI", 17, weight="bold"),
                     text_color=TXT_PRI, anchor="w").grid(row=0, column=1, padx=(0, 18), pady=(16, 4), sticky="ew")
        ctk.CTkLabel(card, text=message, font=ctk.CTkFont("Segoe UI", 12),
                     text_color=TXT_SEC, anchor="w", justify="left", wraplength=440
                     ).grid(row=1, column=1, padx=(0, 18), pady=(0, 10), sticky="ew")

        if suggestions:
            tips = "\n".join(f"- {tip}" for tip in suggestions)
            ctk.CTkLabel(card, text=tips, font=ctk.CTkFont("Segoe UI", 11),
                         text_color=TXT_SEC, anchor="w", justify="left", wraplength=440
                         ).grid(row=2, column=1, padx=(0, 18), pady=(0, 12), sticky="ew")

        if details:
            detail_box = ctk.CTkTextbox(card, height=78, fg_color=BG_INPUT,
                                        text_color=TXT_DIM, border_color=BORDER,
                                        border_width=1, corner_radius=8, wrap="word")
            detail_box.grid(row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 12))
            detail_box.insert("1.0", details)
            detail_box.configure(state="disabled")

        ctk.CTkButton(card, text="OK", width=96, height=34, fg_color=ACCENT,
                      hover_color="#1D65CA", command=self.destroy
                      ).grid(row=4, column=0, columnspan=2, padx=16, pady=(0, 16), sticky="e")

        self.update_idletasks()
        w, h = 560, self.winfo_reqheight()
        x = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
        y = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


# ═══════════════════════════════════════════════════════════════════════════════
#  yt-dlp helpers
# ═══════════════════════════════════════════════════════════════════════════════
def apply_auth_opts(opts, cfg):
    cookie_file = str(cfg.get("cookie_file", "")).strip()
    if cookie_file:
        opts["cookiefile"] = cookie_file

    browser = str(cfg.get("browser_cookies", "None")).strip()
    if browser and browser.lower() != "none":
        opts["cookiesfrombrowser"] = (browser.lower(),)

    return opts


def fmt_duration(secs):
    if not secs:
        return ""
    secs = int(secs)
    h, r = divmod(secs, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def fmt_size(b):
    if not b:
        return ""
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"

def build_ydl_opts(cfg, out_dir, ext, quality, is_audio, progress_hook,
                   subs=False, embed_thumb=False, sponsor_block=False,
                   playlist=False):
    os.makedirs(out_dir, exist_ok=True)
    if playlist:
        outtmpl = os.path.join(
            out_dir,
            "%(playlist_title).80B",
            "%(playlist_index)03d - %(title).100B [%(id)s].%(ext)s",
        )
    else:
        outtmpl = os.path.join(out_dir, "%(title).120B [%(id)s].%(ext)s")
    postprocessors = []

    if is_audio:
        q_map = {
            "Best": "0", "320 kbps": "320", "256 kbps": "256",
            "192 kbps": "192", "128 kbps": "128",
            "96 kbps": "96", "64 kbps": "64", "Worst": "9",
        }
        aq = q_map.get(quality, "0")
        postprocessors.append({
            "key": "FFmpegExtractAudio",
            "preferredcodec": ext,
            "preferredquality": aq,
        })
        fmt = "bestaudio/best" if quality != "Worst" else "worstaudio/worst"
    else:
        height = None
        if quality not in ("Best Available", "Worst"):
            m = re.match(r"(\d+)p", quality)
            if m:
                height = int(m.group(1))
        if quality == "Worst":
            fmt = "worstvideo+worstaudio/worst"
        elif height:
            fmt = (f"bestvideo[height<={height}]+bestaudio/"
                   f"bestvideo[height<={height}]+bestaudio/best")
        else:
            fmt = "bestvideo+bestaudio/best"
        postprocessors.append({
            "key": "FFmpegVideoConvertor",
            "preferedformat": ext,
        })

    if embed_thumb:
        postprocessors.append({"key": "EmbedThumbnail"})
    if subs:
        postprocessors.append({
            "key": "FFmpegEmbedSubtitle",
            "already_have_subtitle": False,
        })
    if sponsor_block:
        postprocessors.append({"key": "SponsorBlock"})
        postprocessors.append({
            "key": "ModifyChapters",
            "remove_sponsor_segments": ["sponsor", "intro", "outro", "selfpromo"],
        })

    try:
        conc = int(cfg.get("concurrent", 1))
    except (ValueError, TypeError):
        conc = 1

    opts = {
        "format":          fmt,
        "outtmpl":         outtmpl,
        "progress_hooks":  [progress_hook],
        "postprocessors":  postprocessors,
        "quiet":           True,
        "no_warnings":     True,
        "merge_output_format": ext if not is_audio else None,
        "noplaylist":      not playlist,
        "writesubtitles":  subs,
        "subtitleslangs":  ["en"] if subs else [],
        "writethumbnail":  embed_thumb,
        "concurrent_fragment_downloads": conc,
        "retries":         5,
        "fragment_retries": 5,
        "windowsfilenames": True,
        "restrictfilenames": True,
        "trim_file_name": 160,
    }
    ffmpeg = cfg.get("ffmpeg_path", "").strip()
    if ffmpeg:
        opts["ffmpeg_location"] = ffmpeg
    return apply_auth_opts(opts, cfg)


# ═══════════════════════════════════════════════════════════════════════════════
#  Main Application Window
# ═══════════════════════════════════════════════════════════════════════════════
class MediaFlowApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.cfg     = load_config()
        self.history = load_history()

        ctk.set_appearance_mode(self.cfg.get("theme", "dark"))
        ctk.set_default_color_theme("blue")
        self.configure(fg_color=BG_ROOT)

        self.title(f"{APP_NAME}  ·  v{VERSION}")
        self._apply_app_icon()
        self._set_initial_geometry()

        self._build_ui()
        self._nav("Download")

    def _apply_app_icon(self):
        try:
            if sys.platform == "win32":
                ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                    "MediaFlow.Pro.Desktop")
        except Exception:
            pass

        icon_path = resource_path("assets", ICON_FILE)
        if icon_path.exists():
            try:
                self.iconbitmap(str(icon_path))
            except Exception:
                pass

    def _set_initial_geometry(self):
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        usable_w = max(760, screen_w - 80)
        usable_h = max(560, screen_h - 80)
        width = min(max(1100, int(screen_w * 0.78)), usable_w)
        height = min(max(720, int(screen_h * 0.82)), usable_h)
        if screen_w < 900:
            width = max(640, screen_w - 24)
        if screen_h < 700:
            height = max(520, screen_h - 60)
        x = max(0, (screen_w - width) // 2)
        y = max(0, (screen_h - height) // 2)
        self.geometry(f"{width}x{height}+{x}+{y}")
        self.minsize(min(760, width), min(560, height))

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_content()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=220, fg_color=BG_PANEL, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsew")
        sb.grid_propagate(False)
        sb.grid_rowconfigure(10, weight=1)
        self._sidebar_icon = None

        # Logo
        logo_f = ctk.CTkFrame(sb, fg_color="transparent")
        logo_f.grid(row=0, column=0, padx=20, pady=(28, 24), sticky="ew")
        icon_path = resource_path("assets", ICON_PNG_FILE)
        if Image is not None and icon_path.exists():
            try:
                icon_img = Image.open(icon_path)
                self._sidebar_icon = ctk.CTkImage(
                    light_image=icon_img, dark_image=icon_img, size=(38, 38))
                ctk.CTkLabel(logo_f, image=self._sidebar_icon, text="").grid(
                    row=0, column=0, padx=(0,10))
            except Exception:
                ctk.CTkFrame(logo_f, width=4, height=36,
                             fg_color=ACCENT, corner_radius=2).grid(row=0, column=0, padx=(0,10))
        else:
            ctk.CTkFrame(logo_f, width=4, height=36,
                         fg_color=ACCENT, corner_radius=2).grid(row=0, column=0, padx=(0,10))
        lbl_f = ctk.CTkFrame(logo_f, fg_color="transparent")
        lbl_f.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(lbl_f, text="MediaFlow",
                     font=ctk.CTkFont("Segoe UI", 20, weight="bold"),
                     text_color=TXT_PRI).grid(row=0, sticky="w")
        ctk.CTkLabel(lbl_f, text="Universal Downloader",
                     font=ctk.CTkFont("Segoe UI", 10),
                     text_color=TXT_SEC).grid(row=1, sticky="w")

        ctk.CTkLabel(sb, text="MENU",
                     font=ctk.CTkFont("Segoe UI", 9, weight="bold"),
                     text_color=TXT_DIM).grid(row=1, column=0, padx=20, sticky="w")

        self._nav_btns = {}
        for i, (name, icon) in enumerate([
            ("Download", "⬇"),
            ("History",  "🕐"),
            ("Settings", "⚙"),
        ]):
            btn = ctk.CTkButton(
                sb, text=f"  {icon}   {name}",
                anchor="w", height=42,
                font=ctk.CTkFont("Segoe UI", 13),
                fg_color="transparent",
                hover_color="#2A2F3D",
                text_color=TXT_SEC,
                corner_radius=8,
                command=lambda n=name: self._nav(n))
            btn.grid(row=2+i, column=0, padx=10, pady=2, sticky="ew")
            self._nav_btns[name] = btn

        ctk.CTkFrame(sb, height=1, fg_color=BORDER).grid(
            row=5, column=0, padx=16, pady=16, sticky="ew")

        ctk.CTkLabel(sb, text="SAVE LOCATION",
                     font=ctk.CTkFont("Segoe UI", 9, weight="bold"),
                     text_color=TXT_DIM).grid(row=6, column=0, padx=20, sticky="w")

        dir_card = ctk.CTkFrame(sb, fg_color=BG_CARD, corner_radius=8)
        dir_card.grid(row=7, column=0, padx=12, pady=(4,0), sticky="ew")
        dir_card.grid_columnconfigure(0, weight=1)

        self._dir_lbl = ctk.CTkLabel(
            dir_card, text=self._short(self.cfg["output_dir"]),
            font=ctk.CTkFont("Segoe UI", 10), text_color=TXT_SEC,
            wraplength=155, justify="left", anchor="w")
        self._dir_lbl.grid(row=0, column=0, padx=10, pady=(8,2), sticky="w")

        ctk.CTkButton(
            dir_card, text="Change Folder", height=28,
            font=ctk.CTkFont("Segoe UI", 10),
            fg_color=BG_INPUT, hover_color=BORDER,
            text_color=TXT_SEC, corner_radius=6,
            command=self._browse_dir
        ).grid(row=1, column=0, padx=8, pady=(0,8), sticky="ew")

        ctk.CTkLabel(sb, text=f"v{VERSION}",
                     font=ctk.CTkFont("Segoe UI", 9),
                     text_color=TXT_DIM).grid(row=11, column=0, pady=(0,12))

    def _build_content(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.grid(row=0, column=1, sticky="nsew")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self._frames = {}
        for Cls in (DownloadFrame, HistoryFrame, SettingsFrame):
            f = Cls(container, self)
            f.grid(row=0, column=0, sticky="nsew")
            self._frames[Cls.NAME] = f

    def _nav(self, name):
        for n, btn in self._nav_btns.items():
            if n == name:
                btn.configure(fg_color="#2A3550", text_color=ACCENT)
            else:
                btn.configure(fg_color="transparent", text_color=TXT_SEC)
        self._frames[name].tkraise()
        if name == "History":
            self._frames["History"].refresh(self.history)

    def _browse_dir(self):
        d = filedialog.askdirectory(initialdir=self.cfg["output_dir"])
        if d:
            self.cfg["output_dir"] = d
            save_config(self.cfg)
            self.apply_runtime_settings()
            settings_frame = getattr(self, "_frames", {}).get("Settings")
            if settings_frame is not None and hasattr(settings_frame, "_dir_var"):
                settings_frame._dir_var.set(d)

    @staticmethod
    def _short(p, n=24):
        p = str(p)
        return p if len(p) <= n else "..." + p[-(n-1):]

    def add_history(self, entry):
        self.history.insert(0, entry)
        self.history = self.history[:self.cfg.get("max_history", 100)]
        save_history(self.history)
        history_frame = getattr(self, "_frames", {}).get("History")
        if history_frame is not None:
            history_frame.refresh(self.history)

    def apply_runtime_settings(self):
        ctk.set_appearance_mode(self.cfg.get("theme", "dark"))
        self._dir_lbl.configure(text=self._short(self.cfg["output_dir"]))
        self.history = self.history[:self.cfg.get("max_history", 100)]
        save_history(self.history)
        history_frame = getattr(self, "_frames", {}).get("History")
        if history_frame is not None:
            history_frame.refresh(self.history)


# ═══════════════════════════════════════════════════════════════════════════════
#  Download Frame
# ═══════════════════════════════════════════════════════════════════════════════
class DownloadFrame(ctk.CTkFrame):
    NAME = "Download"

    def __init__(self, parent, app: MediaFlowApp):
        super().__init__(parent, fg_color=BG_ROOT, corner_radius=0)
        self.app = app

        # Initialize thread state BEFORE building UI (button callbacks reference these)
        self._download_thread = None   # <-- BUG FIX
        self._cancel_flag     = threading.Event()
        self._thumb_image     = None
        self._media_features  = {}

        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Top bar ──────────────────────────────────────────────────────────
        topbar = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=60)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(topbar, text="Smart Download",
                     font=ctk.CTkFont("Segoe UI", 16, weight="bold"),
                     text_color=TXT_PRI
                     ).grid(row=0, column=0, padx=24, pady=(10,2), sticky="w")
        ctk.CTkLabel(topbar, text="Paste a supported media link and configure your download below",
                     font=ctk.CTkFont("Segoe UI", 11), text_color=TXT_SEC
                     ).grid(row=1, column=0, padx=24, pady=(0,10), sticky="w")

        self._body = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=BG_CARD,
            scrollbar_button_hover_color=BORDER,
        )
        self._body.grid(row=1, column=0, sticky="nsew", padx=0, pady=0)
        self._body.grid_columnconfigure(0, weight=1)

        # ── URL input card ───────────────────────────────────────────────────
        url_card = ctk.CTkFrame(self._body, fg_color=BG_CARD, corner_radius=8)
        url_card.grid(row=0, column=0, sticky="ew", padx=24, pady=(16, 6))
        url_card.grid_columnconfigure(0, weight=1)
        self._source_hint = None

        ctk.CTkLabel(url_card, text="MEDIA / PLAYLIST URL",
                     font=ctk.CTkFont("Segoe UI", 9, weight="bold"),
                     text_color=TXT_DIM
                     ).grid(row=0, column=0, padx=14, pady=(12,4), sticky="w")

        url_row = ctk.CTkFrame(url_card, fg_color="transparent")
        url_row.grid(row=1, column=0, sticky="ew", padx=12, pady=(0,12))
        url_row.grid_columnconfigure(0, weight=1)

        self._url_var = ctk.StringVar()
        self._url_entry = ctk.CTkEntry(
            url_row, textvariable=self._url_var,
            placeholder_text="Paste YouTube, Facebook, Instagram, Google Drive, Vimeo, SoundCloud...",
            height=42, font=ctk.CTkFont("Segoe UI", 12),
            fg_color=BG_INPUT, border_color=BORDER,
            text_color=TXT_PRI, placeholder_text_color=TXT_DIM,
            corner_radius=8)
        self._url_entry.grid(row=0, column=0, sticky="ew", padx=(0,8))
        self._url_entry.bind("<Return>", lambda _: self._fetch_info())

        self._paste_btn = ctk.CTkButton(
            url_row, text="Paste", width=76, height=42,
            font=ctk.CTkFont("Segoe UI", 11),
            fg_color=BG_INPUT, hover_color=BORDER,
            text_color=TXT_SEC, border_color=BORDER, border_width=1,
            corner_radius=8, command=self._paste_url)
        self._paste_btn.grid(row=0, column=1, padx=(0,8))

        self._fetch_btn = ctk.CTkButton(
            url_row, text="  Analyse  ", height=42,
            font=ctk.CTkFont("Segoe UI", 12, weight="bold"),
            fg_color=ACCENT, hover_color="#1D65CA", corner_radius=8,
            command=self._fetch_info)
        self._fetch_btn.grid(row=0, column=2)

        self._source_hint = ctk.CTkLabel(
            url_card,
            text="Supported by yt-dlp: " + ", ".join(SUPPORTED_SOURCE_HINTS) + ", and many more",
            font=ctk.CTkFont("Segoe UI", 10),
            text_color=TXT_DIM,
            wraplength=760,
            justify="left",
        )
        self._source_hint.grid(row=2, column=0, padx=14, pady=(0,12), sticky="w")

        # ── Info card ────────────────────────────────────────────────────────
        info_card = ctk.CTkFrame(self._body, fg_color=BG_CARD, corner_radius=8)
        info_card.grid(row=1, column=0, sticky="ew", padx=24, pady=6)
        info_card.grid_columnconfigure(1, weight=1)

        self._thumb_box = ctk.CTkFrame(info_card, width=THUMBNAIL_SIZE[0], height=THUMBNAIL_SIZE[1],
                                 fg_color=BG_INPUT, corner_radius=6)
        self._thumb_box.grid(row=0, column=0, rowspan=2, padx=14, pady=12)
        self._thumb_box.grid_propagate(False)
        self._thumb_label = ctk.CTkLabel(self._thumb_box, text="▶",
                                         font=ctk.CTkFont("Segoe UI", 24),
                                         text_color=TXT_DIM)
        self._thumb_label.place(relx=.5, rely=.5, anchor="center")

        self._info_title = ctk.CTkLabel(
            info_card, text="Paste a link and click Analyse to load media info",
            font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
            text_color=TXT_PRI, wraplength=640, justify="left", anchor="w")
        self._info_title.grid(row=0, column=1, sticky="w", padx=8, pady=(12,2))

        self._info_meta = ctk.CTkLabel(
            info_card, text="",
            font=ctk.CTkFont("Segoe UI", 11), text_color=TXT_SEC,
            justify="left", anchor="w")
        self._info_meta.grid(row=1, column=1, sticky="w", padx=8, pady=(0,12))

        # ── Options card ─────────────────────────────────────────────────────
        opts_card = ctk.CTkFrame(self._body, fg_color=BG_CARD, corner_radius=8)
        opts_card.grid(row=2, column=0, sticky="ew", padx=24, pady=6)
        opts_card.grid_columnconfigure(0, weight=1)
        opts_card.grid_columnconfigure(1, weight=1)
        self._opts_card = opts_card

        self._left_opts = ctk.CTkFrame(opts_card, fg_color="transparent")
        self._left_opts.grid(row=0, column=0, padx=14, pady=12, sticky="w")

        self._right_opts = ctk.CTkFrame(opts_card, fg_color="transparent")
        self._right_opts.grid(row=0, column=1, padx=14, pady=12, sticky="e")

        # Media type
        ctk.CTkLabel(self._left_opts, text="MEDIA TYPE",
                     font=ctk.CTkFont("Segoe UI", 9, weight="bold"),
                     text_color=TXT_DIM).grid(row=0, column=0, sticky="w", padx=(0,30))
        ctk.CTkLabel(self._left_opts, text="FORMAT",
                     font=ctk.CTkFont("Segoe UI", 9, weight="bold"),
                     text_color=TXT_DIM).grid(row=0, column=1, sticky="w", padx=(0,30))
        ctk.CTkLabel(self._left_opts, text="QUALITY",
                     font=ctk.CTkFont("Segoe UI", 9, weight="bold"),
                     text_color=TXT_DIM).grid(row=0, column=2, sticky="w")

        self._type_var = ctk.StringVar(value="Video")
        self._type_seg = ctk.CTkSegmentedButton(
            self._left_opts, values=["Video", "Audio"],
            variable=self._type_var,
            font=ctk.CTkFont("Segoe UI", 12),
            command=self._on_type_change)
        self._type_seg.grid(row=1, column=0, pady=(6,0), padx=(0,20), sticky="w")

        self._fmt_var = ctk.StringVar(value="mp4")
        self._fmt_menu = ctk.CTkOptionMenu(
            self._left_opts, variable=self._fmt_var,
            values=VIDEO_FORMATS, width=100,
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=BG_INPUT, button_color=BG_INPUT,
            button_hover_color=BORDER, dropdown_fg_color=BG_CARD,
            text_color=TXT_PRI)
        self._fmt_menu.grid(row=1, column=1, pady=(6,0), padx=(0,20), sticky="w")

        self._qual_var = ctk.StringVar(value="Best Available")
        self._qual_menu = ctk.CTkOptionMenu(
            self._left_opts, variable=self._qual_var,
            values=VIDEO_QUALITIES, width=160,
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=BG_INPUT, button_color=BG_INPUT,
            button_hover_color=BORDER, dropdown_fg_color=BG_CARD,
            text_color=TXT_PRI)
        self._qual_menu.grid(row=1, column=2, pady=(6,0), sticky="w")

        # Checkboxes
        ctk.CTkLabel(self._right_opts, text="OPTIONS",
                     font=ctk.CTkFont("Segoe UI", 9, weight="bold"),
                     text_color=TXT_DIM).grid(row=0, column=0, columnspan=2, sticky="w")

        chk_kw = dict(
            font=ctk.CTkFont("Segoe UI", 11), text_color=TXT_SEC,
            fg_color=ACCENT, hover_color="#1D65CA",
            border_color=BORDER, checkmark_color=TXT_PRI)

        self._playlist_var = ctk.BooleanVar(value=False)
        self._subs_var     = ctk.BooleanVar(value=False)
        self._thumb_var    = ctk.BooleanVar(value=False)
        self._sponsor_var  = ctk.BooleanVar(value=False)

        self._playlist_check = ctk.CTkCheckBox(self._right_opts, text="Full Playlist",
                                               variable=self._playlist_var, **chk_kw)
        self._playlist_check.grid(row=1, column=0, padx=(0,20), pady=(6,0), sticky="w")
        self._subs_check = ctk.CTkCheckBox(self._right_opts, text="Subtitles",
                                           variable=self._subs_var, **chk_kw)
        self._subs_check.grid(row=1, column=1, pady=(6,0), sticky="w")
        self._thumb_check = ctk.CTkCheckBox(self._right_opts, text="Embed Thumbnail",
                                            variable=self._thumb_var, **chk_kw)
        self._thumb_check.grid(row=2, column=0, padx=(0,20), pady=(6,0), sticky="w")
        self._sponsor_check = ctk.CTkCheckBox(self._right_opts, text="SponsorBlock",
                                              variable=self._sponsor_var, **chk_kw)
        self._sponsor_check.grid(row=2, column=1, pady=(6,0), sticky="w")
        self._set_feature_options({})

        # ── Progress card ────────────────────────────────────────────────────
        prog_card = ctk.CTkFrame(self._body, fg_color=BG_CARD, corner_radius=8)
        prog_card.grid(row=3, column=0, sticky="ew", padx=24, pady=6)
        prog_card.grid_columnconfigure(0, weight=1)

        prog_inner = ctk.CTkFrame(prog_card, fg_color="transparent")
        prog_inner.grid(row=0, column=0, sticky="ew", padx=16, pady=12)
        prog_inner.grid_columnconfigure(0, weight=1)

        self._status_var = ctk.StringVar(value="Idle  —  ready to download")
        self._speed_var  = ctk.StringVar(value="")
        self._eta_var    = ctk.StringVar(value="")

        stat_row = ctk.CTkFrame(prog_inner, fg_color="transparent")
        stat_row.grid(row=0, column=0, sticky="ew")
        stat_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(stat_row, textvariable=self._status_var,
                     font=ctk.CTkFont("Segoe UI", 11), text_color=TXT_SEC, anchor="w"
                     ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(stat_row, textvariable=self._speed_var,
                     font=ctk.CTkFont("Consolas", 10), text_color=TXT_DIM
                     ).grid(row=0, column=1, sticky="e", padx=(8,0))
        ctk.CTkLabel(stat_row, textvariable=self._eta_var,
                     font=ctk.CTkFont("Consolas", 10), text_color=TXT_DIM
                     ).grid(row=0, column=2, sticky="e", padx=(8,0))

        self._progress = ctk.CTkProgressBar(
            prog_inner, height=6, corner_radius=3,
            fg_color=BG_INPUT, progress_color=ACCENT)
        self._progress.grid(row=1, column=0, sticky="ew", pady=(8,0))
        self._progress.set(0)

        # ── Action buttons ───────────────────────────────────────────────────
        self._act_row = ctk.CTkFrame(self._body, fg_color="transparent")
        self._act_row.grid(row=4, column=0, sticky="ew", padx=24, pady=(8,10))
        self._act_row.grid_columnconfigure(0, weight=1)

        self._dl_btn = ctk.CTkButton(
            self._act_row, text="  ⬇   Start Download  ", height=48,
            font=ctk.CTkFont("Segoe UI", 14, weight="bold"),
            fg_color=ACCENT, hover_color="#1D65CA", corner_radius=10,
            command=self._start_download)
        self._dl_btn.grid(row=0, column=0, sticky="ew", padx=(0,8))

        self._cancel_btn = ctk.CTkButton(
            self._act_row, text="✕  Cancel", width=110, height=48,
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=BG_CARD, hover_color="#3A2020",
            text_color=ERROR, border_color=ERROR, border_width=1,
            corner_radius=10, state="disabled",
            command=self._cancel)
        self._cancel_btn.grid(row=0, column=1, padx=(0,8))

        self._folder_btn = ctk.CTkButton(
            self._act_row, text="📁  Open Folder", width=140, height=48,
            font=ctk.CTkFont("Segoe UI", 12),
            fg_color=BG_CARD, hover_color=BORDER,
            text_color=TXT_SEC, border_color=BORDER, border_width=1,
            corner_radius=10, command=self._open_folder)
        self._folder_btn.grid(row=0, column=2)

        # ── Log console ──────────────────────────────────────────────────────
        log_hdr = ctk.CTkFrame(self._body, fg_color="transparent")
        log_hdr.grid(row=5, column=0, sticky="ew", padx=24, pady=(4,0))
        log_hdr.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(log_hdr, text="CONSOLE OUTPUT",
                     font=ctk.CTkFont("Segoe UI", 9, weight="bold"),
                     text_color=TXT_DIM).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(log_hdr, text="Clear", width=52, height=22,
                      font=ctk.CTkFont("Segoe UI", 9),
                      fg_color="transparent", hover_color=BORDER,
                      text_color=TXT_DIM, command=self._clear_log
                      ).grid(row=0, column=1, sticky="e")

        self._log = ctk.CTkTextbox(
            self._body, font=ctk.CTkFont("Consolas", 10),
            fg_color=BG_PANEL, text_color=TXT_SEC,
            border_color=BORDER, border_width=1,
            corner_radius=6, wrap="word", state="disabled", height=96)
        self._log.grid(row=6, column=0, sticky="ew", padx=24, pady=(4,16))

    # ── Event Handlers ────────────────────────────────────────────────────────
    def _paste_url(self):
        try:
            self._url_var.set(self.clipboard_get().strip())
        except Exception:
            pass

    def _on_type_change(self, value):
        if value == "Video":
            self._fmt_var.set("mp4")
            self._fmt_menu.configure(values=VIDEO_FORMATS)
            self._qual_var.set("Best Available")
            self._qual_menu.configure(values=VIDEO_QUALITIES)
        else:
            self._fmt_var.set("mp3")
            self._fmt_menu.configure(values=AUDIO_FORMATS)
            self._qual_var.set("Best")
            self._qual_menu.configure(values=AUDIO_QUALITIES)

    def _log_write(self, msg):
        self._log.configure(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.insert("end", f"[{ts}]  {msg}\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _clear_log(self):
        self._log.configure(state="normal")
        self._log.delete("1.0", "end")
        self._log.configure(state="disabled")

    def _set_feature_options(self, features):
        self._media_features = features

        option_map = [
            ("playlist", self._playlist_check, self._playlist_var),
            ("subtitles", self._subs_check, self._subs_var),
            ("thumbnail", self._thumb_check, self._thumb_var),
            ("sponsorblock", self._sponsor_check, self._sponsor_var),
        ]
        for key, checkbox, variable in option_map:
            enabled = bool(features.get(key))
            checkbox.configure(state="normal" if enabled else "disabled")
            if not enabled:
                variable.set(False)

    @staticmethod
    def _analyze_features(info):
        info_type = info.get("_type") or ""
        entries = info.get("entries")
        extractor = (info.get("extractor_key") or info.get("extractor") or "").lower()
        webpage_url = (info.get("webpage_url") or info.get("original_url") or "").lower()

        is_playlist = info_type in {"playlist", "multi_video"} or entries is not None
        has_subtitles = bool(info.get("subtitles") or info.get("automatic_captions"))
        has_thumbnail = bool(DownloadFrame._extract_thumbnail_url(info))
        sponsorblock = "youtube" in extractor or "youtu.be" in webpage_url or "youtube.com" in webpage_url

        return {
            "playlist": is_playlist,
            "subtitles": has_subtitles,
            "thumbnail": has_thumbnail,
            "sponsorblock": sponsorblock,
        }

    # ── Fetch Info ────────────────────────────────────────────────────────────
    def _fetch_info(self):
        url = self._url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please paste a media URL first.")
            return
        self._reset_thumbnail()
        self._set_feature_options({})
        self._info_title.configure(text="Analysing media link...")
        self._info_meta.configure(text="")
        self._fetch_btn.configure(state="disabled", text="Analysing…")
        self._log_write(f"Fetching info: {url}")
        playlist = self._playlist_var.get()
        threading.Thread(target=self._fetch_worker, args=(url, playlist), daemon=True).start()

    def _fetch_worker(self, url, playlist):
        try:
            opts = apply_auth_opts({
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
                "noplaylist": not playlist,
            }, self.app.cfg)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info:
                raise yt_dlp.utils.DownloadError("No media information was returned for this URL.")
            title    = info.get("title", "Unknown")
            uploader = info.get("uploader", "")
            duration = fmt_duration(info.get("duration"))
            views    = info.get("view_count")
            n_fmt    = len(info.get("formats", []))
            webpage_url = info.get("webpage_url") or url
            extractor = info.get("extractor_key") or info.get("extractor") or ""
            if not playlist and not n_fmt and not info.get("url"):
                raise yt_dlp.utils.DownloadError(
                    "No downloadable video formats were found for this URL.")
            views_s  = f"{views:,} views" if views else ""
            thumb_url = self._extract_thumbnail_url(info)
            features = self._analyze_features(info)
            self.after(0, lambda: self._update_info(
                title, uploader, duration, views_s, n_fmt, extractor, webpage_url, thumb_url, features))
            self.after(0, lambda: self._log_write(
                f'OK  "{title}"  |  {duration}  |  {n_fmt} formats'))
        except Exception as e:
            self.after(0, lambda m=str(e): self._log_write(f"ERROR  {m}"))
            self.after(0, lambda m=str(e): self._show_error(m, fetch=True))
        finally:
            self.after(0, lambda: self._fetch_btn.configure(
                state="normal", text="  Analyse  "))

    def _update_info(self, title, uploader, duration, views, n_fmt, extractor="", webpage_url="", thumb_url="", features=None):
        self._info_title.configure(text=title)
        parts = []
        if extractor: parts.append(extractor)
        if uploader: parts.append(f"👤 {uploader}")
        if duration:  parts.append(f"⏱ {duration}")
        if views:     parts.append(f"👁 {views}")
        if n_fmt:     parts.append(f"🎬 {n_fmt} formats")
        self._info_meta.configure(text="   ·   ".join(parts))
        self._set_feature_options(features or {})
        if thumb_url:
            self._load_thumbnail(thumb_url, webpage_url)
        else:
            self._set_thumbnail_placeholder("No preview")

    @staticmethod
    def _extract_thumbnail_url(info):
        thumbs = info.get("thumbnails") or []
        if thumbs:
            thumbs = sorted(
                thumbs,
                key=lambda t: (t.get("width") or 0) * (t.get("height") or 0),
                reverse=True,
            )
            for thumb in thumbs:
                if thumb.get("url"):
                    return thumb["url"]
        extractor = (info.get("extractor_key") or info.get("extractor") or "").lower()
        video_id = info.get("id")
        if video_id and "youtube" in extractor:
            return f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
        return info.get("thumbnail") or ""

    def _reset_thumbnail(self):
        self._thumb_image = None
        self._set_thumbnail_placeholder("Preview")

    def _load_thumbnail(self, thumb_url, referer=""):
        if Image is None:
            return
        threading.Thread(
            target=self._thumbnail_worker,
            args=(thumb_url, referer),
            daemon=True,
        ).start()

    def _thumbnail_worker(self, thumb_url, referer):
        try:
            raw = self._download_thumbnail_bytes(thumb_url, referer)
            img = Image.open(io.BytesIO(raw)).convert("RGB")
            resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS")
            img = ImageOps.fit(img, THUMBNAIL_SIZE, method=resample)
            self.after(0, lambda image=img: self._set_thumbnail(image))
        except Exception as e:
            self.after(0, lambda m=str(e): self._log_write(f"Thumbnail unavailable: {m}"))
            self.after(0, lambda: self._set_thumbnail_placeholder("No preview"))

    def _download_thumbnail_bytes(self, thumb_url, referer):
        opts = apply_auth_opts({
            "quiet": True,
            "no_warnings": True,
        }, self.app.cfg)
        headers = {"User-Agent": "Mozilla/5.0"}
        if referer:
            headers["Referer"] = referer

        last_error = None
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                response = ydl.urlopen(urllib.request.Request(thumb_url, headers=headers))
                return response.read(3 * 1024 * 1024)
        except Exception as e:
            last_error = e

        try:
            req = urllib.request.Request(thumb_url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                return response.read(3 * 1024 * 1024)
        except Exception:
            raise last_error

    def _set_thumbnail(self, image):
        self._thumb_image = ctk.CTkImage(light_image=image, dark_image=image, size=THUMBNAIL_SIZE)
        self._thumb_label.configure(image=self._thumb_image, text="")

    def _set_thumbnail_placeholder(self, label):
        self._thumb_image = None
        self._thumb_label.configure(
            image=None,
            text=f"▶\n{label}",
            text_color=TXT_DIM,
            font=ctk.CTkFont("Segoe UI", 12, weight="bold"),
        )

    def _show_error(self, raw_msg, fetch=False):
        clean = clean_error_text(raw_msg)
        title, message, suggestions = classify_error(clean)
        if fetch and title == "Download failed":
            title = "Could not fetch media"
            message = "MediaFlow could not read downloadable media information from this link."
        ErrorDialog(self, title, message, details=clean, suggestions=suggestions)

    # ── Download ──────────────────────────────────────────────────────────────
    def _start_download(self):
        url = self._url_var.get().strip()
        if not url:
            messagebox.showwarning("No URL", "Please paste a media URL first.")
            return
        # Safe check — _download_thread always exists (set in __init__)
        if self._download_thread is not None and self._download_thread.is_alive():
            messagebox.showinfo("Busy", "A download is already in progress.")
            return

        self._cancel_flag.clear()
        self._progress.set(0)
        self._status_var.set("Starting download…")
        self._speed_var.set("")
        self._eta_var.set("")
        self._dl_btn.configure(state="disabled")
        self._cancel_btn.configure(state="normal")

        ext      = self._fmt_var.get()
        quality  = self._qual_var.get()
        is_audio = self._type_var.get() == "Audio"
        out_dir  = self.app.cfg["output_dir"]
        options = {
            "subs": self._subs_var.get(),
            "embed_thumb": self._thumb_var.get(),
            "sponsor_block": self._sponsor_var.get(),
            "playlist": self._playlist_var.get(),
        }

        self._log_write(
            f"Starting  [{self._type_var.get()}]  [{quality}]  [.{ext}]  "
            f"{'playlist' if options['playlist'] else 'single'}")

        self._download_thread = threading.Thread(
            target=self._dl_worker,
            args=(url, out_dir, ext, quality, is_audio, options),
            daemon=True)
        self._download_thread.start()

    def _dl_worker(self, url, out_dir, ext, quality, is_audio, options):
        t0 = time.time()

        def hook(d):
            if self._cancel_flag.is_set():
                raise yt_dlp.utils.DownloadError("Cancelled by user")
            st = d.get("status")
            if st == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
                done  = d.get("downloaded_bytes", 0)
                speed = d.get("speed") or 0
                eta   = d.get("eta") or 0
                pct   = done / total if total else 0
                pct_s = f"Downloading {pct*100:.1f}%  {fmt_size(done)} / {fmt_size(total)}"
                spd_s = f"{speed/1024/1024:.1f} MB/s" if speed else ""
                eta_s = f"ETA {eta}s" if eta else ""
                self.after(0, lambda p=pct:   self._progress.set(p))
                self.after(0, lambda s=pct_s: self._status_var.set(s))
                self.after(0, lambda s=spd_s: self._speed_var.set(s))
                self.after(0, lambda s=eta_s: self._eta_var.set(s))
            elif st == "finished":
                self.after(0, lambda: self._status_var.set("Processing / merging…"))
                self.after(0, lambda: self._progress.set(0.99))

        try:
            opts = build_ydl_opts(
                self.app.cfg, out_dir, ext, quality, is_audio, hook,
                subs=options["subs"],
                embed_thumb=options["embed_thumb"],
                sponsor_block=options["sponsor_block"],
                playlist=options["playlist"])
            with yt_dlp.YoutubeDL(opts) as ydl:
                info  = ydl.extract_info(url)
                title = (info.get("title") or url) if info else url
            elapsed = time.time() - t0
            self.after(0, lambda: self._on_done(title, url, ext, is_audio, elapsed))
        except yt_dlp.utils.DownloadError as e:
            msg = str(e)
            if "Cancelled" in msg:
                self.after(0, self._on_cancelled)
            else:
                self.after(0, lambda m=msg: self._on_error(m))
        except Exception as e:
            self.after(0, lambda m=str(e): self._on_error(m))

    def _on_done(self, title, url, ext, is_audio, elapsed):
        self._progress.set(1.0)
        self._status_var.set(f"✓  Completed in {elapsed:.1f}s")
        self._speed_var.set("")
        self._eta_var.set("")
        self._dl_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
        self._log_write(f'DONE  "{title}"  ({elapsed:.1f}s)')
        self.app.add_history({
            "title":     title,
            "url":       url,
            "ext":       ext,
            "type":      "Audio" if is_audio else "Video",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
        })

    def _on_error(self, msg):
        clean = clean_error_text(msg)
        self._status_var.set("✗  Download failed")
        self._speed_var.set("")
        self._eta_var.set("")
        self._dl_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
        self._log_write(f"ERROR  {clean}")
        self._show_error(clean)

    def _on_cancelled(self):
        self._progress.set(0)
        self._status_var.set("Cancelled")
        self._speed_var.set("")
        self._eta_var.set("")
        self._dl_btn.configure(state="normal")
        self._cancel_btn.configure(state="disabled")
        self._log_write("CANCELLED  Download stopped by user")

    def _cancel(self):
        self._cancel_flag.set()
        self._status_var.set("Cancelling…")

    def _open_folder(self):
        d = self.app.cfg["output_dir"]
        try:
            if sys.platform == "win32":
                os.startfile(d)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", d])
            else:
                subprocess.Popen(["xdg-open", d])
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ═══════════════════════════════════════════════════════════════════════════════
#  History Frame
# ═══════════════════════════════════════════════════════════════════════════════
class HistoryFrame(ctk.CTkFrame):
    NAME = "History"

    def __init__(self, parent, app: MediaFlowApp):
        super().__init__(parent, fg_color=BG_ROOT, corner_radius=0)
        self.app = app
        self._all = []
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        topbar = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=60)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(topbar, text="Download History",
                     font=ctk.CTkFont("Segoe UI", 16, weight="bold"),
                     text_color=TXT_PRI
                     ).grid(row=0, column=0, padx=24, pady=(10,2), sticky="w")
        ctk.CTkLabel(topbar, text="All previous downloads, searchable and re-downloadable",
                     font=ctk.CTkFont("Segoe UI", 11), text_color=TXT_SEC
                     ).grid(row=1, column=0, padx=24, pady=(0,10), sticky="w")
        ctk.CTkButton(topbar, text="Clear All", width=90, height=30,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color=BG_CARD, hover_color=BORDER,
                      text_color=ERROR, corner_radius=8,
                      command=self._clear_all
                      ).grid(row=0, column=1, rowspan=2, padx=20)

        # Stats
        stats_card = ctk.CTkFrame(self, fg_color=BG_CARD, corner_radius=8)
        stats_card.grid(row=1, column=0, sticky="ew", padx=24, pady=(14,6))
        self._stats_lbl = ctk.CTkLabel(
            stats_card, text="No downloads yet",
            font=ctk.CTkFont("Segoe UI", 11), text_color=TXT_SEC)
        self._stats_lbl.grid(padx=14, pady=10, sticky="w")

        # Search
        search_frame = ctk.CTkFrame(self, fg_color="transparent")
        search_frame.grid(row=2, column=0, sticky="ew", padx=24, pady=(0,8))
        search_frame.grid_columnconfigure(0, weight=1)
        self._q = ctk.StringVar()
        self._q.trace_add("write", lambda *_: self._render_filtered())
        ctk.CTkEntry(search_frame, textvariable=self._q,
                     placeholder_text="Search by title…",
                     height=36, fg_color=BG_CARD, border_color=BORDER,
                     text_color=TXT_PRI, placeholder_text_color=TXT_DIM,
                     corner_radius=8).grid(row=0, column=0, sticky="ew")

        # List
        self._list = ctk.CTkScrollableFrame(
            self, fg_color="transparent",
            scrollbar_button_color=BG_CARD,
            scrollbar_button_hover_color=BORDER)
        self._list.grid(row=3, column=0, sticky="nsew", padx=24, pady=(0,16))
        self._list.grid_columnconfigure(0, weight=1)

    def refresh(self, history):
        self._all = history
        n   = len(history)
        n_v = sum(1 for h in history if h.get("type") == "Video")
        n_a = n - n_v
        txt = f"{n} total  ·  {n_v} video(s)  ·  {n_a} audio file(s)"
        self._stats_lbl.configure(text=txt if n else "No downloads yet")
        self._render_filtered()

    def _render_filtered(self):
        q = self._q.get().lower()
        items = [h for h in self._all
                 if q in h.get("title","").lower() or q in h.get("url","").lower()]
        for w in self._list.winfo_children():
            w.destroy()
        if not items:
            ctk.CTkLabel(self._list,
                         text="No results." if q else
                              "No downloads yet.\nStart downloading to build history.",
                         text_color=TXT_DIM, font=ctk.CTkFont("Segoe UI", 12),
                         justify="center").grid(pady=48)
            return
        for i, entry in enumerate(items):
            self._row(i, entry)

    def _row(self, i, entry):
        card = ctk.CTkFrame(self._list, fg_color=BG_CARD, corner_radius=8)
        card.grid(row=i, column=0, sticky="ew", pady=(0,4))
        card.grid_columnconfigure(1, weight=1)

        is_audio = entry.get("type") == "Audio"
        badge = ctk.CTkFrame(card,
                             width=52, height=52, corner_radius=6,
                             fg_color="#1A2E44" if not is_audio else "#1A2E2A")
        badge.grid(row=0, column=0, rowspan=2, padx=10, pady=10)
        badge.grid_propagate(False)
        ctk.CTkLabel(badge, text="🎵" if is_audio else "🎬",
                     font=ctk.CTkFont("Segoe UI", 22)
                     ).place(relx=.5, rely=.5, anchor="center")

        ctk.CTkLabel(card, text=entry.get("title","Unknown"),
                     font=ctk.CTkFont("Segoe UI", 12, weight="bold"),
                     text_color=TXT_PRI, wraplength=500, justify="left", anchor="w"
                     ).grid(row=0, column=1, sticky="w", padx=8, pady=(10,2))

        meta = (f".{entry.get('ext','')}  ·  "
                f"{entry.get('type','')}  ·  "
                f"{entry.get('timestamp','')}")
        ctk.CTkLabel(card, text=meta,
                     font=ctk.CTkFont("Segoe UI", 10), text_color=TXT_DIM, anchor="w"
                     ).grid(row=1, column=1, sticky="w", padx=8, pady=(0,10))

        url = entry.get("url","")
        ctk.CTkButton(card, text="↻ Re-download", width=120, height=32,
                      font=ctk.CTkFont("Segoe UI", 11),
                      fg_color=BG_INPUT, hover_color=BORDER,
                      text_color=ACCENT, border_color=ACCENT, border_width=1,
                      corner_radius=6,
                      command=lambda u=url: self._redownload(u)
                      ).grid(row=0, column=2, rowspan=2, padx=10)

    def _redownload(self, url):
        self.app._frames["Download"]._url_var.set(url)
        self.app._nav("Download")

    def _clear_all(self):
        if messagebox.askyesno("Clear History",
                               "Delete all download history?\nThis cannot be undone."):
            self.app.history.clear()
            save_history([])
            self.refresh([])


# ═══════════════════════════════════════════════════════════════════════════════
#  Settings Frame
# ═══════════════════════════════════════════════════════════════════════════════
class SettingsFrame(ctk.CTkFrame):
    NAME = "Settings"

    def __init__(self, parent, app: MediaFlowApp):
        super().__init__(parent, fg_color=BG_ROOT, corner_radius=0)
        self.app = app
        self._build()

    def _build(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        topbar = ctk.CTkFrame(self, fg_color=BG_PANEL, corner_radius=0, height=60)
        topbar.grid(row=0, column=0, sticky="ew")
        topbar.grid_propagate(False)
        topbar.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(topbar, text="Settings",
                     font=ctk.CTkFont("Segoe UI", 16, weight="bold"),
                     text_color=TXT_PRI
                     ).grid(row=0, column=0, padx=24, pady=(10,2), sticky="w")
        ctk.CTkLabel(topbar, text="Configure your preferences and defaults",
                     font=ctk.CTkFont("Segoe UI", 11), text_color=TXT_SEC
                     ).grid(row=1, column=0, padx=24, pady=(0,10), sticky="w")

        body = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                      scrollbar_button_color=BG_CARD)
        body.grid(row=1, column=0, sticky="nsew", padx=24, pady=16)
        body.grid_columnconfigure(1, weight=1)

        r = [0]

        def sec(title):
            f = ctk.CTkFrame(body, fg_color="transparent")
            f.grid(row=r[0], column=0, columnspan=2,
                   sticky="ew", padx=4, pady=(20 if r[0] > 0 else 0, 6))
            f.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(f, text=title,
                         font=ctk.CTkFont("Segoe UI", 10, weight="bold"),
                         text_color=ACCENT).grid(row=0, column=0, sticky="w")
            ctk.CTkFrame(f, height=1, fg_color=BORDER
                         ).grid(row=0, column=1, sticky="ew", padx=(10,0))
            r[0] += 1

        def lbl(text):
            ctk.CTkLabel(body, text=text,
                         font=ctk.CTkFont("Segoe UI", 12),
                         text_color=TXT_SEC, anchor="w"
                         ).grid(row=r[0], column=0, sticky="w", padx=4, pady=8)

        def wgt(widget, pady=8):
            widget.grid(row=r[0], column=1, sticky="e", padx=4, pady=pady)
            r[0] += 1

        entry_kw = dict(fg_color=BG_INPUT, border_color=BORDER,
                        text_color=TXT_PRI, corner_radius=6)
        menu_kw  = dict(fg_color=BG_INPUT, button_color=BG_INPUT,
                        button_hover_color=BORDER, dropdown_fg_color=BG_CARD,
                        text_color=TXT_PRI)

        # OUTPUT
        sec("OUTPUT")
        lbl("Save Location")
        dir_f = ctk.CTkFrame(body, fg_color="transparent")
        dir_f.grid(row=r[0], column=1, sticky="e", padx=4, pady=8)
        self._dir_var = ctk.StringVar(value=self.app.cfg["output_dir"])
        ctk.CTkEntry(dir_f, textvariable=self._dir_var, width=300,
                     **entry_kw).grid(row=0, column=0)
        ctk.CTkButton(dir_f, text="Browse", width=72, height=32,
                      fg_color=BG_CARD, hover_color=BORDER,
                      text_color=TXT_SEC, corner_radius=6,
                      command=self._browse).grid(row=0, column=1, padx=(6,0))
        r[0] += 1

        lbl("Max History Entries")
        self._hist_var = ctk.StringVar(value=str(self.app.cfg.get("max_history",100)))
        wgt(ctk.CTkEntry(body, textvariable=self._hist_var, width=80, **entry_kw))

        lbl("Concurrent Fragments")
        self._conc_var = ctk.StringVar(value=str(self.app.cfg.get("concurrent","1")))
        wgt(ctk.CTkOptionMenu(body, variable=self._conc_var,
                              values=["1","2","4","8","16"], width=80, **menu_kw))

        # ADVANCED
        sec("ADVANCED")
        lbl("FFmpeg Path  (blank = auto-detect)")
        self._ffmpeg_var = ctk.StringVar(value=self.app.cfg.get("ffmpeg_path",""))
        wgt(ctk.CTkEntry(body, textvariable=self._ffmpeg_var, width=380,
                         placeholder_text="e.g. C:\\ffmpeg\\bin",
                         placeholder_text_color=TXT_DIM, **entry_kw))

        lbl("Cookie File  (optional)")
        cookie_f = ctk.CTkFrame(body, fg_color="transparent")
        cookie_f.grid(row=r[0], column=1, sticky="e", padx=4, pady=8)
        self._cookie_var = ctk.StringVar(value=self.app.cfg.get("cookie_file",""))
        ctk.CTkEntry(cookie_f, textvariable=self._cookie_var, width=300,
                     placeholder_text="cookies.txt for login-required sites",
                     placeholder_text_color=TXT_DIM, **entry_kw).grid(row=0, column=0)
        ctk.CTkButton(cookie_f, text="Browse", width=72, height=32,
                      fg_color=BG_CARD, hover_color=BORDER,
                      text_color=TXT_SEC, corner_radius=6,
                      command=self._browse_cookie).grid(row=0, column=1, padx=(6,0))
        r[0] += 1

        lbl("Use Browser Cookies")
        self._browser_cookie_var = ctk.StringVar(
            value=self.app.cfg.get("browser_cookies","None"))
        wgt(ctk.CTkOptionMenu(body, variable=self._browser_cookie_var,
                              values=BROWSER_COOKIE_SOURCES, width=130, **menu_kw))

        # APPEARANCE
        sec("APPEARANCE")
        lbl("Theme")
        self._theme_var = ctk.StringVar(value=self.app.cfg["theme"])
        wgt(ctk.CTkSegmentedButton(body, values=["light","dark","system"],
                                   variable=self._theme_var,
                                   font=ctk.CTkFont("Segoe UI", 11)))

        # ABOUT
        sec("ABOUT")
        about = ctk.CTkFrame(body, fg_color=BG_CARD, corner_radius=8)
        about.grid(row=r[0], column=0, columnspan=2, sticky="ew", padx=4, pady=6)
        about.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(about, text=f"{APP_NAME}  ·  Version {VERSION}",
                     font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
                     text_color=TXT_PRI).grid(padx=14, pady=(12,2), sticky="w")
        ctk.CTkLabel(about, text="Powered by yt-dlp  ·  CustomTkinter  ·  Python 3",
                     font=ctk.CTkFont("Segoe UI", 11), text_color=TXT_SEC
                     ).grid(padx=14, pady=(0,4), sticky="w")
        ctk.CTkLabel(about,
                     text="⚠  ffmpeg is required for merging video/audio and converting formats.",
                     font=ctk.CTkFont("Segoe UI", 10), text_color=WARN
                     ).grid(padx=14, pady=(0,12), sticky="w")
        r[0] += 1

        # Save
        ctk.CTkButton(body, text="  💾   Save Settings  ", height=44,
                      font=ctk.CTkFont("Segoe UI", 13, weight="bold"),
                      fg_color=ACCENT, hover_color="#1D65CA", corner_radius=10,
                      command=self._save
                      ).grid(row=r[0], column=0, columnspan=2,
                             sticky="ew", padx=4, pady=(20,8))

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self._dir_var.get())
        if d:
            self._dir_var.set(d)

    def _browse_cookie(self):
        f = filedialog.askopenfilename(
            title="Select cookies.txt",
            filetypes=[("Cookie files", "*.txt"), ("All files", "*.*")],
        )
        if f:
            self._cookie_var.set(f)

    def _save(self):
        self.app.cfg["output_dir"]  = self._dir_var.get()
        self.app.cfg["ffmpeg_path"] = self._ffmpeg_var.get()
        self.app.cfg["theme"]       = self._theme_var.get()
        self.app.cfg["concurrent"]  = self._conc_var.get()
        self.app.cfg["cookie_file"] = self._cookie_var.get()
        self.app.cfg["browser_cookies"] = self._browser_cookie_var.get()
        try:
            self.app.cfg["max_history"] = int(self._hist_var.get())
        except ValueError:
            pass
        save_config(self.app.cfg)
        self.app.apply_runtime_settings()
        messagebox.showinfo("Saved", "Settings applied to the running app.")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = MediaFlowApp()
    app.mainloop()
