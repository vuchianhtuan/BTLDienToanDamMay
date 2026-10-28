$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    docker compose exec -T app python -m pytest tests -q -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) { throw 'Automated tests failed.' }
    docker compose exec -T app python deploy/elasticity/kit.py lint
    if ($LASTEXITCODE -ne 0) { throw 'Offline Heat checks failed.' }
    docker compose exec -T app python tests/smoke_live.py
    if ($LASTEXITCODE -ne 0) { throw 'Live smoke test failed.' }
} finally { Pop-Location }
