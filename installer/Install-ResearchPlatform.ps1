param(
  [string]$InstallRoot = (Join-Path $env:LOCALAPPDATA "ResearchControlPlatform"),
  [switch]$TestOnly
)

$ErrorActionPreference = "Stop"
$sourceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$platformName = -join ([char[]](0x79D1, 0x7814, 0x63A7, 0x5236, 0x5E73, 0x53F0))
$logRoot = Join-Path $env:LOCALAPPDATA "ResearchControlPlatformLogs"
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$logPath = Join-Path $logRoot "installer.log"

function Write-InstallLog([string]$Message) {
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
  Add-Content -LiteralPath $logPath -Value $line -Encoding utf8
}

function Get-DockerCliPath {
  $docker = Get-Command docker -ErrorAction SilentlyContinue
  if ($docker) {
    return $docker.Source
  }
  if (-not $docker) {
    $candidate = Join-Path ${env:ProgramFiles} "Docker\Docker\resources\bin\docker.exe"
    if (Test-Path -LiteralPath $candidate) {
      return $candidate
    }
  }
  return $null
}

function Test-DockerReady {
  $dockerCli = Get-DockerCliPath
  if (-not $dockerCli) {
    return $false
  }
  & $dockerCli info *> $null
  return $LASTEXITCODE -eq 0
}

function Install-DockerDesktopBestEffort {
  if (Get-Command docker -ErrorAction SilentlyContinue) {
    $desktop = Join-Path ${env:ProgramFiles} "Docker\Docker\Docker Desktop.exe"
    if (Test-Path -LiteralPath $desktop) {
      Start-Process -FilePath $desktop | Out-Null
    }
    return
  }
  if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    throw "Docker CLI was not found and winget is unavailable. Install Docker Desktop manually, then run this installer again."
  }
  Write-InstallLog "Attempting Docker Desktop install through winget."
  & winget install --id Docker.DockerDesktop --source winget --accept-package-agreements --accept-source-agreements
  if ($LASTEXITCODE -ne 0) {
    throw "Docker Desktop installation through winget failed. Install Docker Desktop manually, then run this installer again."
  }
  $dockerBin = Join-Path ${env:ProgramFiles} "Docker\Docker\resources\bin"
  if (Test-Path -LiteralPath $dockerBin -and $env:Path -notlike "*$dockerBin*") {
    $env:Path = "$dockerBin;$env:Path"
  }
  $desktop = Join-Path ${env:ProgramFiles} "Docker\Docker\Docker Desktop.exe"
  if (Test-Path -LiteralPath $desktop) {
    Start-Process -FilePath $desktop | Out-Null
  }
}

function Wait-DockerReady([int]$TimeoutSeconds = 300) {
  $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
  while ((Get-Date) -lt $deadline) {
    if (Test-DockerReady) {
      return $true
    }
    Start-Sleep -Seconds 5
  }
  return $false
}

