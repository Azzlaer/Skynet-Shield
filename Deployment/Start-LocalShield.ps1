# Only development: loopback HTTP. Never expose this service publicly.
param([string]$Python = 'python', [string]$Database = (Join-Path $env:LOCALAPPDATA 'SkynetShield\shield.sqlite3'))
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if ($env:SHIELD_ADMIN_KEY -cnotmatch '^[0-9a-f]{64}$') { throw 'Configurar SHIELD_ADMIN_KEY en el entorno privado.' }
if (-not $env:SHIELD_REGISTRY -and ($env:SHIELD_GAME_KEY -cnotmatch '^[0-9a-f]{64}$' -or $env:SHIELD_GAME_KEY -ceq $env:SHIELD_ADMIN_KEY)) { throw 'Configurar SHIELD_GAME_KEY independiente.' }
$previousDb = $env:SHIELD_DB
$env:SHIELD_DB = [IO.Path]::GetFullPath($Database)
try {
    [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($env:SHIELD_DB)) | Out-Null
    Push-Location $root
    try {
        & $Python -m Server.run
        if ($LASTEXITCODE -ne 0) { throw 'Shield Server terminó con error.' }
    } finally { Pop-Location }
} finally { $env:SHIELD_DB = $previousDb }
