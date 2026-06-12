# MediaFlow Android

**MediaFlow Android** is a native Android port of the desktop MediaFlow downloader. It uses Chaquopy to embed a Python 3.14 runtime (with yt-dlp) inside a Java UI built entirely in code — no XML layouts.

[![Android SDK](https://img.shields.io/badge/Android-API%2035-brightgreen)](https://developer.android.com/studio)
[![Python](https://img.shields.io/badge/Python-3.14-blue)](https://python.org)
[![Chaquopy](https://img.shields.io/badge/Chaquopy-17.0.0-orange)](https://chaquo.com/chaquopy)
[![License](https://img.shields.io/badge/license-MIT-green)]()

> ⚠️ This is not a direct `.py` to `.apk` conversion. Android apps require a native Android UI, storage paths, and safe background behavior.

## Features

- **Video downloads** with quality selection (Best Available → Worst)
- **Audio extraction** to mp3, m4a, aac, opus, flac, wav, ogg
- **Playlist support** with ordered filenames
- **Subtitles & thumbnails** (when FFmpeg is available)
- **SponsorBlock** chapter processing (when FFmpeg is available)
- **Download history** with search and re-download
- **Dark / Light / OLED** themes
- **English + Arabic** UI (switch-based translation)
- **File sharing** via Android FileProvider

## Project Structure

```
MediaFlowAndroid/
├── app/
│   ├── build.gradle                  # App-level Gradle (Chaquopy + Android config)
│   └── src/main/
│       ├── AndroidManifest.xml       # Permissions, activity, FileProvider
│       ├── java/com/mediaflow/android/
│       │   └── MainActivity.java     # Entire Java UI (1471 lines, no XML layouts)
│       ├── python/
│       │   └── mediaflow_core.py     # Python backend (yt-dlp wrapper, 295 lines)
│       └── res/
│           ├── drawable/             # mediaflow.png
│           ├── mipmap-hdpi/          # App icon variants
│           ├── values/               # colors.xml, strings.xml, styles.xml
│           └── xml/
│               └── file_paths.xml    # FileProvider paths for sharing
├── build.gradle                      # Root Gradle (AGP 8.7.3 + Chaquopy 17.0.0)
├── settings.gradle                   # Project name: VideoDownloaderAndroid
├── gradle.properties                 # JVM args, AndroidX, non-transitive R class
├── gradlew / gradlew.bat             # Gradle wrapper
├── build_debug_apk.ps1               # PowerShell build helper
└── README.md
```

## Requirements

| Tool | Version |
|---|---|
| Android Studio | Latest (with SDK Platform 35) |
| Android SDK | Platform 35, Build Tools |
| Android Gradle Plugin | 8.7.3 (declared in `build.gradle`) |
| Python | 3.14 (must match Chaquopy config) |
| Java | 17 (Android Studio JBR) |
| NDK | arm64-v8a, x86_64 ABIs |

## Build the APK

### Using the PowerShell script

```powershell
.\build_debug_apk.ps1
```

The script automatically detects Android Studio's SDK and JBR paths. Pass `-Clean` to do a clean build:

```powershell
.\build_debug_apk.ps1 -Clean
```

### Using Gradle directly

```powershell
.\gradlew.bat assembleDebug --no-daemon
```

### From Android Studio

1. Open the `Videos_Downloader_Mobile` folder in Android Studio
2. Let it sync — it will download SDK Platform 35, AGP 8.7.3, and Chaquopy 17.0.0
3. Click **Build → Build Bundle(s) / APK(s) → Build APK(s)**

### Output

```
app/build/outputs/apk/debug/app-debug.apk
```

### Release / Signed APK

Android Studio → **Build → Generate Signed Bundle / APK** → select APK → create/select a keystore → build release.

## Machine-Specific Configuration

The `app/build.gradle` hardcodes a local Python path:

```groovy
buildPython "C:/Users/<user>/AppData/Local/Programs/Python/Python314/python.exe"
```

Update this path to match your machine's Python 3.14 installation.

## Important Android Differences

### Storage

Downloads are saved to the app-specific directory:

```
/Android/data/com.mediaflow.android/files/Download
```

Files here are accessible to the app but are removed on uninstall. A future version can add MediaStore support for the public Downloads folder.

### Permissions

| Permission | Purpose |
|---|---|
| `INTERNET` | Network access for downloads |
| `POST_NOTIFICATIONS` | Android 13+ notification permission |
| `MANAGE_EXTERNAL_STORAGE` | Android 11+ full file access (requested at runtime) |
| `WRITE_EXTERNAL_STORAGE` | Legacy (maxSdkVersion 29) |

### FFmpeg

Android does not ship FFmpeg. Without it, yt-dlp can still download direct/progressive video streams and native audio. FFmpeg-only features (require the checkbox in Settings + a valid path):

- Merging separate video/audio streams
- Audio conversion (mp3/wav/flac/ogg etc.)
- Embedding subtitles / thumbnails
- SponsorBlock chapter modification

## Python / Chaquopy Details

- **Python version**: 3.14 (via Chaquopy)
- **yt-dlp**: `yt-dlp>=2024.12.0` (plain `yt-dlp`, not `[default]` — avoids `brotli` which is unavailable for Chaquopy on this machine)
- **Communication**: JSON serialization through Chaquopy's `PyObject` bridge
- **Progress**: Java `ProgressBridge.onProgress(String)` receives JSON payloads from Python
- **Cancellation**: Java calls `cancel_current()`, Python checks `_cancel_requested` flag
- **Backend**: Single file `mediaflow_core.py` with functional style

## Architecture Notes

- **No XML layouts**: All UI is built programmatically in `MainActivity.java` (1471 lines)
- **Tab navigation**: Download / History / Settings
- **Theme**: Dark/Light/OLED stored in `SharedPreferences` (`mediaflow_prefs`)
- **Translation**: `tr()` method with switch-based Arabic translations; default is English
- **No tests or CI**: Manual APK install testing only
