# CODEX QUOTA EXHAUSTED → GOOGLE GEMINI FALLBACK

## Quick Fix (5 minutes)

**When you see:** `"You've hit your usage limit. Upgrade to Pro"` in OpenClaw

### Step 1: Get Google API Key (Free!)

```
https://makersuite.google.com/app/apikey
→ Click "Create API Key" 
→ Copy it
```

### Step 2: Add to OpenClaw

```powershell
# PowerShell (as Admin):
cd C:\Users\sergen\Desktop\jarvis-mission-control

# Run setup script (interactive):
.\setup_google_fallback.ps1

# OR manual:
$googleKey = "YOUR_KEY_HERE"
$googleKey | openclaw models auth paste-token --provider google

# Set as default:
openclaw models set google/gemini-pro

# Verify:
openclaw models list
openclaw agent --message "test" --deliver
```

## What This Does

| Before | After |
|--------|-------|
| Codex quota dead = silent fail | Google Gemini takes over |
| Jarvis stops | Jarvis keeps running 24h |
| Manual fix needed | Auto-fallback |

## Full Fallback Chain (Order)

1. **Codex** (primary) — gpt-5.3-codex
2. **Google Gemini** (fallback) — gemini-pro ← You add this
3. **OpenRouter** (optional backup) — if setup

## Setup All 3 (Bulletproof)

```powershell
# 1. OpenRouter (exists in .env)
$openrouterKey = (Select-String 'OPENROUTER_API_KEY=' .env | ForEach-Object { $_.Line -split '=' | Select-Object -Last 1 }).Trim()
$openrouterKey | openclaw models auth paste-token --provider openrouter
openclaw models set openrouter/auto

# 2. Google Gemini (backup)
# Get from: https://makersuite.google.com/app/apikey
$googleKey = Read-Host "Paste Google API key"
$googleKey | openclaw models auth paste-token --provider google
openclaw models set google/gemini-pro

# 3. Test fallback
openclaw agent --message "Test: which model am I using?" --deliver
```

## Model Auth Order (What Tries First)

Edit `~\.openclaw\openclaw.json`:

```json
{
  "models": {
    "authOrder": [
      "openai-codex",    // Try Codex first
      "openrouter",      // Fall to OpenRouter
      "google"           // Final fallback to Google
    ]
  }
}
```

## Status Check

```bash
# See all configured providers:
openclaw models list

# See auth details:
type ~\.openclaw\openclaw.json | Select-String auth

# Test in order:
openclaw agent --message "Which model?" --deliver
openclaw logs --follow  # Watch which provider is called
```

## Cost Comparison

| Provider | Codex Quota | Cost |
|----------|------------|------|
| OpenAI Codex | Limited | $$ per run |
| Google Gemini | 60 calls/min free | FREE (generous) |
| OpenRouter | Metered | $$ |

**Gemini free tier is plenty for 24h loop!**

## When Codex Quota Resets

Codex quotas usually reset:
- **ChatGPT Pro** users: Monthly cycle
- **API key holders**: Depends on billing
- **Free tier**: Daily limit

You'll see: "quota reset" in openclaw logs

Then re-enable Codex:
```bash
openclaw models set openai-codex/gpt-5.3-codex
```

---

**TL;DR:** Codex dies → Google Gemini auto-takes over → Jarvis keeps running 24h ✓
