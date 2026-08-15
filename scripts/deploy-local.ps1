param(
  [switch]$SkipBuild,
  [switch]$SkipAgent
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root

function New-RandomHex([int]$Bytes) {
  $buffer = New-Object byte[] $Bytes
  [System.Security.Cryptography.RandomNumberGenerator]::Fill($buffer)
  return ([System.BitConverter]::ToString($buffer) -replace "-", "").ToLowerInvariant()
}

function Set-EnvValue([string]$Path, [string]$Key, [string]$Value) {
  $lines = @(Get-Content -LiteralPath $Path)
  $pattern = "^" + [regex]::Escape($Key) + "="
  $found = $false
  $updated = foreach ($line in $lines) {
    if ($line -match $pattern) {
      $found = $true
      "$Key=$Value"
    } else {
      $line
    }
  }
  if (-not $found) {
    $updated += "$Key=$Value"
  }
  Set-Content -LiteralPath $Path -Value $updated -Encoding ascii
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
  throw "Docker CLI was not found. Install and start Docker Desktop, then run this script again."
}

$dockerReady = $false
$deadline = (Get-Date).AddMinutes(3)
while ((Get-Date) -lt $deadline) {
  & docker info *> $null
  if ($LASTEXITCODE -eq 0) {
    $dockerReady = $true
    break
  }
  Start-Sleep -Seconds 5
}
if (-not $dockerReady) {
  throw "Docker Desktop is not ready after 3 minutes."
}

if (-not (Test-Path -LiteralPath ".env")) {
  Copy-Item -LiteralPath ".env.example" -Destination ".env"
  Set-EnvValue ".env" "SECRET_KEY" (New-RandomHex 32)
  Set-EnvValue ".env" "AGENT_TOKEN" (New-RandomHex 32)
  Set-EnvValue ".env" "POSTGRES_PASSWORD" (New-RandomHex 24)
  Write-Host "Created .env with random local secrets."
}

$envLines = Get-Content -LiteralPath ".env"
foreach ($key in @("SECRET_KEY", "AGENT_TOKEN", "POSTGRES_PASSWORD")) {
  $line = $envLines | Where-Object { $_ -match ("^" + $key + "=") } | Select-Object -First 1
  $value = if ($line) { $line.Substring($key.Length + 1) } else { "" }
  if ([string]::IsNullOrWhiteSpace($value) -or $value -match "^(generate-|change-me|local-development)") {
    throw "$key is missing or still uses a placeholder. Edit .env before deployment."
  }
}

$composeArgs = @("compose", "up", "-d")
if (-not $SkipBuild) {
  $composeArgs += "--build"
}
Write-Host "Starting PostgreSQL, Redis, backend, worker, beat, frontend and Mailpit..."
& docker @composeArgs
if ($LASTEXITCODE -ne 0) {
  throw "Docker Compose failed to start the platform."
}

$frontendPort = 80
$portLine = $envLines | Where-Object { $_ -match "^FRONTEND_PORT=" } | Select-Object -First 1
if ($portLine) {
  $parsedPort = 0
  if ([int]::TryParse($portLine.Substring("FRONTEND_PORT=".Length), [ref]$parsedPort) -and $parsedPort -gt 0) {
    $frontendPort = $parsedPort
  }
}

$frontendUrl = "http://localhost:$frontendPort"
$healthUrl = "$frontendUrl/health"
$setupUrl = "$frontendUrl/api/v1/setup/status"
$ready = $false
$deadline = (Get-Date).AddMinutes(5)
while ((Get-Date) -lt $deadline) {
  try {
    $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5
    $setup = Invoke-RestMethod -Uri $setupUrl -TimeoutSec 5
    if ($health.status -eq "ok" -and $null -ne $setup.initialized) {
      $ready = $true
      break
    }
  } catch {
    Start-Sleep -Seconds 5
    continue
  }
  Start-Sleep -Seconds 5
}
if (-not $ready) {
  & docker compose ps
  throw "The platform did not become ready within 5 minutes."
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

Write-Host ""
Write-Host "Local deployment is ready."
Write-Host "Web:     $frontendUrl"
Write-Host "Mailpit: http://localhost:8025"
if ($lanIp) {
  Write-Host "LAN:     http://${lanIp}:$frontendPort"
}
Write-Host "Setup:   Open the Web address and create the first administrator."
if (-not $SkipAgent) {
  Write-Host "Agent:   .\scripts\start-agent.ps1"
} else {
  Write-Host "Agent:   skipped by -SkipAgent"
}
