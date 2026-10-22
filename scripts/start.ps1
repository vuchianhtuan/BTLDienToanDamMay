$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    if (-not (Test-Path -LiteralPath '.env')) { Copy-Item -LiteralPath '.env.example' -Destination '.env' }
    docker info --format '{{.ServerVersion}}'
    if ($LASTEXITCODE -ne 0) { throw 'Start Docker Desktop and wait for the engine.' }
    docker compose up --build -d --wait --wait-timeout 180
    if ($LASTEXITCODE -ne 0) { throw 'Startup failed. Inspect: docker compose logs --tail 100' }
    Write-Host 'Application ready. Default address: http://localhost:8000 (APP_PORT can override it).'
} finally { Pop-Location }
