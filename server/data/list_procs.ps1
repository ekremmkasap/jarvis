Get-Process | Where-Object { $_.CPU -gt 1 } | Sort-Object CPU -Descending | Select-Object -First 30 Name, Id, CPU, @{N='MB';E={[math]::Round($_.WorkingSet64/1MB,0)}} | Format-Table -AutoSize
