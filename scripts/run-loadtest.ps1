param(
    [ValidateSet('light', 'medium', 'higher')][string]$Profile = 'light',
    [ValidateRange(5, 600)][int]$DurationSeconds = 30,
    [string]$TargetUrl = 'http://127.0.0.1:8000'
)
$ErrorActionPreference = 'Stop'
$settings = @{ light = @(5, 1); medium = @(10, 2); higher = @(20, 2) }
$profileUsers = $settings[$Profile][0]
$spawnRate = $settings[$Profile][1]
$runId = $Profile + '-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$remoteFolder = '/tmp/tv3-loadtests/' + $runId
Push-Location (Split-Path $PSScriptRoot -Parent)
try {
    docker compose exec -T app python -c "from pathlib import Path; Path('$remoteFolder').mkdir(parents=True, exist_ok=True)"
    if ($LASTEXITCODE -ne 0) { throw 'App container is not available.' }
    docker compose exec -T -e ('LOCUST_SUMMARY_FILE=' + $remoteFolder + '/summary.json') app python -m locust -f loadtest/locustfile.py --headless -u $profileUsers -r $spawnRate -t ($DurationSeconds.ToString() + 's') --host $TargetUrl --only-summary --exit-code-on-error 1 --csv ($remoteFolder + '/result') --csv-full-history --html ($remoteFolder + '/report.html')
    $loadExitCode = $LASTEXITCODE
    $localFolder = Join-Path 'test-results/locust' $runId
    New-Item -ItemType Directory -Path $localFolder -Force | Out-Null
    docker compose cp ('app:' + $remoteFolder + '/.') $localFolder
    if ($LASTEXITCODE -ne 0) { throw 'Could not copy Locust reports.' }
    Write-Host ('Reports: ' + (Resolve-Path -LiteralPath $localFolder).Path)
    if ($loadExitCode -ne 0) { throw 'Locust reported failures. Inspect the saved reports.' }
} finally { Pop-Location }
