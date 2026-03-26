# AI Development Automation Architecture

## Goal

Add a modular GitHub automation layer to `jarvis-mission-control` without coupling it to the active Telegram or desktop voice runtime.

## Scope

The automation layer handles repository events such as pull requests, issues, CI failures, and scheduled summaries.

## Design Rules

- Keep the active Jarvis runtime in `server/` and desktop launchers unchanged.
- Keep automation prompts outside Python code under `prompts/`.
- Keep repository-specific behavior in `config/`.
- Keep every automation agent isolated behind the same contract.
- Support dry-run execution first, then GitHub publishing.

## Runtime Flow

`GitHub Event -> Workflow -> scripts/run_agent.py -> Agent.collect() -> Prompt Render -> LLM/Fallback -> validate() -> publish()`

## Initial Agents

1. `git_summarizer`
2. `pr_reviewer`
3. `ci_triager`
4. `issue_router`

## Shared Components

- `agents/base.py`
  Common agent contract and execution flow.
- `agents/registry.py`
  Registry for resolving agent names to implementations.
- `scripts/github_client.py`
  GitHub API access for PRs, issues, workflow runs, comments, and labels.
- `scripts/llm_client.py`
  Ollama-compatible LLM execution with graceful fallback.
- `scripts/prompt_loader.py`
  Markdown prompt loading and template rendering.
- `scripts/markdown_publish.py`
  Output persistence and GitHub publishing helpers.

## Output Policy

- Persist every execution to `outputs/`.
- Do not publish empty or malformed responses.
- Default to dry-run unless `--publish` is explicitly passed.

## Extension Path

Planned second-wave agents:

- `release_writer`
- `changelog_agent`
- `performance_agent`
- `self_improver`
