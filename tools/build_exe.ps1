param(
    [ValidateSet("OneFile", "OneDir")]
    [string]$Mode = "OneFile"
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

python .\tools\generate_icon.py

if (-not (Get-Command pyinstaller -ErrorAction SilentlyContinue)) {
    Write-Error "PyInstaller is not installed. Run: python -m pip install pyinstaller"
}

if ($Mode -eq "OneFile") {
    pyinstaller --noconfirm --clean MediaFlow.spec
} else {
    $IconPath = Join-Path $ProjectRoot "assets\mediaflow.ico"
    $Args = @(
        "--noconfirm",
        "--clean",
        "--windowed",
        "--name", "MediaFlow",
        "app.py"
    )
    if (Test-Path $IconPath) {
        $Args = @("--icon", $IconPath) + $Args
    }
    pyinstaller @Args
}

Write-Host ""
Write-Host "Build complete. Check the dist folder." -ForegroundColor Green
