# PowerShell launcher for Flutter APK Wi-Fi Distributor
param (
    [string]$Build,
    [switch]$Split,
    [switch]$Universal,
    [switch]$Debug,
    [switch]$Server,
    [switch]$CleanRam,
    [int]$Port = 8080
)

$rootDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$pythonPath = "python"

$cmdArgs = @("-m", "flutter_apk_wifi_distributor.cli", "--port", $Port)
if ($Build) { $cmdArgs += @("--build", $Build) }
if ($Split) { $cmdArgs += "--split" }
if ($Universal) { $cmdArgs += "--universal" }
if ($Debug) { $cmdArgs += "--debug" }
if ($Server) { $cmdArgs += "--server" }
if ($CleanRam) { $cmdArgs += "--clean-ram" }

$env:PYTHONPATH = "$rootDir;$env:PYTHONPATH"
& $pythonPath @cmdArgs