function Copy-ProjectFiles([string]$Destination) {
  $sourceFull = (Resolve-Path $sourceRoot).Path.TrimEnd("\")
  $destinationFull = [System.IO.Path]::GetFullPath($Destination).TrimEnd("\")
  if ($sourceFull -eq $destinationFull) {
    throw "Install folder must be different from the source folder."
  }
  New-Item -ItemType Directory -Force -Path $Destination | Out-Null
  $excludeDirs = @(
    ".git",
    ".venv",
    "node_modules",
    "dist",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "storage"
  )
  $excludeFiles = @(".env", "*.log", "*.db")
  $robocopyArgs = @($sourceRoot, $Destination, "/E", "/R:2", "/W:2", "/NFL", "/NDL", "/NP")
  foreach ($dir in $excludeDirs) {
    $robocopyArgs += @("/XD", (Join-Path $sourceRoot $dir))
  }
  foreach ($file in $excludeFiles) {
    $robocopyArgs += @("/XF", $file)
  }
  & robocopy @robocopyArgs | Out-Null
  if ($LASTEXITCODE -gt 7) {
    throw "Project file copy failed with robocopy exit code $LASTEXITCODE."
  }
}

function Start-InstalledPlatform([string]$Destination) {
  Push-Location $Destination
  try {
    & .\scripts\create-desktop-shortcut.ps1
    if ($LASTEXITCODE -ne 0) {
      throw "Desktop shortcut creation failed."
    }
    & .\scripts\start-platform.ps1
    if ($LASTEXITCODE -ne 0) {
      throw "Platform startup failed."
    }
    $agentOut = Join-Path $logRoot "agent.out.log"
    $agentErr = Join-Path $logRoot "agent.err.log"
    Start-Process `
      -FilePath "powershell.exe" `
      -ArgumentList @(
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        (Join-Path $Destination "scripts\start-agent.ps1")
      ) `
      -WorkingDirectory $Destination `
      -WindowStyle Hidden `
      -RedirectStandardOutput $agentOut `
      -RedirectStandardError $agentErr | Out-Null
  } finally {
    Pop-Location
  }
}

function Invoke-Install {
  Write-InstallLog "Install requested. Source=$sourceRoot Destination=$InstallRoot"
  Install-DockerDesktopBestEffort
  if (-not (Wait-DockerReady)) {
    throw "Docker Desktop is not ready. A restart or administrator action may be required. Start Docker Desktop and click Install and Run again."
  }
  Copy-ProjectFiles $InstallRoot
  Start-InstalledPlatform $InstallRoot
  Write-InstallLog "Install and run completed."
}

function Test-InstallationSource {
  $required = @(
    "docker-compose.yml",
    ".env.example",
    "backend\Dockerfile",
    "frontend\Dockerfile",
    "scripts\deploy-local.ps1",
    "scripts\start-platform.ps1",
    "scripts\start-agent.ps1",
    "scripts\create-desktop-shortcut.ps1"
  )
  $missing = @($required | Where-Object { -not (Test-Path -LiteralPath (Join-Path $sourceRoot $_)) })
  if ($missing.Count) {
    throw "Installer source is incomplete: $($missing -join ', ')"
  }
  if ([string]::IsNullOrWhiteSpace($InstallRoot)) {
    throw "InstallRoot must not be empty."
  }
  Write-Output "Installer source check passed."
}

if ($TestOnly) {
  Test-InstallationSource
  exit 0
}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$form = New-Object System.Windows.Forms.Form
$form.Text = "$platformName Installer"
$form.StartPosition = "CenterScreen"
$form.Size = New-Object System.Drawing.Size(640, 420)
$form.MaximizeBox = $false

$title = New-Object System.Windows.Forms.Label
$title.Text = "$platformName Windows Installer"
$title.Font = New-Object System.Drawing.Font("Microsoft YaHei UI", 14, [System.Drawing.FontStyle]::Bold)
$title.AutoSize = $true
$title.Location = New-Object System.Drawing.Point(24, 22)
$form.Controls.Add($title)

$info = New-Object System.Windows.Forms.TextBox
$info.Multiline = $true
$info.ReadOnly = $true
$info.ScrollBars = "Vertical"
$info.Location = New-Object System.Drawing.Point(24, 62)
$info.Size = New-Object System.Drawing.Size(580, 210)
$info.Text = @"
Source:
$sourceRoot

Install folder:
$InstallRoot

The installer copies project files, creates local secrets, creates a Desktop shortcut, starts Docker Compose, waits for health checks, and opens the control platform.

It does not copy .git, .env, storage data, logs, node_modules, or build caches.
"@
$form.Controls.Add($info)

$status = New-Object System.Windows.Forms.Label
$status.Text = "Ready"
$status.AutoSize = $false
$status.Location = New-Object System.Drawing.Point(24, 286)
$status.Size = New-Object System.Drawing.Size(580, 36)
$form.Controls.Add($status)

$button = New-Object System.Windows.Forms.Button
$button.Text = "Install and Run"
$button.Location = New-Object System.Drawing.Point(24, 330)
$button.Size = New-Object System.Drawing.Size(150, 32)
$form.Controls.Add($button)

$close = New-Object System.Windows.Forms.Button
$close.Text = "Close"
$close.Location = New-Object System.Drawing.Point(188, 330)
$close.Size = New-Object System.Drawing.Size(92, 32)
$close.Add_Click({ $form.Close() })
$form.Controls.Add($close)

$button.Add_Click({
  $button.Enabled = $false
  $status.Text = "Installing and starting platform..."
  $form.Refresh()
  try {
    Invoke-Install
    $status.Text = "Installed and running. The platform has been opened in your browser."
    [System.Windows.Forms.MessageBox]::Show(
      "Installation completed and the platform is running.",
      $platformName,
      [System.Windows.Forms.MessageBoxButtons]::OK,
      [System.Windows.Forms.MessageBoxIcon]::Information
    ) | Out-Null
  } catch {
    $status.Text = "Installation failed. See log: $logPath"
    Write-InstallLog "ERROR: $($_.Exception.Message)"
    [System.Windows.Forms.MessageBox]::Show(
      "$($_.Exception.Message)`n`nLog: $logPath",
      $platformName,
      [System.Windows.Forms.MessageBoxButtons]::OK,
      [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
  } finally {
    $button.Enabled = $true
  }
})

[void]$form.ShowDialog()
