param(
  [string]$Version = "dev",
  [string]$OutputDir = "dist",
  [string]$PythonVersion = "3.11.9"
)

$ErrorActionPreference = "Stop"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$Stage = Join-Path $Root "$OutputDir\Legenda-$Version"
$ZipPath = Join-Path $Root "$OutputDir\Legenda-$Version-win64.zip"

if (Test-Path $Stage) { Remove-Item $Stage -Recurse -Force }
New-Item -ItemType Directory -Path $Stage -Force | Out-Null

$copyDirs = @("bin", "web", "corpus", "deploy", "docs")
foreach ($dir in $copyDirs) {
  Copy-Item (Join-Path $Root $dir) (Join-Path $Stage $dir) -Recurse -Force
}

$copyFiles = @(
  "README.md",
  "requirements.txt",
  "requirements-diarization.txt",
  "config.example.json",
  "instances.example.json",
  "nodes.example.json",
  "benchmark_manifest.example.jsonl"
)
foreach ($file in $copyFiles) {
  $source = Join-Path $Root $file
  if (Test-Path $source) {
    Copy-Item $source (Join-Path $Stage $file) -Force
  }
}

$pythonDir = Join-Path $Stage "python"
New-Item -ItemType Directory -Path $pythonDir -Force | Out-Null

$pythonZip = Join-Path $env:TEMP "python-$PythonVersion-embed-amd64.zip"
$pythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-embed-amd64.zip"

Write-Host "Baixando Python embeddable $PythonVersion..."
Invoke-WebRequest -Uri $pythonUrl -OutFile $pythonZip
Expand-Archive -Path $pythonZip -DestinationPath $pythonDir -Force

$pth = Get-ChildItem $pythonDir -Filter "python*._pth" | Select-Object -First 1
if (-not $pth) { throw "Arquivo python*._pth nao encontrado." }

$pthContent = Get-Content $pth.FullName
$pthContent = $pthContent | ForEach-Object {
  if ($_ -eq "#import site") { "import site" } else { $_ }
}
$pthContent += "Lib\site-packages"
Set-Content -Path $pth.FullName -Value $pthContent -Encoding ASCII

$sitePackages = Join-Path $pythonDir "Lib\site-packages"
New-Item -ItemType Directory -Path $sitePackages -Force | Out-Null

Write-Host "Instalando dependencias dentro do pacote..."
python -m pip install --upgrade pip
python -m pip install --only-binary=:all: --target $sitePackages -r (Join-Path $Root "requirements.txt")

$versionFile = @{
  version = $Version
  python = $PythonVersion
  built_at = (Get-Date).ToUniversalTime().ToString("o")
} | ConvertTo-Json
Set-Content -Path (Join-Path $Stage "VERSION.json") -Value $versionFile -Encoding UTF8

if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
Compress-Archive -Path (Join-Path $Stage "*") -DestinationPath $ZipPath -CompressionLevel Optimal

$hash = Get-FileHash -Path $ZipPath -Algorithm SHA256
$checksumPath = "$ZipPath.sha256"
"$($hash.Hash.ToLower())  $(Split-Path $ZipPath -Leaf)" | Set-Content -Path $checksumPath -Encoding ASCII

Write-Host "Pacote: $ZipPath"
Write-Host "SHA256: $checksumPath"
