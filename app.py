"""
MediaFlow Pro - desktop media downloader.

PyQt5 UI + yt-dlp backend.
"""

import ctypes
import io
import json
import os
import re
import subprocess
import sys

# Ensure the user's system PATH is fully inherited so ffmpeg is always found
# even when the app is launched from a venv or via a desktop shortcut.
if sys.platform == "win32":
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment") as key:
            sys_path, _ = winreg.QueryValueEx(key, "Path")
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Environment") as key:
            try:
                user_path, _ = winreg.QueryValueEx(key, "Path")
            except FileNotFoundError:
                user_path = ""
        full_path = os.pathsep.join(filter(None, [sys_path, user_path]))
        os.environ["PATH"] = full_path + os.pathsep + os.environ.get("PATH", "")
    except Exception:
        pass  # Fall back silently; user can set FFmpeg path in Settings
import threading
import time
import urllib.request
from datetime import datetime
from pathlib import Path

from PyQt5.QtCore import Qt, QObject, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
    QProgressBar,
)

try:
    import yt_dlp
except ImportError:
    app = QApplication(sys.argv)
    QMessageBox.critical(
        None,
        "Missing Dependency",
        "yt-dlp is not installed.\n\nRun:\n  pip install yt-dlp",
    )
    sys.exit(1)


APP_NAME = "MediaFlow Pro"
VERSION = "2.1"
APP_DIR = Path(__file__).resolve().parent
CONFIG_FILE = Path.home() / ".ytflow2_config.json"
HISTORY_FILE = Path.home() / ".ytflow2_history.json"
ICON_FILE = "mediaflow.ico"
ICON_PNG_FILE = "mediaflow.png"
THUMBNAIL_SIZE = QSize(128, 72)

DEFAULT_CONFIG = {
    "theme": "dark",
    "output_dir": str(Path.home() / "Downloads"),
    "max_history": 100,
    "ffmpeg_path": "",
    "concurrent": "4",
    "cookie_file": "",
    "browser_cookies": "None",
}

SUPPORTED_SOURCE_HINTS = [
    "YouTube",
    "Facebook",
    "Instagram",
    "TikTok",
    "X/Twitter",
    "Vimeo",
    "SoundCloud",
    "Google Drive",
    "Twitch",
    "Reddit",
]

# Each entry: (display name, brand hex color, list of content-type tags, optional caveat)
# All platforms confirmed present in yt-dlp's extractor list.
PLATFORM_PILLS = [
    # Tier 1 — work reliably, no auth needed for public content
    ("YouTube",      "#FF0000", ["Videos", "Shorts", "Live", "Playlists", "Podcasts"], None),
    ("TikTok",       "#FF0050", ["Videos", "Live", "Collections", "Sounds"],          None),
    ("Facebook",     "#1877F2", ["Videos", "Reels", "Live", "Watch"],                  None),
    ("Instagram",    "#C13584", ["Reels", "Posts", "IGTV"],                            "Stories need cookies"),
    ("X / Twitter",  "#1D9BF0", ["Videos", "GIFs", "Spaces"],                          None),
    ("Twitch",       "#9146FF", ["VODs", "Clips", "Live"],                             None),
    ("Kick",         "#53FC18", ["Live", "VODs", "Clips"],                             None),
    ("Reddit",       "#FF4500", ["Videos", "GIFs", "Posts"],                           None),
    ("Bluesky",      "#0085FF", ["Videos", "GIFs"],                                    None),
    ("Vimeo",        "#1AB7EA", ["Videos", "Showcases", "Events"],                     None),
    ("Dailymotion",  "#0066DC", ["Videos", "Live"],                                    None),
    ("Rumble",       "#85C742", ["Videos", "Live"],                                    None),
    ("SoundCloud",   "#FF5500", ["Tracks", "Playlists", "Podcasts"],                   None),
    ("Bilibili",     "#00A1D6", ["Videos", "Live", "Episodes"],                        None),
    ("Google Drive", "#34A853", ["Videos", "Audio", "Files"],                          None),
    ("Odysee",       "#EF1970", ["Videos", "Live", "Podcasts"],                        None),
    # Tier 2 — work but have geo or login restrictions
    ("BBC iPlayer",  "#FF4B00", ["Shows", "News", "Live"],                             "UK only"),
    ("Arte",         "#006699", ["Videos", "Documentaries"],                           "EU geo-restricted"),
    ("LinkedIn",     "#0A66C2", ["Videos", "Posts"],                                   "Login required"),
    ("Pinterest",    "#E60023", ["Video Pins", "Idea Pins"],                           "Public pins only"),
    ("Xiaohongshu",  "#FE2C55", ["Videos", "Posts"],                                   None),
    ("Douyin",       "#010101", ["Videos"],                                             None),
]
BROWSER_COOKIE_SOURCES = [
    "None",
    "Chrome",
    "Edge",
    "Firefox",
    "Brave",
    "Opera",
    "Vivaldi",
    "Chromium",
]

VIDEO_FORMATS = ["mp4", "mkv", "webm", "avi", "mov", "flv"]
AUDIO_FORMATS = ["mp3", "m4a", "aac", "opus", "flac", "wav", "ogg"]
VIDEO_QUALITIES = [
    "Best Available",
    "4320p (8K)",
    "2160p (4K)",
    "1440p (2K)",
    "1080p (FHD)",
    "720p (HD)",
    "480p",
    "360p",
    "240p",
    "144p",
    "Worst",
]
AUDIO_QUALITIES = [
    "Best",
    "320 kbps",
    "256 kbps",
    "192 kbps",
    "128 kbps",
    "96 kbps",
    "64 kbps",
    "Worst",
]


PALETTES = {
    "dark": {
        "root": "#1A1D23",
        "panel": "#21252E",
        "card": "#282D38",
        "input": "#1E2229",
        "text": "#E8ECF4",
        "muted": "#9AA4B8",
        "dim": "#657087",
        "border": "#2E3441",
        "accent": "#2B7DE9",
        "accent_hover": "#1D65CA",
        "danger": "#F43F5E",
        "success": "#22C55E",
        "warn": "#F59E0B",
        "selected": "#2A3550",
    },
    "light": {
        "root": "#F4F7FB",
        "panel": "#E8EEF7",
        "card": "#FFFFFF",
        "input": "#F2F5FA",
        "text": "#162033",
        "muted": "#536176",
        "dim": "#8290A5",
        "border": "#D7DFEA",
        "accent": "#256FE4",
        "accent_hover": "#1D5FC4",
        "danger": "#D92D50",
        "success": "#16A34A",
        "warn": "#D97706",
        "selected": "#DDE9FF",
    },
}


def resource_path(*parts):
    base = Path(getattr(sys, "_MEIPASS", APP_DIR))
    return base.joinpath(*parts)


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


def save_history(history):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception:
        pass


