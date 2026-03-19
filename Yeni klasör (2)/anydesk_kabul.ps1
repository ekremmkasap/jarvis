# anydesk_kabul.ps1
# AnyDesk gelen bağlantı isteğini otomatik kabul eder
# Telegram /kabul veya Claude trigger dosyası üzerinden çağrılır

Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
Add-Type -AssemblyName Microsoft.VisualBasic
Add-Type -AssemblyName System.Windows.Forms

function Accept-AnyDesk {
    # AnyDesk process'i çalışıyor mu?
    $proc = Get-Process -Name "AnyDesk" -ErrorAction SilentlyContinue
    if (-not $proc) {
        Write-Output "AnyDesk çalışmıyor."
        exit 1
    }

    # UI Automation ile Accept butonunu bul
    $desktop = [System.Windows.Automation.AutomationElement]::RootElement

    # AnyDesk pencerelerini tara
    $walker = [System.Windows.Automation.TreeWalker]::ControlViewWalker
    $child = $walker.GetFirstChild($desktop)

    while ($child -ne $null) {
        $name = $child.Current.Name
        if ($name -like "*AnyDesk*") {
            # Accept / Kabul Et butonunu ara
            $btnNames = @("Accept", "Kabul Et", "Akzeptieren", "Aceptar")
            foreach ($btnName in $btnNames) {
                $cond = New-Object System.Windows.Automation.PropertyCondition(
                    [System.Windows.Automation.AutomationElement]::NameProperty, $btnName
                )
                $btn = $child.FindFirst([System.Windows.Automation.TreeScope]::Descendants, $cond)
                if ($btn) {
                    try {
                        $invoke = $btn.GetCurrentPattern([System.Windows.Automation.InvokePattern]::Pattern)
                        $invoke.Invoke()
                        Write-Output "✅ AnyDesk bağlantısı kabul edildi! (Buton: $btnName)"
                        exit 0
                    } catch {
                        Write-Output "Buton tıklanamadı, SendKeys deneniyor..."
                    }
                }
            }

            # Buton bulunamazsa pencereyi öne al + Enter gönder
            [Microsoft.VisualBasic.Interaction]::AppActivate("AnyDesk")
            Start-Sleep -Milliseconds 500
            [System.Windows.Forms.SendKeys]::SendWait("{TAB}{ENTER}")
            Write-Output "✅ AnyDesk'e Enter gönderildi."
            exit 0
        }
        $child = $walker.GetNextSibling($child)
    }

    Write-Output "❌ AnyDesk bağlantı isteği penceresi bulunamadı."
    exit 1
}

Accept-AnyDesk
