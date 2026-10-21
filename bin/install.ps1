# One-click installer for flutter-apk-wifi-distributor
Write-Host "📦 Installing flutter-apk-wifi-distributor globally via pip..." -ForegroundColor Cyan

$projectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
pip install -e $projectRoot

if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ Successfully installed! You can now run 'apk-distribute' from any Flutter project." -ForegroundColor Green
} else {
    Write-Host "`n❌ Installation failed. Please ensure Python and pip are in your PATH." -ForegroundColor Red
}
