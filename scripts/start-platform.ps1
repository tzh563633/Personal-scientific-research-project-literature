param(
  [switch]$SkipBuild,
  [switch]$SkipAgent
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $root
$logPath = Join-Path $root "storage\logs\platform-launcher.log"
$platformName = -join ([char[]](0x79D1, 0x7814, 0x63A7, 0x5236, 0x5E73, 0x53F0))

try {
  $deployScript = Join-Path $PSScriptRoot "deploy-local.ps1"
  $deployParams = @{}
  if ($SkipBuild) { $deployParams["SkipBuild"] = $true }
  if ($SkipAgent) { $deployParams["SkipAgent"] = $true }

  & $deployScript @deployParams
  if ($LASTEXITCODE -ne 0) {
    throw "Local deployment failed. See $logPath"
  }

  $frontendPort = 80
  if (Test-Path -LiteralPath ".env") {
    $portLine = Get-Content -LiteralPath ".env" |
      Where-Object { $_ -match "^FRONTEND_PORT=" } |
      Select-Object -First 1
    if ($portLine) {
      $parsedPort = 0
      if ([int]::TryParse($portLine.Substring("FRONTEND_PORT=".Length), [ref]$parsedPort) -and $parsedPort -gt 0) {
        $frontendPort = $parsedPort
      }
    }
  }

  Start-Process "http://localhost:$frontendPort"
} catch {
  $message = "$platformName startup failed.`n$($_.Exception.Message)`nLog: $logPath"
  Add-Content -LiteralPath $logPath -Value $message -Encoding utf8
  Add-Type -AssemblyName PresentationFramework
  [System.Windows.MessageBox]::Show(
    $message,
    $platformName,
    [System.Windows.MessageBoxButton]::OK,
    [System.Windows.MessageBoxImage]::Error
  ) | Out-Null
  exit 1
}
