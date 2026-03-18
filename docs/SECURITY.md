# Security Baseline

## Secrets
- Never hardcode tokens or API keys in source.
- Use `.env` loaded at runtime.
- Keep `.env` out of version control.

## Incident Action
If a token is exposed in terminal/chat/source:
1. Revoke immediately.
2. Generate new token.
3. Update `.env` only.
4. Verify bot/API access with new token.

## Remote Command Safety
- Use command allowlist.
- Disable destructive shell operations by default.
- Log all remote commands with run/event IDs.
