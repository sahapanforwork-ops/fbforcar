# Registers the autopilot in Windows Task Scheduler for the current Windows user (no admin needed).
#   daily    09:07                      join new groups + post once per group
#   comments 10:23 12:23 ... 20:23      find people looking for a car + comment
# The tasks wake the PC from Sleep (plugged in), and run late if the PC was off at that time.
# Remove them again:  powershell -ExecutionPolicy Bypass -File setup_autopilot.ps1 -Remove
param([switch]$Remove)

$names = @("fbforcar autopilot daily", "fbforcar autopilot comments")
if ($Remove) {
    foreach ($n in $names) { Unregister-ScheduledTask -TaskName $n -Confirm:$false -ErrorAction SilentlyContinue }
    Write-Output "Removed: $($names -join ', ')"
    exit 0
}

$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = Join-Path $env:LOCALAPPDATA "Programs\Python\Python313\python.exe"
if (-not (Test-Path $py)) { $py = (Get-Command python -ErrorAction Stop).Source }

$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 3)
$principal = New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Limited

$daily = New-ScheduledTaskAction -Execute $py -Argument "-X utf8 autopilot.py daily" -WorkingDirectory $dir
Register-ScheduledTask -TaskName $names[0] -Action $daily -Trigger (New-ScheduledTaskTrigger -Daily -At "09:07") `
    -Settings $settings -Principal $principal -Description "fbforcar: join new groups + post once per group (autopilot.py daily)" -Force | Out-Null

$times = "10:23", "12:23", "14:23", "16:23", "18:23", "20:23"
$triggers = $times | ForEach-Object { New-ScheduledTaskTrigger -Daily -At $_ }
$comments = New-ScheduledTaskAction -Execute $py -Argument "-X utf8 autopilot.py comments" -WorkingDirectory $dir
Register-ScheduledTask -TaskName $names[1] -Action $comments -Trigger $triggers `
    -Settings $settings -Principal $principal -Description "fbforcar: find people looking for a car + comment (autopilot.py comments)" -Force | Out-Null

foreach ($n in $names) {
    $i = Get-ScheduledTaskInfo -TaskName $n
    Write-Output ("{0}: next run {1}" -f $n, $i.NextRunTime)
}
