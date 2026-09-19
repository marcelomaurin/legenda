param(
  [string]$AppDir = "C:\\Legenda",
  [string]$Python = "python"
)

$ErrorActionPreference = "Stop"

Write-Host "Legenda v2 - instalacao Windows"
Write-Host "Diretorio: $AppDir"

if (-not (Test-Path $AppDir)) {
  New-Item -ItemType Directory -Path $AppDir | Out-Null
}

Push-Location $AppDir
try {
  if (-not (Test-Path ".venv")) {
    & $Python -m venv .venv
  }

  & ".\\.venv\\Scripts\\python.exe" -m pip install --upgrade pip
  & ".\\.venv\\Scripts\\pip.exe" install -r requirements.txt

  if (-not (Test-Path "config.json")) {
    Copy-Item "config.example.json" "config.json"
  }

  if (-not (Test-Path "instances.json")) {
    Copy-Item "instances.example.json" "instances.json"
  }

  $taskName = "LegendaOrchestrator"
  $pythonExe = Join-Path $AppDir ".venv\\Scripts\\python.exe"
  $script = Join-Path $AppDir "bin\\orchestrator.py"
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
  Write-Host "Task Scheduler: $taskName"
  Write-Host "Configuracao: $AppDir\\instances.json"
}
finally {
  Pop-Location
}
