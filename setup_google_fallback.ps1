# Setup Google Gemini Fallback for OpenClaw
# When Codex quota dies → Use Google Gemini instead
# Run this ONLY when Codex quota exhausted

Write-Host "[*] Setting up Google Gemini fallback for OpenClaw..."
Write-Host ""
Write-Host "Step 1: Get your Google Gemini API key"
Write-Host "  Go to: https://makersuite.google.com/app/apikey"
Write-Host "  Click 'Create API Key'"
Write-Host "  Copy the key"
Write-Host ""

$googleKey = Read-Host "Paste your Google API key"

if (-not $googleKey -or $googleKey.Length -lt 10) {
    Write-Host "[!] Invalid API key. Aborting."
    exit 1
}

# Configure OpenClaw main profile with Google
Write-Host "[*] Configuring OpenClaw main profile..."
$cmd = @(
    "openclaw",
    "models", "auth", "paste-token",
    "--provider", "google"
)

$googleKey | & $cmd[0] @cmd[1..($cmd.Length-1)]

Write-Host "[*] Setting Google as default model..."
openclaw models set google/gemini-pro

Write-Host "[*] Checking configuration..."
openclaw models list | Select-String google

Write-Host ""
Write-Host "Setup complete!"
Write-Host "Fallback: Google Gemini is now active in OpenClaw"
Write-Host ""
Write-Host "Test:"
openclaw agent --message "Merhaba, ben Google Gemini ile bağlanmış Jarvis'im" --deliver
