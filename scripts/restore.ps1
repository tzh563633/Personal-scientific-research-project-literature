param(
  [Parameter(Mandatory = $true)]
  [string]$BackupPath,
  [string]$StorageRoot = "$PSScriptRoot\..\storage",
  [string]$ComposeFile = "$PSScriptRoot\..\docker-compose.yml",
  [switch]$SkipDatabase
)

$backup = (Resolve-Path $BackupPath).Path
$storage = (Resolve-Path $StorageRoot).Path

if (Test-Path $backup -PathType Leaf) {
  throw "Pass a backup directory produced by the application, not a single archive file."
}

$storageArchive = Join-Path $backup "storage.zip"
$databaseDump = Join-Path $backup "database.dump"
if (-not (Test-Path $storageArchive)) {
  throw "Backup is missing storage.zip: $backup"
}

$temp = Join-Path ([System.IO.Path]::GetTempPath()) ("research-restore-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $temp | Out-Null
try {
  $expanded = Join-Path $temp "storage"
  Expand-Archive -LiteralPath $storageArchive -DestinationPath $expanded -Force
  Get-ChildItem -LiteralPath $expanded -Force | Copy-Item -Destination $storage -Recurse -Force
  Write-Output "Storage restored to: $storage"

  if (-not $SkipDatabase) {
    if (-not (Test-Path $databaseDump)) {
      throw "Backup is missing database.dump. Use -SkipDatabase for a storage-only restore."
    }
    $compose = (Resolve-Path $ComposeFile).Path
    docker compose -f $compose up -d postgres backend
    if ($LASTEXITCODE -ne 0) {
      throw "Could not start the PostgreSQL and backend services."
    }
    # Use the backend image's client so pg_dump and pg_restore stay compatible.
    docker compose -f $compose cp $databaseDump backend:/tmp/research-restore.dump
    if ($LASTEXITCODE -ne 0) {
      throw "Could not copy the database dump into the backend container."
    }
    docker compose -f $compose exec -T backend sh -c 'export PGPASSWORD="$POSTGRES_PASSWORD"; pg_restore16 -h postgres -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner /tmp/research-restore.dump'
    if ($LASTEXITCODE -ne 0) {
      throw "PostgreSQL restore failed."
    }
    docker compose -f $compose exec -T backend rm -f /tmp/research-restore.dump
    Write-Output "Database restored through Docker Compose."
  }
}
finally {
  Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
