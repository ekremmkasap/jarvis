Add-Type -AssemblyName Microsoft.VisualBasic

$wshell = New-Object -ComObject wscript.shell

$processes = Get-Process | Where-Object { $_.MainWindowTitle -match "AnyDesk" -or $_.Name -like "AnyDesk*" }
$found = $false

foreach ($p in $processes) {
    if ($p.MainWindowHandle -ne 0) {
        try {
            $null = [Microsoft.VisualBasic.Interaction]::AppActivate($p.Id)
            Start-Sleep -Milliseconds 800
            
            # Ana pencereye odaklandıktan sonra, Kabul Et demek için Enter deneyelim
            $wshell.SendKeys("{ENTER}")
            Start-Sleep -Milliseconds 200
            
            # Belki pencerede odak başka yerdedir, Tab ile dolaşıp Enter deneyelim
            $wshell.SendKeys("{TAB}")
            Start-Sleep -Milliseconds 100
            $wshell.SendKeys("{ENTER}")
            Start-Sleep -Milliseconds 100
            
            # Kısa yolları deneyelim
            $wshell.SendKeys("%k") # Alt+K (Türkçe AnyDesk için Kabul)
            Start-Sleep -Milliseconds 100
            $wshell.SendKeys("%a") # Alt+A (İngilizce AnyDesk için Accept)
            Start-Sleep -Milliseconds 100
            
            # Son çare Space tuşu
            $wshell.SendKeys(" ")
            
            Write-Output "kabul edildi ($($p.MainWindowTitle))"
            $found = $true
            break
        } catch {
            Write-Output "Pencere on plana alinamadi: $($_.Exception.Message)"
        }
    }
}

if (-not $found) {
    Write-Output "Anydesk penceresi bulunamadi veya etkinlestirilemedi."
}
