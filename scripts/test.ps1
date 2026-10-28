$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    docker compose exec -T app python -m pytest tests -q -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) { throw 'Automated tests failed.' }
    docker compose exec -T app python tests/smoke_live.py
    if ($LASTEXITCODE -ne 0) { throw 'Live smoke test failed.' }
    docker compose exec -T app python tests/smoke_locust.py
    if ($LASTEXITCODE -ne 0) { throw 'Locust integration checks failed.' }
} finally { Pop-Location }
