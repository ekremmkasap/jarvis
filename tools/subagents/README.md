# Jarvis Subagent Shortcuts

This folder keeps Jarvis-specific prompt generators for the Codex subagent workflow.

These scripts do not execute agents by themselves. They generate clean delegation prompts for this repository and can optionally copy the prompt to the Windows clipboard.

## Commands

- `tools\subagents\jarvis-sub-help.cmd`
- `tools\subagents\jarvis-sub-map.cmd`
- `tools\subagents\jarvis-sub-debug.cmd`
- `tools\subagents\jarvis-sub-review.cmd`
- `tools\subagents\jarvis-sub-bug.cmd`
- `tools\subagents\jarvis-sub-fix.cmd`
- `tools\subagents\jarvis-sub-audit.cmd`
- `tools\subagents\jarvis-sub-flow.cmd`
- `tools\subagents\jarvis-sub-search.cmd`
- `tools\subagents\jarvis-sub-docs.cmd`
- `tools\subagents\jarvis-sub-organize.cmd`
- `tools\subagents\jarvis-sub-python.cmd`
- `tools\subagents\jarvis-sub-ps51.cmd`
- `tools\subagents\jarvis-sub-pwsh.cmd`
- `tools\subagents\jarvis-sub-tool.cmd`
- `tools\subagents\jarvis-sub-mcp.cmd`
- `tools\subagents\jarvis-sub-ai.cmd`
- `tools\subagents\jarvis-sub-backend.cmd`
- `tools\subagents\jarvis-sub-frontend.cmd`
- `tools\subagents\jarvis-sub-wininfra.cmd`
- `tools\subagents\jarvis-sub.cmd`

## Common Usage

```bat
tools\subagents\jarvis-sub-map.cmd "login timeout handling" -Scope "server/bridge.py" -Copy
```

```bat
tools\subagents\jarvis-sub-bug.cmd "voice bridge failure" -Scope "services/voice" -Evidence "timeout after wake word" -Copy
```

```bat
tools\subagents\jarvis-sub-fix.cmd "router fallback bug" -Scope "server/bridge.py" -Implementer backend-developer -Copy
```

```bat
tools\subagents\jarvis-sub-audit.cmd "provider routing changes" -Scope "server/bridge.py" -Topic "routing and safety" -Copy
```

```bat
tools\subagents\jarvis-sub-flow.cmd "mission dispatch path" -Scope "server/bridge.py" -Copy
```

```bat
tools\subagents\jarvis-sub-backend.cmd "task routing bug" -Scope "server/bridge.py" -Copy
```

```bat
tools\subagents\jarvis-sub-frontend.cmd "dashboard panel regression" -Scope "apps/web-ui/src" -Copy
```

```bat
tools\subagents\jarvis-sub.cmd docs -Topic "OpenAI Responses API" -Question "structured output defaults" -Version latest -Copy
```

## Notes

- Commands target this repository by default, so the path argument is not needed.
- Use `-Scope` when you want to narrow the prompt to a file, module, or behavior area.
- Use `-Copy` to send the generated prompt to the Windows clipboard.
- `start_jarvis.bat --subagent-help` prints the shortcut help without launching the watchdog.

## Codex Workflow

- Source pool: `external-repos/awesome-codex-subagents/`
- Project agent directory used by Codex in this repo: `.codex/agents/`
- Jarvis shortcut layer: `tools/subagents/`
- These shortcut commands do not execute subagents directly. They generate delegation prompts for Codex.
- After generating a prompt, paste it into the active Codex session and explicitly delegate to the named subagent.
- Codex does not auto-spawn custom subagents; the prompt must say `Use backend-developer ...`, `Use reviewer ...`, or similar.

Example direct Codex prompt:

```text
Use backend-developer to implement or fix task routing bug in the Jarvis repo at C:\Users\sergen\Desktop\jarvis-mission-control, focused on server/bridge.py. Trace the entrypoint and side effects first, make the smallest coherent change, and return changed files plus success and failure validation notes.
```

Example shortcut -> Codex flow:

```bat
tools\subagents\jarvis-sub-backend.cmd "task routing bug" -Scope "server/bridge.py" -Copy
```

Paste the clipboard output into Codex and let Codex delegate from there.

## Which Shortcut To Use

- Use `jarvis-sub-search` when you do not know where the behavior lives yet.
- Use `jarvis-sub-map` when you know the area but need the exact entrypoint and side effects.
- Use `jarvis-sub-bug` or `jarvis-sub-debug` when you have a failure symptom and want root-cause analysis before patching.
- Use `jarvis-sub-fix` when the owner path is unclear and you want Codex to confirm it before editing.
- Use `jarvis-sub-backend`, `jarvis-sub-frontend`, `jarvis-sub-python`, `jarvis-sub-ps51`, or `jarvis-sub-pwsh` when the owning layer is already obvious.
- Use `jarvis-sub-review` after a change and `jarvis-sub-audit` when you need broader correctness, safety, and doc-backed constraints.
- Use `jarvis-sub-organize` when the task should be split into multiple subagent threads instead of one implementation pass.

## Recommended Delegation Patterns

- Unknown owner area: `search` -> `map` -> `fix` -> `review`
- Suspected regression: `bug` -> `backend` or `frontend` -> `review`
- Risky routing or policy work: `audit` -> `fix` -> `review`
- Large or mixed-surface work: `organize` -> specialist implementer -> `review`

Example multi-step prompt:

```text
Use search-specialist first to narrow the owner area for intermittent Telegram command failure in the Jarvis repo at C:\Users\sergen\Desktop\jarvis-mission-control, then use code-mapper to trace the confirmed flow, then use backend-developer to implement the smallest safe fix, and finally use reviewer to check regressions and missing tests.
```

## Restart Note

- You do not need to restart OpenCode just to use `.codex/agents/` or the `tools/subagents/` prompt generators.
- If OpenCode serve is already running, these docs and prompt shortcuts do not require a restart.
- If you add or replace `.toml` files under `.codex/agents/` and an already-open Codex session does not see them, refresh or restart the Codex session, not OpenCode.

## Troubleshooting

- If Codex edits the wrong area, rerun the shortcut with a tighter `-Scope`.
- If Codex does not use the intended specialist, make the prompt explicit with `Use backend-developer ...` or the exact agent name.
- If the generated prompt is too broad, start with `jarvis-sub-search` or `jarvis-sub-map` instead of a fixing shortcut.
- If clipboard copy fails, rerun without `-Copy`; the prompt text is still printed to the terminal.
- If you only need the shortcut catalog, run `tools\subagents\jarvis-sub-help.cmd` or `start_jarvis.bat --subagent-help`.
