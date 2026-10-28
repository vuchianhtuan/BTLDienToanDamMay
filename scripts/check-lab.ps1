# Read-only checks. Does not upload files, stop services or change stored objects.
[CmdletBinding()]
param(
    [string]$BaseUrl = 'http://127.0.0.1:18000',
    [switch]$CheckApi
)
$ErrorActionPreference = 'Stop'
$parsedUrl = $null
if (-not [Uri]::TryCreate($BaseUrl, [UriKind]::Absolute, [ref]$parsedUrl) -or
    $parsedUrl.Scheme -ne 'http' -or $parsedUrl.Host -notin @('127.0.0.1','localhost','[::1]') -or
    $parsedUrl.UserInfo -or $parsedUrl.AbsolutePath -ne '/' -or $parsedUrl.Query -or $parsedUrl.Fragment) {
    throw 'BaseUrl must be a local SSH tunnel URL, for example http://127.0.0.1:18000.'
}
$BaseUrl = $BaseUrl.TrimEnd('/')
try {
    $ready = Invoke-RestMethod -Uri "$BaseUrl/health/ready" -TimeoutSec 15
    if ($ready.status -ne 'ready' -or $ready.storage -ne 'swift') { throw 'Expected a ready Swift-backed lab.' }
    foreach ($path in @('/', '/assets/app.js', '/assets/styles.css')) {
        $response = Invoke-WebRequest -UseBasicParsing -Uri ($BaseUrl + $path) -TimeoutSec 15
        if ($response.StatusCode -ne 200) { throw "Asset unavailable: $path" }
    }
    Write-Host 'PASS: readiness (Swift), frontend and static assets.'
    if ($CheckApi) {
        $secureKey = $null
        $apiKey = $env:APP_API_KEY
        if ([string]::IsNullOrWhiteSpace($apiKey)) {
            $secureKey = Read-Host 'Lab API key (hidden)' -AsSecureString
            $apiKey = ([pscredential]::new('lab', $secureKey)).GetNetworkCredential().Password
        }
        if ([string]::IsNullOrWhiteSpace($apiKey)) { throw 'An API key is required for -CheckApi.' }
        try {
            $headers = @{ 'X-API-Key' = $apiKey }
            $rows = Invoke-RestMethod -Uri "$BaseUrl/api/files?limit=1" -Headers $headers -TimeoutSec 20
            $rows = @($rows)
            if ($rows.Count -gt 0) {
                $fileId = [guid]::Parse([string]$rows[0].id).ToString()
                $verified = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/files/$fileId/verify" -Headers $headers -TimeoutSec 45
                if ($verified.intact -ne $true) { throw 'The existing file failed its integrity check.' }
                Write-Host 'PASS: authenticated API and SHA-256 verification of one existing file.'
            } else {
                Write-Host 'PASS: authenticated API. No existing file available to verify.'
            }
        } finally {
            $apiKey = $null
            $headers = $null
            if ($secureKey) { $secureKey.Dispose() }
        }
    }
} catch {
    throw "Lab check failed. Keep the tunnel open and check EC2/App/DB readiness and your API key. Details: $($_.Exception.Message)"
}
