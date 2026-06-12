import json
import os
import re
import time
from pathlib import Path

import yt_dlp


VIDEO_FORMATS = ["mp4", "mkv", "webm"]
AUDIO_FORMATS = ["mp3", "m4a", "aac", "opus", "flac", "wav", "ogg"]
VIDEO_QUALITIES = [
    "Best Available",
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

_cancel_requested = False


def get_options():
    return json.dumps(
        {
            "video_formats": VIDEO_FORMATS,
            "audio_formats": AUDIO_FORMATS,
            "video_qualities": VIDEO_QUALITIES,
            "audio_qualities": AUDIO_QUALITIES,
        }
    )


def cancel_current():
    global _cancel_requested
    _cancel_requested = True


def fmt_duration(secs):
    if not secs:
        return ""
    secs = int(secs)
    hours, rem = divmod(secs, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes}:{seconds:02d}"


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


def _json_error(exc):
    return json.dumps({"ok": False, "error": clean_error_text(exc)})


def _safe_output_dir(output_dir):
    path = Path(output_dir).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _base_opts(playlist=False):
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": not playlist,
        "restrictfilenames": True,
        "trim_file_name": 160,
        "retries": 5,
        "fragment_retries": 5,
    }


def _format_selector(ext, quality, is_audio, allow_ffmpeg):
    if is_audio:
        if not allow_ffmpeg:
            if quality == "Worst":
                return "worstaudio/worst"
            return f"bestaudio[ext={ext}]/bestaudio/best"
        return "bestaudio/best" if quality != "Worst" else "worstaudio/worst"

    if not allow_ffmpeg:
        if quality == "Worst":
            return f"worst[ext={ext}]/worst"
        return f"best[ext={ext}]/best"

    if quality == "Worst":
        return "worstvideo+worstaudio/worst"

    match = re.match(r"(\d+)p", quality)
    if match:
        height = int(match.group(1))
        return f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"

    return "bestvideo+bestaudio/best"


def _build_ydl_opts(output_dir, ext, quality, is_audio, progress_hook, options):
    playlist = bool(options.get("playlist"))
    out_dir = _safe_output_dir(output_dir)
    if playlist:
        outtmpl = os.path.join(
            out_dir,
            "%(playlist_title).80B",
            "%(playlist_index)03d - %(title).100B [%(id)s].%(ext)s",
        )
    else:
        outtmpl = os.path.join(out_dir, "%(title).120B [%(id)s].%(ext)s")

    allow_ffmpeg = bool(options.get("allow_ffmpeg"))
    postprocessors = []
    if is_audio and allow_ffmpeg:
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
    elif allow_ffmpeg:
        postprocessors.append({"key": "FFmpegVideoConvertor", "preferedformat": ext})

    if options.get("embed_thumb") and allow_ffmpeg:
        postprocessors.append({"key": "EmbedThumbnail"})
    if options.get("subs") and allow_ffmpeg:
        postprocessors.append({"key": "FFmpegEmbedSubtitle", "already_have_subtitle": False})
    if options.get("sponsor_block") and allow_ffmpeg:
        postprocessors.append({"key": "SponsorBlock"})
        postprocessors.append(
            {
                "key": "ModifyChapters",
                "remove_sponsor_segments": ["sponsor", "intro", "outro", "selfpromo"],
            }
        )

    opts = _base_opts(playlist=playlist)
    opts.update(
        {
            "format": _format_selector(ext, quality, is_audio, allow_ffmpeg),
            "outtmpl": outtmpl,
            "progress_hooks": [progress_hook],
            "postprocessors": postprocessors,
            "merge_output_format": ext if allow_ffmpeg and not is_audio else None,
            "writesubtitles": bool(options.get("subs") and allow_ffmpeg),
            "subtitleslangs": ["en"] if options.get("subs") and allow_ffmpeg else [],
            "writethumbnail": bool(options.get("embed_thumb") and allow_ffmpeg),
            "concurrent_fragment_downloads": int(options.get("concurrent", 1)),
        }
    )

    ffmpeg_path = str(options.get("ffmpeg_path", "")).strip()
    if ffmpeg_path:
        opts["ffmpeg_location"] = ffmpeg_path

    return opts


def fetch_info(url, playlist=False):
    try:
        opts = _base_opts(playlist=playlist)
        opts["skip_download"] = True
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
        if not info:
            raise yt_dlp.utils.DownloadError("No media information was returned for this URL.")
        if not playlist and not info.get("formats") and not info.get("url"):
            raise yt_dlp.utils.DownloadError("No downloadable video formats were found for this URL.")

        title = info.get("title", "Unknown")
        views = info.get("view_count")
        formats = len(info.get("formats", []))
        return json.dumps(
            {
                "ok": True,
                "title": title,
                "uploader": info.get("uploader") or "",
                "duration": fmt_duration(info.get("duration")),
                "views": f"{views:,}" if views else "",
                "formats": formats,
                "extractor": info.get("extractor_key") or info.get("extractor") or "",
                "webpage_url": info.get("webpage_url") or url,
                "thumbnail": info.get("thumbnail") or "",
            }
        )
    except Exception as exc:
        return _json_error(exc)


def download(url, output_dir, ext, quality, is_audio, options_json, progress_callback=None):
    global _cancel_requested
    _cancel_requested = False
    start = time.time()

    try:
        options = json.loads(options_json or "{}")
    except Exception:
        options = {}

    def emit(payload):
        if progress_callback is not None:
            progress_callback.onProgress(json.dumps(payload))

    def hook(data):
        if _cancel_requested:
            raise yt_dlp.utils.DownloadError("Cancelled by user")
        status = data.get("status")
        if status == "downloading":
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            done = data.get("downloaded_bytes", 0)
            speed = data.get("speed") or 0
            eta = data.get("eta") or 0
            pct = done / total if total else 0
            emit(
                {
                    "status": "downloading",
                    "percent": pct,
                    "message": f"Downloading {pct * 100:.1f}%  {fmt_size(done)} / {fmt_size(total)}",
                    "speed": f"{speed / 1024 / 1024:.1f} MB/s" if speed else "",
                    "eta": f"ETA {eta}s" if eta else "",
                }
            )
        elif status == "finished":
            emit({"status": "processing", "percent": 0.99, "message": "Processing / merging..."})

    try:
        opts = _build_ydl_opts(output_dir, ext, quality, bool(is_audio), hook, options)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url)
        downloaded_files = []
        if info:
            if 'requested_downloads' in info:
                for d in info['requested_downloads']:
                    filepath = d.get('filepath') or d.get('_filename')
                    if filepath:
                        downloaded_files.append(filepath)
            else:
                filepath = info.get('_filename')
                if filepath:
                    downloaded_files.append(filepath)

        elapsed = time.time() - start
        return json.dumps(
            {
                "ok": True,
                "title": (info.get("title") or url) if info else url,
                "url": url,
                "ext": ext,
                "type": "Audio" if is_audio else "Video",
                "elapsed": elapsed,
                "output_dir": output_dir,
                "downloaded_files": downloaded_files,
            }
        )
    except Exception as exc:
        if "Cancelled" in str(exc):
            return json.dumps({"ok": False, "cancelled": True, "error": "Cancelled"})
        return _json_error(exc)
