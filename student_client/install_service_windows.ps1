$pythonPath = (Get-Command python).Source
$scriptPath = Join-Path $PSScriptRoot "service.py"
$taskName = "NetSupportStudentService"

schtasks /Create /F /SC ONLOGON /RL HIGHEST /TN $taskName /TR "`"$pythonPath`" `"$scriptPath`""
Write-Host "Startup task created: $taskName"
