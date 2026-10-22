$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    # Preserve volumes and uploaded files.
    docker compose stop
    if ($LASTEXITCODE -ne 0) { throw 'Could not stop services.' }
} finally { Pop-Location }
