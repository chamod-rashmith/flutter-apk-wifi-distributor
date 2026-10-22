# Universal one-click installer for flutter-apk-wifi-distributor on Windows
Write-Host "`n[+] Installing flutter-apk-wifi-distributor CLI and Antigravity Plugin..." -ForegroundColor Cyan

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# 1. Install CLI tool via pip
Write-Host "[*] Installing Python CLI package (editable mode)..." -ForegroundColor Yellow
pip install -e $projectRoot

if ($LASTEXITCODE -ne 0) {
    Write-Host "[!] Failed to install Python package via pip. Please ensure Python and pip are available in your PATH." -ForegroundColor Red
    exit 1
}

# 2. Deploy Antigravity Plugin to user's .gemini config
$geminiPluginDir = Join-Path $HOME ".gemini\config\plugins\flutter-apk-wifi-distributor"
Write-Host "[*] Installing Antigravity AI Plugin to: $geminiPluginDir" -ForegroundColor Yellow

if (!(Test-Path $geminiPluginDir)) {
    New-Item -ItemType Directory -Force -Path $geminiPluginDir | Out-Null
}

$sourcePluginDir = Join-Path $projectRoot "plugin"
Copy-Item -Path "$sourcePluginDir\*" -Destination $geminiPluginDir -Recurse -Force

Write-Host "`n[OK] Installation Complete!" -ForegroundColor Green
Write-Host "   - CLI Command: apk-distribute is now available system-wide." -ForegroundColor Cyan
Write-Host "   - AI Plugin  : Successfully registered for Antigravity AI agents." -ForegroundColor Cyan
Write-Host "   - Try asking : Start Wi-Fi distribution server to choose and build Flutter APK`n" -ForegroundColor Gray
