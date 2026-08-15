param(
  [string]$StorageRoot = "$PSScriptRoot\..\storage",
  [int]$RetentionDays = 14
)

$resolved = (Resolve-Path $StorageRoot).Path
$backupRoot = Join-Path $resolved "backups"
New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$archive = Join-Path $backupRoot "manual-$stamp"
$archivePath = "$archive.zip"

Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
$zip = [System.IO.Compression.ZipFile]::Open($archivePath, [System.IO.Compression.ZipArchiveMode]::Create)
try {
  $backupPrefix = "$([System.IO.Path]::GetFullPath($backupRoot))$([System.IO.Path]::DirectorySeparatorChar)"
  $rootPrefix = "$([System.IO.Path]::GetFullPath($resolved).TrimEnd([System.IO.Path]::DirectorySeparatorChar))$([System.IO.Path]::DirectorySeparatorChar)"
  $logsPrefix = "$([System.IO.Path]::GetFullPath((Join-Path $resolved 'logs')))$([System.IO.Path]::DirectorySeparatorChar)"
  Get-ChildItem -LiteralPath $resolved -File -Recurse |
    Where-Object {
      -not $_.FullName.StartsWith($backupPrefix, [System.StringComparison]::OrdinalIgnoreCase) -and
      -not $_.FullName.StartsWith($logsPrefix, [System.StringComparison]::OrdinalIgnoreCase)
    } |
    ForEach-Object {
      $entryName = $_.FullName.Substring($rootPrefix.Length).Replace("\", "/")
      [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
        $zip,
        $_.FullName,
        $entryName,
        [System.IO.Compression.CompressionLevel]::Optimal
      ) | Out-Null
    }
}
finally {
  $zip.Dispose()
}

Get-ChildItem $backupRoot -Filter "*.zip" |
  Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-$RetentionDays) } |
  Remove-Item -Force
Write-Output "Storage backup created: $archivePath"
