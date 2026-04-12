# 204 Operator Surface Plan - /codex-accounts

Date: 2026-04-13

## Page Role

`/codex-accounts` becomes the operator control plane for the five Codex slots:

- atlas
- forge
- nexus
- shield
- spark

It should remain under the admin/control boundary and not become a public landing surface.

## Polling Contract

Refresh every 5 seconds:

- `GET /api/codex/slots`
- `GET /api/codex/queue`
- `GET /api/codex/health`

On-demand actions:

- `GET /api/codex/jobs`
- `GET /api/codex/audit`
- `POST /api/codex/dispatch`
- `POST /api/codex/control`

## Panels

### 1. Account List Panel

Per slot show:

- `slot_id`
- `label`
- role badge
- status badge
- quota progress / estimate
- current job summary
- elapsed duration if running
- last completion
- fail count
- cooldown remaining

### 2. Live Work Panel

Sections:

- running jobs
- pending queue in priority order
- failed jobs (last 10)

### 3. Controls Panel

Per-slot controls:

- Drain
- Pause
- Disable
- Force Retry

Global controls:

- Dispatch form
- Clear all cooldowns

### 4. Health Panel

Per-slot health indicators:

- green / yellow / red
- stuck job count
- quota burn rate
- cooldown state
- last 10 dispatch decisions

## Type Contract Requirements

The UI should define exact TypeScript interfaces for:

- slot records
- queue records
- job records
- health records
- audit records
- dispatch/control responses

No implicit `any` data plumbing for the new control-plane endpoints.

## Design Rules

- Reuse existing Tailwind classes and page tone
- No new npm packages
- Keep operator-first density; no marketing treatment
- Make actions obvious and reversible where possible
- Do not render sensitive values from execution truth
