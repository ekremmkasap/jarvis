$code = @"
using System;
using System.Text;
using System.Runtime.InteropServices;
using System.Collections.Generic;

public class AnyDeskHelper {
    public delegate bool EnumWindowsProc(IntPtr hWnd, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumWindows(EnumWindowsProc enumProc, IntPtr lParam);

    [DllImport("user32.dll", CharSet = CharSet.Auto)]
    public static extern int GetWindowText(IntPtr hWnd, StringBuilder strText, int maxCount);

    [DllImport("user32.dll")]
    public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);

    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);

    [DllImport("user32.dll")]
    public static extern bool IsWindowVisible(IntPtr hWnd);

    [DllImport("user32.dll")]
    public static extern bool PostMessage(IntPtr hWnd, uint Msg, IntPtr wParam, IntPtr lParam);

    [DllImport("user32.dll")]
    public static extern bool EnumChildWindows(IntPtr hWndParent, EnumWindowsProc lpEnumFunc, IntPtr lParam);

    public const uint WM_KEYDOWN = 0x0100;
    public const uint WM_KEYUP   = 0x0101;
    public const uint BM_CLICK   = 0x00F5;
    public const int  VK_RETURN  = 0x0D;
    public const int  VK_SPACE   = 0x20;

    public static List<IntPtr> GetAnyDeskWindows(uint[] pids) {
        List<IntPtr> windows = new List<IntPtr>();
        EnumWindows((hWnd, lParam) => {
            uint pid;
            GetWindowThreadProcessId(hWnd, out pid);
            foreach (uint target in pids) {
                if (pid == target && IsWindowVisible(hWnd)) {
                    StringBuilder sb = new StringBuilder(256);
                    GetWindowText(hWnd, sb, 256);
                    if (!string.IsNullOrEmpty(sb.ToString())) {
                        windows.Add(hWnd);
                    }
                }
            }
            return true;
        }, IntPtr.Zero);
        return windows;
    }

    public static IntPtr FindAcceptButton(IntPtr parent) {
        IntPtr found = IntPtr.Zero;
        EnumChildWindows(parent, (hWnd, lParam) => {
            StringBuilder sb = new StringBuilder(256);
            GetWindowText(hWnd, sb, 256);
            string text = sb.ToString().ToLower();
            if (text.Contains("accept") || text.Contains("kabul") || text.Contains("allow") || text.Contains("izin")) {
                found = hWnd;
                return false;
            }
            return true;
        }, IntPtr.Zero);
        return found;
    }

    public static void SendKeyNoFocus(IntPtr hWnd, int vk) {
        PostMessage(hWnd, WM_KEYDOWN, new IntPtr(vk), IntPtr.Zero);
        PostMessage(hWnd, WM_KEYUP,   new IntPtr(vk), IntPtr.Zero);
    }
}
"@

try { Add-Type -TypeDefinition $code -Language CSharp } catch {}

$processes = Get-Process -Name "AnyDesk" -ErrorAction SilentlyContinue
if (-not $processes) {
    Write-Output "AnyDesk calismiyor."
    exit 1
}

[System.UInt32[]]$pidArray = $processes | Select-Object -ExpandProperty Id
$windows = [AnyDeskHelper]::GetAnyDeskWindows($pidArray)

if ($windows.Count -eq 0) {
    Write-Output "Hicbir AnyDesk penceresi bulunamadi."
    exit 1
}

foreach ($w in $windows) {
    [AnyDeskHelper]::ShowWindow($w, 9) | Out-Null
    Start-Sleep -Milliseconds 300

    # 1. YONTEM: Buton bul, BM_CLICK gonder (fokus gerekmez)
    $btn = [AnyDeskHelper]::FindAcceptButton($w)
    if ($btn -ne [IntPtr]::Zero) {
        [AnyDeskHelper]::PostMessage($btn, [AnyDeskHelper]::BM_CLICK, [IntPtr]::Zero, [IntPtr]::Zero) | Out-Null
        Write-Output "kabul edildi (buton tiklandi)"
        exit 0
    }

    # 2. YONTEM: PostMessage ile Enter/Space (fokus gerekmez)
    [AnyDeskHelper]::SendKeyNoFocus($w, [AnyDeskHelper]::VK_RETURN)
    Start-Sleep -Milliseconds 200
    [AnyDeskHelper]::SendKeyNoFocus($w, [AnyDeskHelper]::VK_SPACE)
    Start-Sleep -Milliseconds 200

    # 3. YONTEM: SetForegroundWindow + SendKeys (yedek)
    [AnyDeskHelper]::SetForegroundWindow($w) | Out-Null
    Start-Sleep -Milliseconds 500
    $wshell = New-Object -ComObject wscript.shell
    $wshell.SendKeys("{ENTER}")
    Start-Sleep -Milliseconds 100
    $wshell.SendKeys("%k")
    Start-Sleep -Milliseconds 100
    $wshell.SendKeys("%a")
}

Write-Output "kabul edildi"
exit 0
