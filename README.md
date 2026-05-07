# MediaFlow Pro

MediaFlow Pro is a desktop media downloader for Windows, built with Python, CustomTkinter, and yt-dlp. It can download video or audio from YouTube and many other yt-dlp supported sources, including Facebook, Instagram, TikTok, Vimeo, SoundCloud, Google Drive, Twitch, Reddit, and more.

> Some services require login cookies, public sharing settings, or direct access permission. Only download content you have the right to save.

## Features

- Clean desktop UI with Download, History, and Settings views
- Video downloads with quality selection up to the best available stream
- Audio extraction to mp3, m4a, aac, opus, flac, wav, or ogg
- Playlist downloads with ordered filenames
- Optional subtitles, embedded thumbnails, and SponsorBlock processing
- Download history with search and re-download shortcuts
- Optional cookies.txt or browser-cookie support for login-required sources
- Repeatable PyInstaller build script for creating a Windows executable

## Project Structure

```text
.
├── app.py                 # Main CustomTkinter application
├── assets/                # Optional app icons and bundled assets
├── tools/build_exe.ps1    # PyInstaller build helper
├── MediaFlow.spec         # One-file Windows build spec
├── requirements.txt       # Runtime dependencies
├── requirements-dev.txt   # Runtime + build dependencies
├── .gitignore
└── README.md
```

## Requirements

- Python 3.10 or newer
- FFmpeg installed and available in PATH
- Internet access

FFmpeg is required for merging separate video/audio streams and converting formats. Download it from <https://ffmpeg.org/download.html>.

## Run From Source

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

## Build The EXE

Install the build dependencies:

```powershell
python -m pip install -r requirements-dev.txt
```

Create a one-file executable:

```powershell
.\tools\build_exe.ps1
```

The executable will be written to `dist\MediaFlow.exe`.

To build a folder-based version instead:

```powershell
.\tools\build_exe.ps1 -Mode OneDir
```

## Downloading From Other Sources

MediaFlow uses yt-dlp, so source support comes from yt-dlp extractors rather than custom code for each website. Paste a supported media URL, click `Analyse`, choose video or audio settings, then start the download.

Notes for common sources:

- `YouTube`: works for videos, Shorts, playlists, and many public streams.
- `Facebook` and `Instagram`: often need cookies because many links are private, age-gated, region-gated, or login-gated.
- `Google Drive`: the file must be shared with your account or publicly accessible. Very large files may trigger Drive's own quota/virus-scan limits.
- `SoundCloud`, `Vimeo`, `TikTok`, `Twitch`, `Reddit`: public links usually work; restricted links may need cookies.

To use cookies, open `Settings` and choose either:

- `Cookie File`: a Netscape-format `cookies.txt`
- `Use Browser Cookies`: Chrome, Edge, Firefox, Brave, Opera, Vivaldi, or Chromium

After saving, retry the download.

## Configuration

The app stores local settings and history in your user folder:

- `%USERPROFILE%\.ytflow2_config.json`
- `%USERPROFILE%\.ytflow2_history.json`

These files are personal machine state and should not be committed.

## Troubleshooting

- Update yt-dlp if a site stops working: `python -m pip install -U yt-dlp`
- Confirm FFmpeg is installed: `ffmpeg -version`
- Try a lower quality or different output format
- Use cookies for login-required or private media
- Confirm the URL is accessible in your browser
