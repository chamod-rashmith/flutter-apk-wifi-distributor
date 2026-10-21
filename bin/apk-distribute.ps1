# PowerShell launcher for Flutter APK Wi-Fi Distributor
param (
    [switch]$Build,
    [switch]$NoSplit,
    [switch]$CleanRam = $true,
    [int]$Port = 8080,
    [string]$Type = "arm64"
)

$rootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pythonPath = "python"

$cmdArgs = @("-m", "flutter_apk_wifi_distributor.cli", "--port", $Port, "--type", $Type)
if ($Build) { $cmdArgs += "--build" }
if ($NoSplit) { $cmdArgs += "--no-split" }
if ($CleanRam) { $cmdArgs += "--clean-ram" }

$env:PYTHONPATH = "$rootDir;$env:PYTHONPATH"
& $pythonPath @cmdArgs
