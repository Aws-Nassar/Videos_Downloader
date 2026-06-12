# MediaFlow Pro

**MediaFlow Pro** is a desktop media downloader for Windows, built with Python, PyQt5, and yt-dlp. It downloads video or audio from YouTube and hundreds of other supported sources — including Facebook, Instagram, TikTok, Vimeo, SoundCloud, Google Drive, Twitch, Reddit, and more.

> Only download content you have the right to save. Some services require login cookies or public sharing.

## Features

| Category | Details |
|---|---|
| **Video** | Quality selection (144p → 8K), format choice (mp4, mkv, webm, avi, mov, flv) |
| **Audio** | Extraction to mp3, m4a, aac, opus, flac, wav, ogg |
| **Playlists** | Full playlist downloads with ordered filenames |
| **Subtitles** | Optional subtitle downloads + embedded thumbnails |
| **SponsorBlock** | Optional SponsorBlock chapter processing |
| **History** | Download history with search and re-download shortcuts |
| **Cookies** | Support for cookies.txt or browser-cookie extraction |
| **Portable** | FFmpeg bundled inside the Windows executable — no separate install for end users |

## Project Structure

```
.
├── app.py                      # Main PyQt5 application
├── assets/                     # App icons (mediaflow.ico, mediaflow.png)
├── hooks/
│   └── hook_ffmpeg_path.py     # PyInstaller runtime hook — adds bundled FFmpeg to PATH
├── tools/
│   ├── build_exe.ps1           # PowerShell build helper
│   ├── generate_icon.py        # Icon generation utility
│   ├── ffmpeg.exe              # ← place FFmpeg binaries here (not committed)
│   ├── ffprobe.exe             # ← place FFmpeg binaries here (not committed)
│   └── ffplay.exe              # ← place FFmpeg binaries here (not committed)
├── MediaFlow.spec              # PyInstaller one-file build spec
├── requirements.txt            # Runtime dependencies
├── requirements-dev.txt        # Runtime + build dependencies (includes PyInstaller)
├── .editorconfig
├── .gitignore
└── README.md
```

## Requirements

- **Python 3.10+**
- **FFmpeg** — required for merging separate video/audio streams, converting formats, and extracting audio
  - **Running from source**: Install FFmpeg and add its `bin` folder to your system PATH, or set the path in the app's **Settings → FFmpeg Path**
  - **Running the built `.exe`**: FFmpeg is bundled automatically at build time
  - Download FFmpeg from [BtbN/FFmpeg-Builds](https://github.com/BtbN/FFmpeg-Builds/releases) (`ffmpeg-master-latest-win64-gpl.zip`)
- Internet access

## Run From Source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

If FFmpeg is not on your PATH, open **Settings** and set the **FFmpeg Path** field to the folder containing `ffmpeg.exe`.

## Build the Executable

Place the three FFmpeg binaries in `tools\`:

```
tools\ffmpeg.exe
tools\ffprobe.exe
tools\ffplay.exe
```

If they are not in `tools\`, the build falls back to whatever `ffmpeg.exe` is on your system PATH. If FFmpeg is found neither in `tools\` nor on PATH, the executable will still work but require manual FFmpeg configuration in Settings.

```powershell
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
pyinstaller MediaFlow.spec
```

Or use the helper script:

```powershell
.\tools\build_exe.ps1
```

Output: `dist\MediaFlow.exe`

## Downloading From Other Sources

MediaFlow uses yt-dlp, so source support comes from yt-dlp extractors rather than custom code for each site. Paste a supported URL, click **Analyse**, choose settings, then click **Start Download**.

| Source | Notes |
|---|---|
| **YouTube** | Videos, Shorts, playlists, and most public streams |
| **Facebook / Instagram** | Often need cookies (private/age-gated/login-gated links) |
| **Google Drive** | Must be publicly shared or shared with your account |
| **SoundCloud, Vimeo, TikTok, Twitch, Reddit** | Public links usually work; restricted links may need cookies |

To use cookies, open **Settings** and choose either:
- **Cookie File** — a Netscape-format `cookies.txt` exported from your browser
- **Use Browser Cookies** — Chrome, Edge, Firefox, Brave, Opera, Vivaldi, or Chromium

## Configuration

Settings and history are stored locally in your user profile:

| File | Purpose |
|---|---|
| `%USERPROFILE%\.ytflow2_config.json` | App preferences (theme, output dir, FFmpeg path, etc.) |
| `%USERPROFILE%\.ytflow2_history.json` | Download history |

These are personal machine state and are not committed to the repository.

## Troubleshooting

| Symptom | Fix |
|---|---|
| "FFmpeg is missing or unavailable" (source run) | Install FFmpeg and set its path in Settings, or add it to PATH |
| "FFmpeg is missing or unavailable" (exe run) | Rebuild the exe after placing `ffmpeg.exe` in `tools\` |
| PyInstaller not found during build | Activate venv first, then `pip install -r requirements-dev.txt` |
| A site stops working | Update yt-dlp: `python -m pip install -U yt-dlp` |
| Private or login-required content fails | Enable browser cookies or supply a `cookies.txt` in Settings |
| Download fails with no clear error | Confirm the URL opens in your browser and try a different quality or format |
