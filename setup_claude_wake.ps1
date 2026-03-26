$python = "python.exe"
$root = "C:\Users\sergen\Desktop\jarvis-mission-control"
$script = "server\agent_os\claude_wake_runner.py"

$action = New-ScheduledTaskAction -Execute $python -Argument $script -WorkingDirectory $root
$trigger = New-ScheduledTaskTrigger -Daily -At 9:02AM

Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "JARVIS Claude Wake" -Description "Claude resume package generator" -Force
Write-Output "JARVIS Claude Wake scheduled for 09:02 daily."
