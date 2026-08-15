$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "Docker CLI was not found."
}

& docker compose ps
Write-Host ""
try {
  $health = Invoke-RestMethod -Uri "http://localhost/health" -TimeoutSec 5
  Write-Host ("Backend health: " + $health.status)
} catch {
  Write-Host "Backend health: unavailable"
}

$lanIp = Get-NetIPConfiguration -ErrorAction SilentlyContinue |
  Where-Object { $_.IPv4DefaultGateway -and $_.IPv4Address } |
  ForEach-Object { $_.IPv4Address | Select-Object -ExpandProperty IPAddress -First 1 } |
  Where-Object {
    $_ -notlike "127.*" -and
    $_ -notlike "169.254.*" -and
    $_ -notlike "172.*"
  } |
  Select-Object -First 1
if ($lanIp) {
  Write-Host "LAN address: http://${lanIp}"
}
