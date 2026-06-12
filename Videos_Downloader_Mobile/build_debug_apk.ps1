param(
    [switch]$Clean
)

$ErrorActionPreference = "Stop"

$sdk = Join-Path $env:LOCALAPPDATA "Android\Sdk"
$studioJbr = "C:\Program Files\Android\Android Studio\jbr"

if (-not (Test-Path $sdk)) {
    throw "Android SDK was not found at $sdk. Install it with Android Studio first."
}

if (-not (Test-Path $studioJbr)) {
    throw "Android Studio JBR was not found at $studioJbr."
}

$env:ANDROID_HOME = $sdk
$env:ANDROID_SDK_ROOT = $sdk
$env:JAVA_HOME = $studioJbr

if ($Clean) {
    .\gradlew.bat clean --no-daemon
}

.\gradlew.bat assembleDebug --no-daemon
