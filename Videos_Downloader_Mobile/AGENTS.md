# MediaFlow Android — AGENTS.md

## Project overview

Single-module Android Studio project at `Videos_Downloader_App/` that wraps an Android-adapted `yt-dlp` Python backend (via Chaquopy) in a native Java UI.

- **Root project name** (settings.gradle): `VideoDownloaderAndroid`
- **App package / namespace**: `com.mediaflow.android`
- **Java entrypoint**: `app/src/main/java/com/mediaflow/android/MainActivity.java`
- **Python backend**: `app/src/main/python/mediaflow_core.py`
- **Android SDK**: compileSdk/targetSdk 35, minSdk 24
- **AGP**: 8.7.3 **| Chaquopy**: 17.0.0 **| Python**: 3.14 (Chaquopy)
- **Java 17** source/target compatibility
- **NDK**: `arm64-v8a`, `x86_64` only

## Build & run

```powershell
.\build_debug_apk.ps1
```

Requirements: Android SDK Platform 35, Android Studio JBR (sets `ANDROID_HOME` and `JAVA_HOME` automatically). Alternatively:

```powershell
.\gradlew.bat assembleDebug --no-daemon
```

APK output: `app/build/outputs/apk/debug/app-debug.apk`

`Build` → `Generate Signed Bundle / APK` for signed release.

## Machine-specific config

- `app/build.gradle` hardcodes a local Python path in `buildPython "C:/Users/coldw/.../python.exe"` — must be updated per machine
- Python 3.14 on Windows must match the configured path
- The shell used for build must have `ANDROID_HOME` and `JAVA_HOME` reachable (the `.ps1` script auto-sets them from Android Studio's SDK and JBR paths)

## Architecture notes

- **No tests, no CI, no lint/format config** — only manual APK install testing
- UI is built purely in Java code (no XML layouts except `AndroidManifest.xml` and resource files)
- Tab navigation: Download / History / Settings
- Downloaded files save to app-specific directory: `/Android/data/com.mediaflow.android/files/Download` (via `getExternalFilesDir`)
- FileProvider (`@xml/file_paths`) enables play/share of downloaded files
- Permissions: INTERNET, POST_NOTIFICATIONS, MANAGE_EXTERNAL_STORAGE (Android 11+), WRITE_EXTERNAL_STORAGE (legacy maxSdkVersion 29)

## Chaquopy / Python details

- `yt-dlp>=2024.12.0` installed via pip — uses plain `yt-dlp` (not `[default]`) to avoid pulling in `brotli` (not available for Chaquopy on this machine)
- Python backend communicates with Java via JSON serialization through Chaquopy's `PyObject` bridge
- Progress callbacks: Java `ProgressBridge.onProgress(String)` receives JSON progress payload from Python
- Cancellation: Java calls `cancel_current()`, Python checks `_cancel_requested` flag in download hook

## FFmpeg (optional)

Without FFmpeg, `yt-dlp` can still download direct/progressive streams and native audio. FFmpeg-only features (require `allow_ffmpeg` checkbox in Settings + a valid path):
- Merging separate video/audio streams
- Audio conversion (mp3/wav/flac/ogg etc.)
- Embedding subtitles / thumbnails
- SponsorBlock chapter modification

Format/quality selection adapts based on whether FFmpeg is enabled.

## Style conventions

- Java: no XML layouts — all UI built programmatically in `MainActivity.java`
- Python backend: single file `mediaflow_core.py` with functional style (no classes except `_json_error` helpers)
- No code generation, migrations, or build artifacts beyond normal Gradle/Chaquopy
- Strings: `tr()` method with switch-based Arabic translation; default is English
- Theme: dark/light/oled stored in SharedPreferences (`mediaflow_prefs`)

## Important paths

| What | Path |
|---|---|
| Android manifest | `app/src/main/AndroidManifest.xml` |
| Java activity | `app/src/main/java/com/mediaflow/android/MainActivity.java` |
| Python backend | `app/src/main/python/mediaflow_core.py` |
| App resources | `app/src/main/res/` |
| Build script | `build_debug_apk.ps1` |
| Gradle wrapper | `gradlew.bat` |
