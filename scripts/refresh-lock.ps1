$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path $PSScriptRoot -Parent
$lockWorkspace = Join-Path ([System.IO.Path]::GetTempPath()) ('integrity-lock-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $lockWorkspace | Out-Null
try {
    Copy-Item -LiteralPath (Join-Path $repoRoot 'requirements.txt') -Destination (Join-Path $lockWorkspace 'requirements.txt')
    # The container sees only this task's dependency files, not .env or credentials.
    docker run --rm --mount "type=bind,source=$lockWorkspace,target=/work" python:3.12-slim sh -c 'python -m pip install -r /work/requirements.txt >&2 && python -m pip freeze > /work/requirements.lock.txt'
    if ($LASTEXITCODE -ne 0) { throw 'Could not resolve Linux dependency lock.' }
    Copy-Item -LiteralPath (Join-Path $lockWorkspace 'requirements.lock.txt') -Destination (Join-Path $repoRoot 'requirements.lock.txt')
    Write-Host 'Lock updated. Review the diff, rebuild and run tests before committing.'
} finally {
    # Remove exactly the task-created files; no recursive deletion.
    foreach ($lockFile in @('requirements.txt', 'requirements.lock.txt')) {
        $lockFilePath = Join-Path $lockWorkspace $lockFile
        if (Test-Path -LiteralPath $lockFilePath) { Remove-Item -LiteralPath $lockFilePath }
    }
    Remove-Item -LiteralPath $lockWorkspace
}
