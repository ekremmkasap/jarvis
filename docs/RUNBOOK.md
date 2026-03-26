# Automation Runbook

## First Run

1. Copy `.env.example` to `.env` if needed.
2. Set `GITHUB_TOKEN` for publish mode.
3. Set `AUTOMATION_MODEL` if LLM output should use Ollama.
4. Start with dry-run mode.

## Dry-Run Commands

```bash
python scripts/run_agent.py --agent git_summarizer
python scripts/run_agent.py --agent pr_reviewer --event-path path/to/pull_request_event.json
python scripts/run_agent.py --agent ci_triager --event-path path/to/workflow_run_event.json
python scripts/run_agent.py --agent issue_router --event-path path/to/issue_event.json
```

## Publish Mode

Use `--publish` only after validating dry-run output.

## Failure Handling

- If GitHub credentials are missing, persist markdown locally and skip publish.
- If Ollama is unavailable, agents fall back to deterministic markdown output.
- If validation fails, exit non-zero so workflows fail visibly.
