$ErrorActionPreference = 'Stop'
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    $frontendTests = @(Get-ChildItem -LiteralPath tests/frontend -Filter '*.test.cjs' -File | ForEach-Object { $_.FullName })
    node --test @frontendTests
    if ($LASTEXITCODE -ne 0) { throw 'Frontend tests failed. Use Node.js 20+.' }
    docker compose exec -T app python -m pytest tests -q -p no:cacheprovider
    if ($LASTEXITCODE -ne 0) { throw 'Automated tests failed.' }
    docker compose exec -T app python deploy/elasticity/kit.py lint
    if ($LASTEXITCODE -ne 0) { throw 'Offline Heat checks failed.' }
    docker compose exec -T app python tests/smoke_live.py
    if ($LASTEXITCODE -ne 0) { throw 'Live smoke test failed.' }
    docker compose exec -T app python tests/loadtest/smoke_workload.py
    if ($LASTEXITCODE -ne 0) { throw 'Selected fixture and streaming workload checks failed.' }
    docker compose exec -T app python tests/smoke_locust.py
    if ($LASTEXITCODE -ne 0) { throw 'Locust integration checks failed.' }
} finally { Pop-Location }
