param(
  [string]$AppDir = "C:\Legenda"
)

$ErrorActionPreference = "Stop"

$SourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$PackageRoot = Split-Path -Parent $SourceDir

Write-Host "Legenda v2 - instalacao portavel Windows"
Write-Host "Origem : $PackageRoot"
Write-Host "Destino: $AppDir"

if (-not (Test-Path (Join-Path $PackageRoot "python\python.exe"))) {
  throw "Runtime Python embutido nao encontrado em python\python.exe."
}

if (-not (Test-Path $AppDir)) {
  New-Item -ItemType Directory -Path $AppDir -Force | Out-Null
}

$preserve = @("config.json", "instances.json", "nodes.json")
$backup = @{}

foreach ($name in $preserve) {
  $path = Join-Path $AppDir $name
  if (Test-Path $path) {
    $backup[$name] = Get-Content $path -Raw
  }
}

Write-Host "Copiando arquivos..."
Get-ChildItem -Path $PackageRoot -Force | ForEach-Object {
  Copy-Item $_.FullName -Destination $AppDir -Recurse -Force
}

foreach ($entry in $backup.GetEnumerator()) {
  Set-Content -Path (Join-Path $AppDir $entry.Key) -Value $entry.Value -Encoding UTF8
}

if (-not (Test-Path (Join-Path $AppDir "config.json"))) {
  Copy-Item (Join-Path $AppDir "config.example.json") (Join-Path $AppDir "config.json")
}

if (-not (Test-Path (Join-Path $AppDir "instances.json"))) {
  Copy-Item (Join-Path $AppDir "instances.example.json") (Join-Path $AppDir "instances.json")
}

$taskName = "LegendaOrchestrator"
$pythonExe = Join-Path $AppDir "python\python.exe"
$script = Join-Path $AppDir "bin\orchestrator.py"
$instances = Join-Path $AppDir "instances.json"
$argument = '"' + $script + '" "' + $instances + '"'

$action = New-ScheduledTaskAction -Execute $pythonExe -Argument $argument -WorkingDirectory $AppDir
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Force | Out-Null
Start-ScheduledTask -TaskName $taskName

Write-Host ""
Write-Host "Instalacao concluida."
Write-Host "Python embutido: $pythonExe"
Write-Host "Task Scheduler : $taskName"
Write-Host "Configuracao   : $AppDir\instances.json"
