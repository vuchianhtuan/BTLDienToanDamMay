# Keep this terminal open. Ctrl+C closes only this SSH tunnel.
[CmdletBinding()]
param(
    [string]$ConfigPath = (Join-Path $PSScriptRoot '../deploy/tv2/lab-access.json'),
    [string]$Ec2Host,
    [string]$KeyPath,
    [ValidateRange(1024,65535)][int]$LocalPort,
    [switch]$DryRun
)
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    throw 'Copy deploy/tv2/lab-access.example.json to lab-access.json and fill in your connection settings first.'
}
$configFile = (Resolve-Path -LiteralPath $ConfigPath).Path
$config = Get-Content -Raw -LiteralPath $configFile | ConvertFrom-Json
if (-not $PSBoundParameters.ContainsKey('Ec2Host')) { $Ec2Host = [string]$config.ec2_host }
if (-not $PSBoundParameters.ContainsKey('KeyPath')) { $KeyPath = [string]$config.ssh_key_path }
if (-not $PSBoundParameters.ContainsKey('LocalPort')) { $LocalPort = [int]$config.local_port }
$sshUser = [string]$config.ssh_user
$appHost = [string]$config.app_host
$appPort = [int]$config.app_port
foreach ($address in @($Ec2Host, $appHost)) {
    if ($address -notmatch '^[A-Za-z0-9][A-Za-z0-9.-]*$' -or $address -eq 'EC2_HOST_OR_DNS') {
        throw 'Set ec2_host and app_host to an IPv4 address or DNS name, without a URL scheme or port.'
    }
}
if ($sshUser -notmatch '^[A-Za-z_][A-Za-z0-9_-]*$') { throw 'Invalid ssh_user in lab configuration.' }
if ($appPort -lt 1 -or $appPort -gt 65535 -or $LocalPort -lt 1024 -or $LocalPort -gt 65535) {
    throw 'app_port must be 1..65535 and local_port must be 1024..65535.'
}
function Resolve-LabPath([string]$Value) {
    if ([string]::IsNullOrWhiteSpace($Value)) { throw 'ssh_key_path must point to your own SSH private key.' }
    if ($Value.StartsWith('~/') -or $Value.StartsWith('~\')) {
        $Value = Join-Path ([Environment]::GetFolderPath('UserProfile')) $Value.Substring(2)
    } elseif (-not [IO.Path]::IsPathRooted($Value)) {
        $Value = Join-Path (Split-Path $configFile -Parent) $Value
    }
    if (-not (Test-Path -LiteralPath $Value -PathType Leaf)) { throw "File not found: $Value" }
    return (Resolve-Path -LiteralPath $Value).Path
}
$resolvedKey = Resolve-LabPath $KeyPath
$sshCommand = Get-Command ssh -CommandType Application -ErrorAction Stop | Select-Object -First 1
$forward = '127.0.0.1:{0}:{1}:{2}' -f $LocalPort, $appHost, $appPort
$sshArguments = @(
    '-N', '-T', '-i', $resolvedKey,
    '-o', 'IdentitiesOnly=yes',
    '-o', 'StrictHostKeyChecking=ask',
    '-o', 'ConnectTimeout=10',
    '-o', 'ExitOnForwardFailure=yes',
    '-o', 'ServerAliveInterval=30',
    '-o', 'ServerAliveCountMax=3'
)
if (-not [string]::IsNullOrWhiteSpace([string]$config.known_hosts_path)) {
    $knownHosts = Resolve-LabPath ([string]$config.known_hosts_path)
    # OpenSSH parses this option itself; quote paths containing spaces.
    $sshArguments += @('-o', ('UserKnownHostsFile="{0}"' -f $knownHosts.Replace('\','/')))
}
$sshArguments += @('-L', $forward, "$sshUser@$Ec2Host")
if ($DryRun) {
    [pscustomobject]@{ Executable = $sshCommand.Source; Arguments = $sshArguments; Url = "http://127.0.0.1:$LocalPort" }
    return
}
$portProbe = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $LocalPort)
$portProbe.Server.ExclusiveAddressUse = $true
try {
    $portProbe.Start()
} catch {
    throw "Local port $LocalPort is busy or unavailable. Use -LocalPort 18001 or close your existing tunnel."
} finally {
    $portProbe.Stop()
}
Write-Host "Connecting to $Ec2Host. Keep this terminal open; Ctrl+C disconnects."
Write-Host "After SSH connects, open http://127.0.0.1:$LocalPort and enter the API key supplied separately."
Write-Host "From a second terminal: ./scripts/check-lab.ps1 -BaseUrl http://127.0.0.1:$LocalPort -CheckApi"
& $sshCommand.Source @sshArguments
if ($LASTEXITCODE -ne 0) {
    throw 'SSH tunnel exited with an error. Check endpoint, SSH permission/key, host fingerprint, EC2 security group and whether the lab VMs are running.'
}