def fmt_duration(secs):
    if not secs:
        return ""
    secs = int(secs)
    h, r = divmod(secs, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def fmt_size(value):
    if not value:
        return ""
    value = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"


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
            "MediaFlow uses safer filenames; try the download again.",
            ["Retry the download", "Choose a shorter save folder path", "Update yt-dlp if it continues"],
        )
    if "unsupported url" in lower or "no suitable extractor" in lower:
        return (
            "This link is not supported",
            "yt-dlp does not have an extractor for this URL, or the page is not a direct media link.",
            ["Copy the media post URL", "Check that the post is public"],
        )
    if "private" in lower or "login" in lower or "cookies" in lower or "permission" in lower:
        return (
            "This media needs access permission",
            "The site is asking for a logged-in session or the link is private.",
            ["Select browser cookies in Settings", "Or provide a cookies.txt file", "Confirm the link opens in your browser"],
        )
    if "no video" in lower or "not a video" in lower or "requested format is not available" in lower:
        return (
            "No downloadable video was found",
            "The page loaded, but yt-dlp could not find a media stream matching your selected options.",
            ["Try Audio mode", "Try Best Available", "Confirm the URL points to playable media"],
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
            ["Check your connection", "Retry in a moment", "Open the link in your browser"],
        )
    return (
        "Download failed",
        "MediaFlow could not process this link.",
        ["Check the URL", "Try cookies for restricted sites", "Try another format or quality"],
    )


def apply_auth_opts(opts, cfg):
    cookie_file = str(cfg.get("cookie_file", "")).strip()
    if cookie_file:
        opts["cookiefile"] = cookie_file

    browser = str(cfg.get("browser_cookies", "None")).strip()
    if browser and browser.lower() != "none":
        opts["cookiesfrombrowser"] = (browser.lower(),)

    return opts


