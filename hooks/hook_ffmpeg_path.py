"""
Runtime hook: make bundled ffmpeg.exe visible to yt-dlp when running as a
PyInstaller one-file executable.

PyInstaller extracts bundled binaries to sys._MEIPASS at runtime.
This hook prepends that directory to PATH so yt-dlp's automatic FFmpeg
detection finds ffmpeg.exe / ffprobe.exe without any user configuration.
"""

import os
import sys

if hasattr(sys, "_MEIPASS"):
    meipass = sys._MEIPASS
    current_path = os.environ.get("PATH", "")
    if meipass not in current_path:
        os.environ["PATH"] = meipass + os.pathsep + current_path
