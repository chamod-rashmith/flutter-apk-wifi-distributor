# PowerShell convenience wrapper for Flutter APK Wi-Fi Distributor
param (
    [string]$Build,
    [switch]$Split,
    [switch]$Universal,
    [switch]$Debug,
    [switch]$Server,
    [switch]$CleanRam,
    [int]$Port = 8080
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$pythonScript = Join-Path $scriptDir "distribute_apk.py"

$argsList = @($pythonScript, "--port", $Port)
if ($Build) { $argsList += @("--build", $Build) }
if ($Split) { $argsList += "--split" }
if ($Universal) { $argsList += "--universal" }
if ($Debug) { $argsList += "--debug" }
if ($Server) { $argsList += "--server" }
if ($CleanRam) { $argsList += "--clean-ram" }

python @argsList