def build_ydl_opts(
    cfg,
    out_dir,
    ext,
    quality,
    is_audio,
    progress_hook,
    subs=False,
    embed_thumb=False,
    sponsor_block=False,
    playlist=False,
):
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
            "Best": "0",
            "320 kbps": "320",
            "256 kbps": "256",
            "192 kbps": "192",
            "128 kbps": "128",
            "96 kbps": "96",
            "64 kbps": "64",
            "Worst": "9",
        }
        postprocessors.append(
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": ext,
                "preferredquality": q_map.get(quality, "0"),
            }
        )
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
            fmt = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
        else:
            fmt = "bestvideo+bestaudio/best"
        postprocessors.append({"key": "FFmpegVideoConvertor", "preferedformat": ext})

    if embed_thumb:
        postprocessors.append({"key": "EmbedThumbnail"})
    if subs:
        postprocessors.append({"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False})
    if sponsor_block:
        postprocessors.append({"key": "SponsorBlock"})
        postprocessors.append(
            {
                "key": "ModifyChapters",
                "remove_sponsor_segments": ["sponsor", "intro", "outro", "selfpromo"],
            }
        )

    try:
        conc = int(cfg.get("concurrent", 1))
    except (TypeError, ValueError):
        conc = 1

    opts = {
        "format": fmt,
        "outtmpl": outtmpl,
        "progress_hooks": [progress_hook],
        "postprocessors": postprocessors,
        "quiet": True,
        "no_warnings": True,
        "merge_output_format": ext if not is_audio else None,
        "noplaylist": not playlist,
        "writesubtitles": subs,
        "subtitleslangs": ["en"] if subs else [],
        "writethumbnail": embed_thumb,
        "concurrent_fragment_downloads": conc,
        "retries": 5,
        "fragment_retries": 5,
        "windowsfilenames": True,
        "restrictfilenames": True,
        "trim_file_name": 160,
        # YouTube throttling fixes
        "http_chunk_size": 10485760,          # 10 MB chunks — bypasses per-request throttling
        "throttledratelimit": 102400,          # re-fetch URL if speed drops below 100 KB/s
        "extractor_args": {"youtube": {"player_client": ["web", "default"]}},
    }
    ffmpeg = cfg.get("ffmpeg_path", "").strip()
    if ffmpeg:
        opts["ffmpeg_location"] = ffmpeg
    return apply_auth_opts(opts, cfg)


def make_card():
    frame = QFrame()
    frame.setObjectName("card")
    return frame


def clear_layout(layout):
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


class ErrorDialog(QDialog):
    def __init__(self, parent, raw_msg, fetch=False):
        super().__init__(parent)
        clean = clean_error_text(raw_msg)
        title, message, suggestions = classify_error(clean)
        if fetch and title == "Download failed":
            title = "Could not fetch media"
            message = "MediaFlow could not read downloadable media information from this link."

        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(540)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title_label = QLabel(title)
        title_label.setObjectName("dialogTitle")
        message_label = QLabel(message)
        message_label.setWordWrap(True)

        tips = QLabel("\n".join(f"- {tip}" for tip in suggestions))
        tips.setWordWrap(True)
        details = QTextEdit()
        details.setObjectName("detailsBox")
        details.setReadOnly(True)
        details.setFixedHeight(88)
        details.setPlainText(clean)

        ok = QPushButton("OK")
        ok.setObjectName("primaryButton")
        ok.clicked.connect(self.accept)

        layout.addWidget(title_label)
        layout.addWidget(message_label)
        layout.addWidget(tips)
        layout.addWidget(details)
        layout.addWidget(ok, alignment=Qt.AlignRight)


class WorkerSignals(QObject):
    info_ready = pyqtSignal(dict)
    fetch_error = pyqtSignal(str)
    download_error = pyqtSignal(str)
    progress = pyqtSignal(float, str, str, str)
    done = pyqtSignal(str, str, str, bool, float)
    cancelled = pyqtSignal()
    thumb_ready = pyqtSignal(bytes)
    thumb_failed = pyqtSignal(str)


class MainWindow(QMainWindow):
    def __init__(self, qt_app=None):
        super().__init__()
        self.cfg = load_config()
        self.history = load_history()
        self._nav_buttons = {}

        self._apply_app_icon(qt_app)
        self.setWindowTitle(f"{APP_NAME}  ·  v{VERSION}")
        self._set_initial_geometry()
        self.setMinimumSize(760, 540)

        self._build_ui()
        self.apply_theme(self.cfg.get("theme", "dark"))
        self.navigate("Download")

    def _apply_app_icon(self, qt_app=None):
        # Re-use the icon already set on QApplication when available,
        # otherwise fall back to loading it from disk.
        icon_path = resource_path("assets", ICON_FILE)
        if icon_path.exists():
            icon = QIcon(str(icon_path))
        else:
            png_path = resource_path("assets", ICON_PNG_FILE)
            icon = QIcon(str(png_path)) if png_path.exists() else QIcon()
        if not icon.isNull():
            self.setWindowIcon(icon)
            if qt_app:
                qt_app.setWindowIcon(icon)

    def _set_initial_geometry(self):
        screen = QApplication.primaryScreen().availableGeometry()
        width = min(max(1100, int(screen.width() * 0.78)), max(760, screen.width() - 60))
        height = min(max(720, int(screen.height() * 0.82)), max(540, screen.height() - 60))
        x = screen.x() + max(0, (screen.width() - width) // 2)
        y = screen.y() + max(0, (screen.height() - height) // 2)
        self.setGeometry(x, y, width, height)

    def _build_ui(self):
        root = QWidget()
        root.setObjectName("appRoot")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(root)

        self.sidebar = QWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFixedWidth(240)
        side = QVBoxLayout(self.sidebar)
        side.setContentsMargins(18, 28, 18, 18)
        side.setSpacing(12)

        logo_row = QHBoxLayout()
        logo_row.setSpacing(10)
        icon_label = QLabel()
        icon_path = resource_path("assets", ICON_PNG_FILE)
        if icon_path.exists():
            pix = QPixmap(str(icon_path)).scaled(38, 38, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            icon_label.setPixmap(pix)
        else:
            icon_label.setFixedSize(4, 36)
            icon_label.setObjectName("accentBar")
        logo_text = QVBoxLayout()
        brand = QLabel("MediaFlow")
        brand.setObjectName("brand")
        tagline = QLabel("Universal Downloader")
        tagline.setObjectName("mutedSmall")
        logo_text.addWidget(brand)
        logo_text.addWidget(tagline)
        logo_row.addWidget(icon_label)
        logo_row.addLayout(logo_text)
        side.addLayout(logo_row)
        side.addSpacing(28)

        menu = QLabel("MENU")
        menu.setObjectName("eyebrow")
        side.addWidget(menu)

        for name in ("Download", "History", "Settings"):
            btn = QPushButton(name)
            btn.setObjectName("navButton")
            btn.setCheckable(True)
            btn.setMinimumHeight(42)
            btn.clicked.connect(lambda _, n=name: self.navigate(n))
            self._nav_buttons[name] = btn
            side.addWidget(btn)

        side.addSpacing(18)
        save_lbl = QLabel("SAVE LOCATION")
        save_lbl.setObjectName("eyebrow")
        side.addWidget(save_lbl)

        folder_card = make_card()
        folder_layout = QVBoxLayout(folder_card)
        folder_layout.setContentsMargins(12, 10, 12, 10)
        self.dir_label = QLabel(self._short(self.cfg["output_dir"], 26))
        self.dir_label.setObjectName("mutedSmall")
        self.dir_label.setWordWrap(True)
        folder_btn = QPushButton("Change Folder")
        folder_btn.setObjectName("secondaryButton")
        folder_btn.clicked.connect(self.browse_output_dir)
        folder_layout.addWidget(self.dir_label)
        folder_layout.addWidget(folder_btn)
        side.addWidget(folder_card)

        side.addStretch(1)
        version = QLabel(f"v{VERSION}")
        version.setObjectName("mutedSmall")
        version.setAlignment(Qt.AlignCenter)
        side.addWidget(version)

        self.stack = QStackedWidget()
        self.stack.setObjectName("contentStack")
        self.download_page = DownloadPage(self)
        self.history_page = HistoryPage(self)
        self.settings_page = SettingsPage(self)
        for page in (self.download_page, self.history_page, self.settings_page):
            self.stack.addWidget(page)

        root_layout.addWidget(self.sidebar)
        root_layout.addWidget(self.stack, 1)

    def navigate(self, name):
        for n, btn in self._nav_buttons.items():
            btn.setChecked(n == name)
        page = {
            "Download": self.download_page,
            "History": self.history_page,
            "Settings": self.settings_page,
        }[name]
        if name == "History":
            self.history_page.refresh(self.history)
        self.stack.setCurrentWidget(page)

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select save folder", self.cfg["output_dir"])
        if directory:
            self.cfg["output_dir"] = directory
            save_config(self.cfg)
            self.apply_runtime_settings()
            self.settings_page.sync_from_config()

    def add_history(self, entry):
        self.history.insert(0, entry)
        self.history = self.history[: self.cfg.get("max_history", 100)]
        save_history(self.history)
        self.history_page.refresh(self.history)

    def apply_runtime_settings(self):
        self.dir_label.setText(self._short(self.cfg["output_dir"], 26))
        self.apply_theme(self.cfg.get("theme", "dark"))
        self.history = self.history[: self.cfg.get("max_history", 100)]
        save_history(self.history)
        self.history_page.refresh(self.history)

    def apply_theme(self, theme):
        if theme == "system":
            theme = "dark"
        palette = PALETTES.get(theme, PALETTES["dark"])
        self._palette = palette
        self.setStyleSheet(build_stylesheet(palette))
        self.download_page.apply_palette(palette)
        self.history_page.apply_palette(palette)
        self.settings_page.apply_palette(palette)

    @staticmethod
    def _short(path, chars=24):
        path = str(path)
        return path if len(path) <= chars else "..." + path[-(chars - 3) :]


class DownloadPage(QWidget):
    def __init__(self, app_window):
        super().__init__()
        self.setObjectName("page")
        self.app_window = app_window
        self.signals = WorkerSignals()
        self.download_thread = None
        self.cancel_event = threading.Event()
        self.thumb_pixmap = None
        self.media_features = {}

        self.signals.info_ready.connect(self._on_info_ready)
        self.signals.fetch_error.connect(self._on_fetch_error)
        self.signals.download_error.connect(self._on_download_error)
        self.signals.progress.connect(self._on_progress)
        self.signals.done.connect(self._on_done)
        self.signals.cancelled.connect(self._on_cancelled)
        self.signals.thumb_ready.connect(self._set_thumbnail_from_bytes)
        self.signals.thumb_failed.connect(self._on_thumb_failed)

        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(70)
        topbar_layout = QVBoxLayout(topbar)
        topbar_layout.setContentsMargins(28, 12, 28, 12)
        topbar_layout.setSpacing(4)
        title = QLabel("Smart Download")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Paste a supported media link and configure your download below")
        subtitle.setObjectName("muted")
        topbar_layout.addWidget(title)
        topbar_layout.addWidget(subtitle)
        root.addWidget(topbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("scrollArea")
        body = QWidget()
        body.setObjectName("scrollBody")
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(24, 18, 24, 20)
        body_layout.setSpacing(12)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        self._build_url_card(body_layout)
        self._build_platform_bar(body_layout)
        self._build_info_card(body_layout)
        self._build_options_card(body_layout)
        self._build_progress_card(body_layout)
        self._build_actions(body_layout)
        self._build_log(body_layout)
        body_layout.addStretch(1)

    def _build_url_card(self, parent):
        card = make_card()
        card.setMinimumHeight(112)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setSpacing(10)
        label = QLabel("MEDIA / PLAYLIST URL")
        label.setObjectName("eyebrow")
        row = QHBoxLayout()
        row.setSpacing(10)
        self.url_edit = QLineEdit()
        self.url_edit.setMinimumHeight(42)
        self.url_edit.setPlaceholderText("Paste YouTube, Facebook, Instagram, Google Drive, Vimeo, SoundCloud...")
        self.url_edit.returnPressed.connect(self.fetch_info)
        paste = QPushButton("Paste")
        paste.setObjectName("secondaryButton")
        paste.setMinimumHeight(42)
        paste.setMinimumWidth(74)
        paste.clicked.connect(self.paste_url)
        self.analyse_btn = QPushButton("Analyse")
        self.analyse_btn.setObjectName("primaryButton")
        self.analyse_btn.setMinimumHeight(42)
        self.analyse_btn.setMinimumWidth(86)
        self.analyse_btn.clicked.connect(self.fetch_info)
        row.addWidget(self.url_edit, 1)
        row.addWidget(paste)
        row.addWidget(self.analyse_btn)
        hint = QLabel("Supported by yt-dlp: " + ", ".join(SUPPORTED_SOURCE_HINTS) + ", and many more")
        hint.setObjectName("mutedSmall")
        hint.setWordWrap(True)
        layout.addWidget(label)
        layout.addLayout(row)
        layout.addWidget(hint)
        parent.addWidget(card)

    def _build_platform_bar(self, parent):
        """Horizontally scrollable row of branded platform pills."""
        outer = QFrame()
        outer.setObjectName("platformBar")
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(4)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(2, 0, 2, 0)
        lbl = QLabel("SUPPORTED PLATFORMS")
        lbl.setObjectName("eyebrow")
        count_lbl = QLabel(f"{len(PLATFORM_PILLS)} platforms  ·  1000+ sites via yt-dlp")
        count_lbl.setObjectName("mutedSmall")
        header_row.addWidget(lbl)
        header_row.addStretch(1)
        header_row.addWidget(count_lbl)
        outer_layout.addLayout(header_row)

        scroll = QScrollArea()
        scroll.setObjectName("platformScroll")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(72)
        scroll.setFrameShape(QFrame.NoFrame)

        inner = QWidget()
        inner.setObjectName("platformInner")
        row = QHBoxLayout(inner)
        row.setContentsMargins(0, 4, 0, 4)
        row.setSpacing(8)

        for name, color, tags, caveat in PLATFORM_PILLS:
            pill = self._make_platform_pill(name, color, tags, caveat)
            row.addWidget(pill)
        row.addStretch(1)

        scroll.setWidget(inner)
        outer_layout.addWidget(scroll)
        parent.addWidget(outer)

    @staticmethod
    def _make_platform_pill(name, color, tags, caveat=None):
        """One branded card: colored left bar + name + tag chips + optional caveat."""
        frame = QFrame()
        frame.setObjectName("platformPill")
        frame.setFixedHeight(52)
        frame.setMinimumWidth(160)

        h = QHBoxLayout(frame)
        h.setContentsMargins(0, 0, 10, 0)
        h.setSpacing(0)

        # Colored left accent stripe
        stripe = QFrame()
        stripe.setFixedWidth(4)
        stripe.setObjectName("platformStripe")
        stripe.setStyleSheet(f"background:{color}; border-radius:3px;")
        h.addWidget(stripe)
        h.addSpacing(9)

        v = QVBoxLayout()
        v.setSpacing(3)
        v.setContentsMargins(0, 6, 0, 6)

        # Name row: platform name + optional caveat badge
        name_row = QHBoxLayout()
        name_row.setSpacing(5)
        name_row.setContentsMargins(0, 0, 0, 0)
        name_lbl = QLabel(name)
        name_lbl.setObjectName("platformName")
        name_lbl.setStyleSheet(f"color:{color}; font-size:12px; font-weight:700;")
        name_row.addWidget(name_lbl)
        if caveat:
            caveat_lbl = QLabel(caveat)
            caveat_lbl.setStyleSheet(
                "color:#F59E0B; background:transparent;"
                "border:1px solid #F59E0B55;"
                "border-radius:3px; font-size:8px; padding:0px 3px;"
            )
            name_row.addWidget(caveat_lbl)
        name_row.addStretch(1)
        v.addLayout(name_row)

        tags_row = QHBoxLayout()
        tags_row.setSpacing(4)
        tags_row.setContentsMargins(0, 0, 0, 0)
        for tag in tags:
            chip = QLabel(tag)
            chip.setObjectName("tagChip")
            chip.setStyleSheet(
                f"color:{color}; background:transparent;"
                f"border:1px solid {color}44;"
                f"border-radius:3px; font-size:9px; padding:0px 4px;"
            )
            tags_row.addWidget(chip)
        tags_row.addStretch(1)
        v.addLayout(tags_row)

        h.addLayout(v)
        return frame

    def _build_info_card(self, parent):
        card = make_card()
        card.setMinimumHeight(104)
        layout = QHBoxLayout(card)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(16)
        self.thumb_label = QLabel()
        self.thumb_label.setObjectName("thumb")
        self.thumb_label.setFixedSize(THUMBNAIL_SIZE)
        self.thumb_label.setAlignment(Qt.AlignCenter)
        self._set_thumbnail_placeholder("Preview")

        text_box = QVBoxLayout()
        text_box.setSpacing(8)
        self.info_title = QLabel("Paste a link and click Analyse to load media info")
        self.info_title.setObjectName("infoTitle")
        self.info_title.setWordWrap(True)
        self.info_meta = QLabel("")
        self.info_meta.setObjectName("muted")
        self.info_meta.setWordWrap(True)
        text_box.addWidget(self.info_title)
        text_box.addWidget(self.info_meta)
        layout.addWidget(self.thumb_label)
        layout.addLayout(text_box, 1)
        parent.addWidget(card)

    def _build_options_card(self, parent):
        card = make_card()
        card.setMinimumHeight(118)
        layout = QGridLayout(card)
        layout.setContentsMargins(18, 15, 18, 15)
        layout.setHorizontalSpacing(24)
        layout.setVerticalSpacing(10)

        layout.addWidget(self._eyebrow("MEDIA TYPE"), 0, 0)
        layout.addWidget(self._eyebrow("FORMAT"), 0, 1)
        layout.addWidget(self._eyebrow("QUALITY"), 0, 2)
        layout.addWidget(self._eyebrow("OPTIONS"), 0, 3, 1, 2)

        type_row = QHBoxLayout()
        self.video_radio = QRadioButton("Video")
        self.audio_radio = QRadioButton("Audio")
        self.video_radio.setChecked(True)
        self.type_group = QButtonGroup(self)
        self.type_group.addButton(self.video_radio)
        self.type_group.addButton(self.audio_radio)
        self.video_radio.toggled.connect(self._on_type_changed)
        type_row.addWidget(self.video_radio)
        type_row.addWidget(self.audio_radio)
        type_row.addStretch(1)
        layout.addLayout(type_row, 1, 0)

        self.format_combo = QComboBox()
        self.format_combo.setMinimumHeight(36)
        self.format_combo.setMinimumWidth(96)
        self.format_combo.addItems(VIDEO_FORMATS)
        self.quality_combo = QComboBox()
        self.quality_combo.setMinimumHeight(36)
        self.quality_combo.setMinimumWidth(210)
        self.quality_combo.addItems(VIDEO_QUALITIES)
        layout.addWidget(self.format_combo, 1, 1)
        layout.addWidget(self.quality_combo, 1, 2)

        self.playlist_check = QCheckBox("Full Playlist")
        self.subs_check = QCheckBox("Subtitles")
        self.thumb_check = QCheckBox("Embed Thumbnail")
        self.sponsor_check = QCheckBox("SponsorBlock")
        layout.addWidget(self.playlist_check, 1, 3)
        layout.addWidget(self.subs_check, 1, 4)
        layout.addWidget(self.thumb_check, 2, 3)
        layout.addWidget(self.sponsor_check, 2, 4)

        for col in range(5):
            layout.setColumnStretch(col, 1 if col in (2, 4) else 0)
        self._set_feature_options({})
        parent.addWidget(card)

    def _build_progress_card(self, parent):
        card = make_card()
        card.setMinimumHeight(70)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 13, 18, 13)
        row = QHBoxLayout()
        self.status_label = QLabel("Idle - ready to download")
        self.status_label.setObjectName("muted")
        self.speed_label = QLabel("")
        self.speed_label.setObjectName("mutedSmall")
        self.eta_label = QLabel("")
        self.eta_label.setObjectName("mutedSmall")
        row.addWidget(self.status_label, 1)
        row.addWidget(self.speed_label)
        row.addWidget(self.eta_label)
        self.progress = QProgressBar()
        self.progress.setRange(0, 1000)
        self.progress.setValue(0)
        self.progress.setTextVisible(False)
        layout.addLayout(row)
        layout.addWidget(self.progress)
        parent.addWidget(card)

    def _build_actions(self, parent):
        row = QHBoxLayout()
        row.setSpacing(10)
        self.download_btn = QPushButton("Start Download")
        self.download_btn.setObjectName("primaryButton")
        self.download_btn.setMinimumHeight(48)
        self.download_btn.clicked.connect(self.start_download)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("dangerButton")
        self.cancel_btn.setMinimumHeight(48)
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self.cancel_download)
        open_btn = QPushButton("Open Folder")
        open_btn.setObjectName("secondaryButton")
        open_btn.setMinimumHeight(48)
        open_btn.setMinimumWidth(120)
        open_btn.clicked.connect(self.open_folder)
        row.addWidget(self.download_btn, 1)
        row.addWidget(self.cancel_btn)
        row.addWidget(open_btn)
        parent.addLayout(row)

    def _build_log(self, parent):
        row = QHBoxLayout()
        label = QLabel("CONSOLE OUTPUT")
        label.setObjectName("eyebrow")
        clear = QPushButton("Clear")
        clear.setObjectName("flatButton")
        clear.clicked.connect(self.log_edit_clear)
        row.addWidget(label)
        row.addStretch(1)
        row.addWidget(clear)
        self.log_edit = QTextEdit()
        self.log_edit.setObjectName("logBox")
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(128)
        self.log_edit.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        parent.addLayout(row)
        parent.addWidget(self.log_edit)

    @staticmethod
    def _eyebrow(text):
        label = QLabel(text)
        label.setObjectName("eyebrow")
        return label

    def _on_type_changed(self):
        if self.video_radio.isChecked():
            self.format_combo.clear()
            self.format_combo.addItems(VIDEO_FORMATS)
            self.quality_combo.clear()
            self.quality_combo.addItems(VIDEO_QUALITIES)
        else:
            self.format_combo.clear()
            self.format_combo.addItems(AUDIO_FORMATS)
            self.quality_combo.clear()
            self.quality_combo.addItems(AUDIO_QUALITIES)

    def paste_url(self):
        self.url_edit.setText(QApplication.clipboard().text().strip())

    def log(self, message):
        self.log_edit.append(f"[{datetime.now().strftime('%H:%M:%S')}]  {message}")

    def log_edit_clear(self):
        self.log_edit.clear()

    def _set_feature_options(self, features):
        self.media_features = features
        option_map = [
            ("playlist", self.playlist_check),
            ("subtitles", self.subs_check),
            ("thumbnail", self.thumb_check),
            ("sponsorblock", self.sponsor_check),
        ]
        for key, checkbox in option_map:
            enabled = bool(features.get(key))
            checkbox.setEnabled(enabled)
            if not enabled:
                checkbox.setChecked(False)

    @staticmethod
    def _extract_thumbnail_url(info):
        thumbs = info.get("thumbnails") or []
        if thumbs:
            thumbs = sorted(
                thumbs,
                key=lambda item: (item.get("width") or 0) * (item.get("height") or 0),
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

    @staticmethod
    def _available_video_qualities(info):
        """Return quality options limited to resolutions actually in this video."""
        formats = info.get("formats") or []
        # Collect unique heights from video-bearing formats.
        heights = set()
        for fmt in formats:
            h = fmt.get("height")
            vcodec = fmt.get("vcodec") or ""
            if h and vcodec and vcodec != "none":
                heights.add(int(h))

        if not heights:
            # Fallback: show full list if no height info found.
            return list(VIDEO_QUALITIES)

        max_height = max(heights)

        # Map each label to its pixel height.
        label_heights = [
            ("4320p (8K)",   4320),
            ("2160p (4K)",   2160),
            ("1440p (2K)",   1440),
            ("1080p (FHD)",  1080),
            ("720p (HD)",     720),
            ("480p",          480),
            ("360p",          360),
            ("240p",          240),
            ("144p",          144),
        ]

        filtered = ["Best Available"]
        for label, h in label_heights:
            # Include this resolution only if the video actually has it
            # (within a small tolerance) OR if it is below the max height
            # so the user can choose a lower quality.
            if any(abs(fh - h) <= 10 for fh in heights) or h < max_height:
                filtered.append(label)
        filtered.append("Worst")
        return filtered

    @staticmethod
    def _analyze_features(info):
        info_type = info.get("_type") or ""
        entries = info.get("entries")
        extractor = (info.get("extractor_key") or info.get("extractor") or "").lower()
        webpage_url = (info.get("webpage_url") or info.get("original_url") or "").lower()
        return {
            "playlist": info_type in {"playlist", "multi_video"} or entries is not None,
            "subtitles": bool(info.get("subtitles") or info.get("automatic_captions")),
            "thumbnail": bool(DownloadPage._extract_thumbnail_url(info)),
            "sponsorblock": "youtube" in extractor or "youtu.be" in webpage_url or "youtube.com" in webpage_url,
        }

    def fetch_info(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "No URL", "Please paste a media URL first.")
            return
        self._set_thumbnail_placeholder("Preview")
        self._set_feature_options({})
        self.info_title.setText("Analysing media link...")
        self.info_meta.setText("")
        self.analyse_btn.setEnabled(False)
        self.analyse_btn.setText("Analysing...")
        self.log(f"Fetching info: {url}")
        playlist = self.playlist_check.isChecked()
        threading.Thread(target=self._fetch_worker, args=(url, playlist), daemon=True).start()

    def _fetch_worker(self, url, playlist):
        try:
            opts = apply_auth_opts(
                {
                    "quiet": True,
                    "no_warnings": True,
                    "skip_download": True,
                    "noplaylist": not playlist,
                },
                self.app_window.cfg,
            )
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
            if not info:
                raise yt_dlp.utils.DownloadError("No media information was returned for this URL.")
            if not playlist and not info.get("formats") and not info.get("url"):
                raise yt_dlp.utils.DownloadError("No downloadable video formats were found for this URL.")
            self.signals.info_ready.emit({"info": info, "url": url})
        except Exception as exc:
            self.signals.fetch_error.emit(str(exc))

    def _on_info_ready(self, payload):
        info = payload["info"]
        title = info.get("title", "Unknown")
        uploader = info.get("uploader", "")
        duration = fmt_duration(info.get("duration"))
        views = info.get("view_count")
        formats = len(info.get("formats", []))
        extractor = info.get("extractor_key") or info.get("extractor") or ""
        webpage_url = info.get("webpage_url") or payload["url"]
        views_text = f"{views:,} views" if views else ""
        parts = [p for p in (extractor, uploader, duration, views_text, f"{formats} formats" if formats else "") if p]

        self.info_title.setText(title)
        self.info_meta.setText("  ·  ".join(parts))
        self._set_feature_options(self._analyze_features(info))

        # Repopulate quality combo with only the resolutions this video has.
        if self.video_radio.isChecked():
            available_qualities = self._available_video_qualities(info)
            self.quality_combo.blockSignals(True)
            self.quality_combo.clear()
            self.quality_combo.addItems(available_qualities)
            self.quality_combo.blockSignals(False)

        self.log(f'OK  "{title}"  |  {duration}  |  {formats} formats')

        thumb_url = self._extract_thumbnail_url(info)
        if thumb_url:
            threading.Thread(target=self._thumbnail_worker, args=(thumb_url, webpage_url), daemon=True).start()
        else:
            self._set_thumbnail_placeholder("No preview")
        self.analyse_btn.setEnabled(True)
        self.analyse_btn.setText("Analyse")

    def _on_fetch_error(self, msg):
        self.log(f"ERROR  {clean_error_text(msg)}")
        self.analyse_btn.setEnabled(True)
        self.analyse_btn.setText("Analyse")
        ErrorDialog(self, msg, fetch=True).exec_()

    def _thumbnail_worker(self, thumb_url, referer):
        try:
            raw = self._download_thumbnail_bytes(thumb_url, referer)
            self.signals.thumb_ready.emit(raw)
        except Exception as exc:
            self.signals.thumb_failed.emit(str(exc))

    def _download_thumbnail_bytes(self, thumb_url, referer):
        opts = apply_auth_opts({"quiet": True, "no_warnings": True}, self.app_window.cfg)
        headers = {"User-Agent": "Mozilla/5.0"}
        if referer:
            headers["Referer"] = referer

        last_error = None
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                response = ydl.urlopen(urllib.request.Request(thumb_url, headers=headers))
                return response.read(3 * 1024 * 1024)
        except Exception as exc:
            last_error = exc

        try:
            req = urllib.request.Request(thumb_url, headers=headers)
            with urllib.request.urlopen(req, timeout=12) as response:
                return response.read(3 * 1024 * 1024)
        except Exception:
            raise last_error

    def _set_thumbnail_from_bytes(self, raw):
        pixmap = QPixmap()
        if pixmap.loadFromData(raw):
            self.thumb_pixmap = pixmap.scaled(
                THUMBNAIL_SIZE,
                Qt.KeepAspectRatioByExpanding,
                Qt.SmoothTransformation,
            )
            self.thumb_label.setPixmap(self.thumb_pixmap)
            self.thumb_label.setText("")
        else:
            self._set_thumbnail_placeholder("No preview")

    def _on_thumb_failed(self, msg):
        self.log(f"Thumbnail unavailable: {msg}")
        self._set_thumbnail_placeholder("No preview")

    def _set_thumbnail_placeholder(self, text):
        self.thumb_pixmap = None
        self.thumb_label.setPixmap(QPixmap())
        self.thumb_label.setText(f"Play\n{text}")

    def start_download(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "No URL", "Please paste a media URL first.")
            return
        if self.download_thread is not None and self.download_thread.is_alive():
            QMessageBox.information(self, "Busy", "A download is already in progress.")
            return

        self.cancel_event.clear()
        self.progress.setValue(0)
        self.status_label.setText("Starting download...")
        self.speed_label.setText("")
        self.eta_label.setText("")
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)

        ext = self.format_combo.currentText()
        quality = self.quality_combo.currentText()
        is_audio = self.audio_radio.isChecked()
        options = {
            "subs": self.subs_check.isChecked(),
            "embed_thumb": self.thumb_check.isChecked(),
            "sponsor_block": self.sponsor_check.isChecked(),
            "playlist": self.playlist_check.isChecked(),
        }
        self.log(
            f"Starting  [{'Audio' if is_audio else 'Video'}]  [{quality}]  [.{ext}]  "
            f"{'playlist' if options['playlist'] else 'single'}"
        )
        self.download_thread = threading.Thread(
            target=self._download_worker,
            args=(url, self.app_window.cfg["output_dir"], ext, quality, is_audio, options),
            daemon=True,
        )
        self.download_thread.start()

    def _download_worker(self, url, out_dir, ext, quality, is_audio, options):
        start = time.time()

        def hook(data):
            if self.cancel_event.is_set():
                raise yt_dlp.utils.DownloadError("Cancelled by user")
            status = data.get("status")
            if status == "downloading":
                total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
                done = data.get("downloaded_bytes", 0)
                speed = data.get("speed") or 0
                eta = data.get("eta") or 0
                pct = done / total if total else 0
                pct_text = f"Downloading {pct * 100:.1f}%  {fmt_size(done)} / {fmt_size(total)}"
                speed_text = f"{speed / 1024 / 1024:.1f} MB/s" if speed else ""
                eta_text = f"ETA {eta}s" if eta else ""
                self.signals.progress.emit(pct, pct_text, speed_text, eta_text)
            elif status == "finished":
                self.signals.progress.emit(0.99, "Processing / merging...", "", "")

        try:
            opts = build_ydl_opts(
                self.app_window.cfg,
                out_dir,
                ext,
                quality,
                is_audio,
                hook,
                subs=options["subs"],
                embed_thumb=options["embed_thumb"],
                sponsor_block=options["sponsor_block"],
                playlist=options["playlist"],
            )
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url)
                title = (info.get("title") or url) if info else url
            elapsed = time.time() - start
            self.signals.done.emit(title, url, ext, is_audio, elapsed)
        except yt_dlp.utils.DownloadError as exc:
            if "Cancelled" in str(exc):
                self.signals.cancelled.emit()
            else:
                self.signals.download_error.emit(str(exc))
        except Exception as exc:
            self.signals.download_error.emit(str(exc))

    def _on_progress(self, pct, status, speed, eta):
        self.progress.setValue(max(0, min(1000, int(pct * 1000))))
        self.status_label.setText(status)
        self.speed_label.setText(speed)
        self.eta_label.setText(eta)

    def _on_done(self, title, url, ext, is_audio, elapsed):
        self.progress.setValue(1000)
        self.status_label.setText(f"Completed in {elapsed:.1f}s")
        self.speed_label.setText("")
        self.eta_label.setText("")
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.log(f'DONE  "{title}"  ({elapsed:.1f}s)')
        self.app_window.add_history(
            {
                "title": title,
                "url": url,
                "ext": ext,
                "type": "Audio" if is_audio else "Video",
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
            }
        )

    def _on_cancelled(self):
        self.progress.setValue(0)
        self.status_label.setText("Cancelled")
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.log("CANCELLED  Download stopped by user")

    def _on_download_error(self, msg):
        clean = clean_error_text(msg)
        self.status_label.setText("Download failed")
        self.speed_label.setText("")
        self.eta_label.setText("")
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.log(f"ERROR  {clean}")
        ErrorDialog(self, clean, fetch=False).exec_()

    def cancel_download(self):
        self.cancel_event.set()
        self.status_label.setText("Cancelling...")

    def open_folder(self):
        directory = self.app_window.cfg["output_dir"]
        try:
            if sys.platform == "win32":
                os.startfile(directory)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", directory])
            else:
                subprocess.Popen(["xdg-open", directory])
        except Exception as exc:
            QMessageBox.critical(self, "Error", str(exc))

    def apply_palette(self, palette):
        # Style the platform bar container and pills to match the active theme.
        self.setStyleSheet(
            self.styleSheet() +
            f"""
            #platformBar {{
                background: transparent;
            }}
            #platformScroll, #platformInner {{
                background: transparent;
            }}
            #platformPill {{
                background: {palette['card']};
                border: 1px solid {palette['border']};
                border-radius: 7px;
            }}
            #platformPill:hover {{
                background: {palette['selected']};
            }}
            """
        )


class HistoryPage(QWidget):
    def __init__(self, app_window):
        super().__init__()
        self.setObjectName("page")
        self.app_window = app_window
        self._all = []
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(70)
        top = QHBoxLayout(topbar)
        top.setContentsMargins(28, 12, 28, 12)
        labels = QVBoxLayout()
        title = QLabel("Download History")
        title.setObjectName("pageTitle")
        subtitle = QLabel("All previous downloads, searchable and re-downloadable")
        subtitle.setObjectName("muted")
        labels.addWidget(title)
        labels.addWidget(subtitle)
        clear = QPushButton("Clear All")
        clear.setObjectName("dangerButton")
        clear.clicked.connect(self.clear_all)
        top.addLayout(labels, 1)
        top.addWidget(clear)
        root.addWidget(topbar)

        body = QVBoxLayout()
        body.setContentsMargins(24, 18, 24, 20)
        body.setSpacing(12)
        self.stats = QLabel("No downloads yet")
        self.stats.setObjectName("muted")
        stats_card = make_card()
        stats_layout = QVBoxLayout(stats_card)
        stats_layout.addWidget(self.stats)
        self.search = QLineEdit()
        self.search.setMinimumHeight(40)
        self.search.setPlaceholderText("Search by title or URL...")
        self.search.textChanged.connect(self._render)
        self.list = QListWidget()
        self.list.setObjectName("historyList")
        self.list.itemDoubleClicked.connect(self.redownload)
        body.addWidget(stats_card)
        body.addWidget(self.search)
        body.addWidget(self.list, 1)
        root.addLayout(body, 1)

    def refresh(self, history):
        self._all = list(history)
        n = len(self._all)
        n_video = sum(1 for item in self._all if item.get("type") == "Video")
        n_audio = n - n_video
        self.stats.setText(f"{n} total  ·  {n_video} video(s)  ·  {n_audio} audio file(s)" if n else "No downloads yet")
        self._render()

    def _render(self):
        query = self.search.text().lower()
        items = [
            item
            for item in self._all
            if query in item.get("title", "").lower() or query in item.get("url", "").lower()
        ]
        self.list.clear()
        if not items:
            self.list.addItem("No results." if query else "No downloads yet. Start downloading to build history.")
            return
        for entry in items:
            text = (
                f"{entry.get('title', 'Unknown')}\n"
                f".{entry.get('ext', '')}  ·  {entry.get('type', '')}  ·  {entry.get('timestamp', '')}"
            )
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, entry.get("url", ""))
            item.setSizeHint(QSize(100, 72))
            self.list.addItem(item)

    def redownload(self, item):
        url = item.data(Qt.UserRole)
        if url:
            self.app_window.download_page.url_edit.setText(url)
            self.app_window.navigate("Download")

    def clear_all(self):
        if QMessageBox.question(self, "Clear History", "Delete all download history?") == QMessageBox.Yes:
            self.app_window.history.clear()
            save_history([])
            self.refresh([])

    def apply_palette(self, palette):
        pass


class SettingsPage(QWidget):
    def __init__(self, app_window):
        super().__init__()
        self.setObjectName("page")
        self.app_window = app_window
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        topbar = QFrame()
        topbar.setObjectName("topbar")
        topbar.setFixedHeight(70)
        top_layout = QVBoxLayout(topbar)
        top_layout.setContentsMargins(28, 12, 28, 12)
        title = QLabel("Settings")
        title.setObjectName("pageTitle")
        subtitle = QLabel("Configure preferences and apply them to the running app")
        subtitle.setObjectName("muted")
        top_layout.addWidget(title)
        top_layout.addWidget(subtitle)
        root.addWidget(topbar)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("scrollArea")
        body = QWidget()
        body.setObjectName("scrollBody")
        form = QGridLayout(body)
        form.setContentsMargins(28, 22, 28, 24)
        form.setHorizontalSpacing(22)
        form.setVerticalSpacing(14)
        scroll.setWidget(body)
        root.addWidget(scroll, 1)

        row = 0
        row = self._section(form, row, "OUTPUT")
        self.dir_edit = QLineEdit()
        self.dir_edit.setMinimumHeight(38)
        browse = QPushButton("Browse")
        browse.setObjectName("secondaryButton")
        browse.setMinimumHeight(38)
        browse.clicked.connect(self.browse_dir)
        dir_row = QHBoxLayout()
        dir_row.addWidget(self.dir_edit, 1)
        dir_row.addWidget(browse)
        self._add_row(form, row, "Save Location", dir_row)
        row += 1

        self.history_edit = QLineEdit()
        self.history_edit.setMinimumHeight(36)
        self.history_edit.setMaximumWidth(100)
        self._add_row(form, row, "Max History Entries", self.history_edit)
        row += 1

        self.concurrent_combo = QComboBox()
        self.concurrent_combo.setMinimumHeight(36)
        self.concurrent_combo.addItems(["1", "2", "4", "8", "16"])
        self.concurrent_combo.setMaximumWidth(120)
        self._add_row(form, row, "Concurrent Fragments", self.concurrent_combo)
        row += 1

        row = self._section(form, row, "ADVANCED")
        self.ffmpeg_edit = QLineEdit()
        self.ffmpeg_edit.setMinimumHeight(38)
        self.ffmpeg_edit.setPlaceholderText(r"e.g. C:\ffmpeg\bin")
        self._add_row(form, row, "FFmpeg Path (blank = auto-detect)", self.ffmpeg_edit)
        row += 1

        self.cookie_edit = QLineEdit()
        self.cookie_edit.setMinimumHeight(38)
        self.cookie_edit.setPlaceholderText("cookies.txt for login-required sites")
        cookie_browse = QPushButton("Browse")
        cookie_browse.setObjectName("secondaryButton")
        cookie_browse.setMinimumHeight(38)
        cookie_browse.clicked.connect(self.browse_cookie)
        cookie_row = QHBoxLayout()
        cookie_row.addWidget(self.cookie_edit, 1)
        cookie_row.addWidget(cookie_browse)
        self._add_row(form, row, "Cookie File (optional)", cookie_row)
        row += 1

        self.browser_combo = QComboBox()
        self.browser_combo.setMinimumHeight(36)
        self.browser_combo.addItems(BROWSER_COOKIE_SOURCES)
        self.browser_combo.setMaximumWidth(160)
        self._add_row(form, row, "Use Browser Cookies", self.browser_combo)
        row += 1

        row = self._section(form, row, "APPEARANCE")
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumHeight(36)
        self.theme_combo.addItems(["light", "dark", "system"])
        self.theme_combo.setMaximumWidth(160)
        self.theme_combo.currentTextChanged.connect(self.preview_theme)
        self._add_row(form, row, "Theme", self.theme_combo)
        row += 1

        about = make_card()
        about_layout = QVBoxLayout(about)
        about_layout.setContentsMargins(18, 14, 18, 14)
        about_layout.addWidget(QLabel(f"{APP_NAME}  ·  Version {VERSION}"))
        about_layout.addWidget(QLabel("Powered by yt-dlp  ·  PyQt5  ·  Python 3"))
        form.addWidget(about, row, 0, 1, 2)
        row += 1

        save = QPushButton("Save Settings")
        save.setObjectName("primaryButton")
        save.setMinimumHeight(48)
        save.clicked.connect(self.save)
        form.addWidget(save, row, 0, 1, 2)
        form.setRowStretch(row + 1, 1)
        self.sync_from_config()

    @staticmethod
    def _section(form, row, title):
        label = QLabel(title)
        label.setObjectName("sectionLabel")
        form.addWidget(label, row, 0, 1, 2)
        return row + 1

    @staticmethod
    def _add_row(form, row, label_text, widget_or_layout):
        label = QLabel(label_text)
        label.setObjectName("muted")
        form.addWidget(label, row, 0)
        if isinstance(widget_or_layout, QHBoxLayout):
            form.addLayout(widget_or_layout, row, 1)
        else:
            form.addWidget(widget_or_layout, row, 1)

    def sync_from_config(self):
        cfg = self.app_window.cfg
        self.dir_edit.setText(cfg["output_dir"])
        self.history_edit.setText(str(cfg.get("max_history", 100)))
        self.concurrent_combo.setCurrentText(str(cfg.get("concurrent", "1")))
        self.ffmpeg_edit.setText(cfg.get("ffmpeg_path", ""))
        self.cookie_edit.setText(cfg.get("cookie_file", ""))
        self.browser_combo.setCurrentText(cfg.get("browser_cookies", "None"))
        self.theme_combo.blockSignals(True)
        self.theme_combo.setCurrentText(cfg.get("theme", "dark"))
        self.theme_combo.blockSignals(False)

    def preview_theme(self, theme):
        self.app_window.apply_theme(theme)

    def browse_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Select save folder", self.dir_edit.text())
        if directory:
            self.dir_edit.setText(directory)

    def browse_cookie(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select cookies.txt", "", "Cookie files (*.txt);;All files (*)")
        if path:
            self.cookie_edit.setText(path)

    def save(self):
        cfg = self.app_window.cfg
        cfg["output_dir"] = self.dir_edit.text().strip() or DEFAULT_CONFIG["output_dir"]
        cfg["ffmpeg_path"] = self.ffmpeg_edit.text().strip()
        cfg["theme"] = self.theme_combo.currentText()
        cfg["concurrent"] = self.concurrent_combo.currentText()
        cfg["cookie_file"] = self.cookie_edit.text().strip()
        cfg["browser_cookies"] = self.browser_combo.currentText()
        try:
            cfg["max_history"] = max(1, int(self.history_edit.text()))
        except ValueError:
            cfg["max_history"] = DEFAULT_CONFIG["max_history"]
            self.history_edit.setText(str(cfg["max_history"]))
        save_config(cfg)
        self.app_window.apply_runtime_settings()
        QMessageBox.information(self, "Saved", "Settings applied to the running app.")

    def apply_palette(self, palette):
        pass


def build_stylesheet(p):
    return f"""
    QMainWindow, QWidget#appRoot, QWidget#page, QStackedWidget#contentStack, QWidget#scrollBody {{
        background: {p['root']};
        color: {p['text']};
        font-family: Segoe UI, Arial;
        font-size: 13px;
    }}
    QLabel {{
        background: transparent;
        color: {p['text']};
    }}
    #sidebar, #topbar {{
        background: {p['panel']};
    }}
    #scrollArea {{
        border: none;
        background: {p['root']};
    }}
    QScrollArea > QWidget > QWidget {{
        background: {p['root']};
    }}
    #card {{
        background: {p['card']};
        border: 1px solid {p['border']};
        border-radius: 8px;
    }}
    #brand {{
        color: {p['text']};
        font-size: 24px;
        font-weight: 700;
    }}
    #pageTitle {{
        color: {p['text']};
        font-size: 19px;
        font-weight: 700;
    }}
    #infoTitle {{
        color: {p['text']};
        font-size: 14px;
        font-weight: 700;
    }}
    #muted, QLabel#muted {{
        color: {p['muted']};
    }}
    #mutedSmall, QLabel#mutedSmall {{
        color: {p['dim']};
        font-size: 11px;
    }}
    #eyebrow, #sectionLabel {{
        color: {p['dim']};
        font-size: 11px;
        font-weight: 700;
    }}
    QLineEdit, QComboBox, QTextEdit {{
        background: {p['input']};
        color: {p['text']};
        border: 1px solid {p['border']};
        border-radius: 7px;
        padding: 8px 10px;
        selection-background-color: {p['accent']};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 22px;
    }}
    QPushButton {{
        background: {p['input']};
        color: {p['muted']};
        border: 1px solid {p['border']};
        border-radius: 7px;
        padding: 9px 15px;
        font-size: 13px;
    }}
    QPushButton:hover {{
        background: {p['border']};
    }}
    QPushButton#primaryButton {{
        background: {p['accent']};
        border-color: {p['accent']};
        color: white;
        font-weight: 700;
    }}
    QPushButton#primaryButton:hover {{
        background: {p['accent_hover']};
    }}
    QPushButton#dangerButton {{
        color: {p['danger']};
        border-color: {p['danger']};
    }}
    QPushButton#flatButton {{
        border: none;
        background: transparent;
        color: {p['dim']};
    }}
    QPushButton#navButton {{
        text-align: left;
        border: none;
        background: transparent;
        color: {p['muted']};
        padding-left: 18px;
        font-size: 13px;
    }}
    QPushButton#navButton:checked {{
        background: {p['selected']};
        color: {p['accent']};
    }}
    QRadioButton, QCheckBox {{
        color: {p['muted']};
        spacing: 8px;
        background: transparent;
        font-size: 13px;
    }}
    QRadioButton::indicator, QCheckBox::indicator {{
        width: 19px;
        height: 19px;
    }}
    QRadioButton::indicator:checked, QCheckBox::indicator:checked {{
        background: {p['accent']};
        border: 1px solid {p['accent']};
        border-radius: 4px;
    }}
    QRadioButton::indicator:unchecked, QCheckBox::indicator:unchecked {{
        background: {p['input']};
        border: 1px solid {p['border']};
        border-radius: 4px;
    }}
    QRadioButton::indicator {{
        border-radius: 9px;
    }}
    QProgressBar {{
        background: {p['input']};
        border: none;
        border-radius: 4px;
        height: 8px;
    }}
    QProgressBar::chunk {{
        background: {p['accent']};
        border-radius: 4px;
    }}
    QLabel#thumb {{
        background: {p['input']};
        border: 1px solid {p['border']};
        border-radius: 7px;
        color: {p['dim']};
        font-weight: 700;
    }}
    QTextEdit#logBox, QTextEdit#detailsBox {{
        font-family: Consolas;
        font-size: 11px;
        color: {p['muted']};
    }}
    QListWidget#historyList {{
        background: transparent;
        border: none;
        color: {p['text']};
    }}
    QListWidget#historyList::item {{
        background: {p['card']};
        border: 1px solid {p['border']};
        border-radius: 7px;
        padding: 10px;
        margin-bottom: 5px;
    }}
    QListWidget#historyList::item:selected {{
        background: {p['selected']};
    }}
    """


def main():
    # Set AppUserModelID BEFORE creating QApplication so Windows
    # correctly groups the window and shows the icon in the taskbar.
    if sys.platform == "win32":
        try:
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
                "MediaFlow.Pro.Desktop"
            )
        except Exception:
            pass

    qt_app = QApplication(sys.argv)

    # Apply icon to the QApplication so it propagates to the taskbar.
    icon_path = resource_path("assets", ICON_FILE)
    if icon_path.exists():
        app_icon = QIcon(str(icon_path))
    else:
        png_path = resource_path("assets", ICON_PNG_FILE)
        app_icon = QIcon(str(png_path)) if png_path.exists() else QIcon()
    qt_app.setWindowIcon(app_icon)

    window = MainWindow(qt_app)
    window.show()
    sys.exit(qt_app.exec_())


if __name__ == "__main__":
    main()
