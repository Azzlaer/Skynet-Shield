# Local alpha prerequisites; no downloads or system modifications.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not [Environment]::Is64BitOperatingSystem) { throw 'AdminCP requiere Windows x64.' }
$python = Get-Command python -ErrorAction Stop
& $python.Source -c "import sys,sqlite3; sys.exit(0 if sys.version_info >= (3,10) else 1)"
if ($LASTEXITCODE -ne 0) { throw 'Se requiere Python 3.10 o superior con SQLite.' }
$dotnet = Get-Command dotnet -ErrorAction Stop
$runtimes = & $dotnet.Source --list-runtimes
if ($LASTEXITCODE -ne 0 -or -not ($runtimes -match '^Microsoft.WindowsDesktop.App 8\.')) { throw 'Se requiere .NET Desktop Runtime 8 x64.' }
foreach ($file in @('Native/x86/SkynetShield.dll','Native/x86/ShieldBridge.dll','Native/x64/SkynetShield.dll','Native/x64/ShieldBridge.dll','AdminCP/SkynetShield.Admin.exe','Server/run.py')) {
    if (-not (Test-Path -LiteralPath (Join-Path $root $file) -PathType Leaf)) { throw "Falta archivo: $file" }
}
Write-Host 'Comprobaciones básicas correctas. Verificar también VC++ Redistributable x86/x64 y arquitectura del proceso.'
