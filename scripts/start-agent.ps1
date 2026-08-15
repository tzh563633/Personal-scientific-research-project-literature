param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$Token = $env:AGENT_TOKEN,
  [string]$Name = $env:COMPUTERNAME
)

if ([string]::IsNullOrWhiteSpace($Token)) {
  $envPath = Join-Path $PSScriptRoot "..\.env"
  if (Test-Path $envPath) {
    $line = Get-Content $envPath | Where-Object { $_ -like "AGENT_TOKEN=*" } | Select-Object -First 1
    if ($line) {
      $Token = $line.Split("=", 2)[1]
    }
  }
}
if ([string]::IsNullOrWhiteSpace($Token)) {
  throw "Pass -Token, set AGENT_TOKEN, or configure AGENT_TOKEN in .env."
}

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
  throw "Python was not found. Install Python 3.11 or newer."
}

Push-Location (Join-Path $PSScriptRoot "..")
try {
  & python -c "import httpx" *> $null
  if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing host Agent dependencies..."
    & python -m pip install -r agent\requirements.txt
    if ($LASTEXITCODE -ne 0) {
      throw "Could not install host Agent dependencies."
    }
  }
  & python -m agent.agent --base-url $BaseUrl --token $Token --name $Name
} finally {
  Pop-Location
}
