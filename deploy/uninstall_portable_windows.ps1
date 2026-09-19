param(
  [string]$AppDir = "C:\Legenda",
  [switch]$RemoveData
)

$ErrorActionPreference = "Stop"
$taskName = "LegendaOrchestrator"

$task = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($task) {
  Stop-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
  Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
  Write-Host "Tarefa $taskName removida."
}

if ($RemoveData -and (Test-Path $AppDir)) {
  Remove-Item $AppDir -Recurse -Force
  Write-Host "Diretorio $AppDir removido."
}
else {
  Write-Host "Arquivos preservados em $AppDir."
}
