"""
Masaüstüne 3 Codex sekme promptu yazar.
Çalıştır: python scripts/write_codex_prompts.py
"""
import pathlib

DESKTOP = pathlib.Path(r"C:\Users\sergen\Desktop")

# ============================================================
# TAB 2 — Multi-Account Control Plane
# ============================================================
TAB2 = r"""================================================================================
CODEX TAB-2 — JARVIS MULTI-ACCOUNT CONTROL PLANE
FINAL HARDCORE EXECUTION PROMPT
Repo: C:\Users\sergen\Desktop\jarvis-mission-control
Mode: PLAN-FIRST -> AUTO-EXECUTE -> VALIDATE -> CLAUDE.MD UPDATE
================================================================================

YOU ARE: Elite AI Software Engineer + CTO Auditor + Architect + Implementer
LANGUAGE: Turkish for user output, English for code/paths/configs
REPO: C:\Users\sergen\Desktop\jarvis-mission-control

================================================================================
ABSOLUTE RULES
================================================================================

1.  PLAN FIRST — do not write code until OPS/ planning artifacts exist on disk
2.  EXECUTE SECOND — after plan artifacts, execute all slices autonomously
3.  VALIDATE THIRD — run pytest after every slice before moving to next
4.  CLAUDE.MD FOURTH — update CLAUDE.md after every slice, commit separately
5.  NEVER expose API keys / tokens in logs, stdout, or API responses
6.  NEVER force-push, hard-reset, or delete unrelated work
7.  NEVER create a third Codex account registry
8.  NEVER trust README/docs over running code
9.  NEVER stop mid-task without writing OPS/208_HANDOFF.md
10. COMMIT after every slice with a descriptive message
11. Maximum parallel work — write tests alongside implementation in same slice
12. If a test fails: fix before moving to next slice, never skip

================================================================================
CLAUDE.MD UPDATE RULE — NON-NEGOTIABLE
================================================================================

After EVERY slice:
  1. Read CLAUDE.md
  2. Find or create section:
       ### Multi-Codex Control Plane (Tab-2 Codex Sprint)
  3. Update: status, completed, remaining, next step
  4. Commit: "chore: update CLAUDE.md — codex multi-account slice N progress"

================================================================================
EXISTING LOCAL ARCHITECTURE — BUILD ON THIS, NOT FROM SCRATCH
================================================================================

EXECUTION TRUTH (preserve, never replace):
  state/codex-accounts/
    atlas/    — Manager/Core slot
    forge/    — Backend slot
    nexus/    — Overflow/Reserve slot
    shield/   — Security slot
    spark/    — Voice/Video slot

METADATA TRUTH (preserve, never replace):
  config/account_registry.json
    label, role, quota_estimate, visible_status, operator_notes per slot

EXISTING CODE (read all before touching any):
  server/account_manager.py          merge/orchestration layer
  server/codex_orchestrator.py       job dispatch + CODEX_HOME isolation
  server/codex_task_router.py        routing logic
  server/codex_job_manager.py        job queue (prev sprint)
  server/codex_quota_tracker.py      quota tracking (prev sprint)
  server/codex_health.py             health watcher (prev sprint)
  server/codex_workspace.py          workspace helper (prev sprint)
  server/orchestrator_gateway.py     multi-provider gateway
  apps/web-ui/src/app/codex-accounts/page.tsx   operator UI
  tools/codex_accounts.py            auth snapshot tooling
  codex-accounts.ps1                 PowerShell auth switch
  docs/CODEX_ACCOUNTS.md             spec doc
  server/SOURCE_OF_TRUTH.md          ownership model

================================================================================
PHASE 1 — PLAN MODE (no writes until OPS/ artifacts exist)
================================================================================

AUDIT STEPS:
  1.1  Read state/codex-accounts/ — map all slot files, format, consistency
  1.2  Read config/account_registry.json — map all fields, check slot parity
  1.3  Read server/codex_orchestrator.py — dispatch flow, real vs stubbed
  1.4  Read server/account_manager.py — merge logic, public API
  1.5  Read server/codex_task_router.py — routing rules
  1.6  Read server/codex_job_manager.py + codex_quota_tracker.py — job state format
  1.7  Read server/codex_health.py + codex_workspace.py — health, worktree logic
  1.8  Read apps/web-ui/src/app/codex-accounts/page.tsx — current UI state
  1.9  Search server/bridge.py for /codex and /api/codex — map endpoints

PLANNING ARTIFACTS (create before any code):

  OPS/200_AUDIT.md
    Slot file inventory, registry field map, consistency check,
    real vs stubbed per server file

  OPS/201_ARCHITECTURE_DECISION.md
    Control plane owner, scheduler design, queue persistence decision,
    failover policy, worktree isolation strategy

  OPS/202_GAP_ANALYSIS.md
    Per category — scheduler, queue, routing, quota, failover,
    worktree, operator UI, observability, security, handoff

  OPS/203_ROLLOUT_PLAN.md
    Faz 1: Foundation hardening
    Faz 2: Scheduler + queue + role affinity
    Faz 3: Worktree isolation + failover + cooldown
    Faz 4: Operator UI + observability

  OPS/204_OPERATOR_SURFACE_PLAN.md
    /codex-accounts page spec — tabs, fields, actions, metrics, refresh rate

After OPS/ artifacts written: SWITCH TO BUILD MODE automatically.

================================================================================
PHASE 2 — BUILD MODE (slice by slice, test + commit + CLAUDE.md each)
================================================================================

---  SLICE 1: server/account_manager.py — Single source of truth hardening  ---

Goal: every caller goes through account_manager, no direct state/ file reads.
  - get_slot(slot_id) -> merged dict (execution truth + metadata truth)
  - list_slots() -> all 5 slots merged
  - get_active_slot() -> currently selected slot
  - set_slot_status(slot_id, status) -> updates execution truth only
  - get_quota_estimate(slot_id) -> from metadata truth only
  - is_slot_available(slot_id) -> checks state + cooldown combined
  - _redact_sensitive(data) -> strips auth_token, password, secret from any dict
  Add: tests/test_account_manager.py (all methods covered)
  Commit: "feat: harden account_manager as single SOT for slot reads"
  CLAUDE.md update.

---  SLICE 2: server/codex_task_router.py — Role affinity routing table  ---

  ROLE_AFFINITY = {
    "backend":  ["forge", "nexus"],
    "security": ["shield", "nexus"],
    "voice":    ["spark", "nexus"],
    "video":    ["spark", "nexus"],
    "core":     ["atlas", "forge"],
    "manager":  ["atlas"],
    "overflow": ["nexus"],
    "any":      ["atlas", "forge", "nexus", "shield", "spark"],
  }
  SLOT_ROLES = {
    "atlas": "manager", "forge": "backend", "nexus": "overflow",
    "shield": "security", "spark": "voice",
  }
  route_task(task: dict) -> slot_id
    - read task["role"] or task["type"]
    - get affinity list
    - filter by account_manager.is_slot_available
    - pick first available
    - last resort: nexus
    - if nexus unavailable: raise SlotExhaustedError
  get_fallback_chain(role: str) -> list[str]
  Add: tests/test_codex_task_router.py
  Commit: "feat: role-affinity routing table in codex_task_router"
  CLAUDE.md update.

---  SLICE 3: server/codex_job_manager.py — Persistent job queue  ---

  Job canonical format:
    job_id, created_at, updated_at,
    status: pending|running|done|failed|cancelled,
    priority: 0-10, role, slot_id, worktree,
    task: {description, type, payload},
    retries, max_retries (default 3),
    failure_reason, started_at, completed_at, output_summary
  Persistence: state/codex_jobs.jsonl (append-friendly line-delimited JSON)
  Implement:
    enqueue(job: dict) -> job_id
    dequeue(role=None) -> next pending job (priority order)
    update_job(job_id, **kwargs)
    get_job(job_id) -> dict
    list_jobs(status=None, slot_id=None, limit=50) -> list
    retry_job(job_id)
    cancel_job(job_id)
    purge_old_jobs(days=7)
    find_stuck_jobs(timeout_minutes=30) -> list of running jobs older than N min
  Add: tests/test_codex_job_manager.py
  Commit: "feat: persistent job queue — state/codex_jobs.jsonl"
  CLAUDE.md update.

---  SLICE 4: server/codex_orchestrator.py — Quota-aware dispatcher  ---

  dispatch(job_id) -> slot_id:
    a. get job from job_manager
    b. get affinity chain from task_router
    c. for each slot in chain:
       - account_manager.is_slot_available(slot)
       - quota_tracker.has_quota(slot, estimated_tokens)
       - if both OK: assign, update job, return slot_id
    d. if no slot: requeue with 5-min delay, log reason
  Cooldown layer:
    Persistence: state/codex_cooldowns.json
    is_in_cooldown(slot_id) -> bool
    set_cooldown(slot_id, minutes=5)
    clear_cooldown(slot_id)
  Failover:
    On mid-job slot failure: get_fallback_chain -> pick next available slot
    Update job record with new slot + failure reason
  Audit log: append every dispatch decision to server/logs/codex_dispatch_audit.jsonl
    Fields: ts, job_id, role, affinity_chain, selected_slot, reason,
            quota_before, cooldown_state
  Add: tests/test_codex_orchestrator.py
  Commit: "feat: quota-aware dispatcher + cooldown + failover + audit log"
  CLAUDE.md update.

---  SLICE 5: server/bridge.py — /api/codex/* operator endpoints  ---

  Add only if endpoint does not already exist (backward-safe):
    GET  /api/codex/slots
         -> list 5 slots: slot_id, label, role, status, quota_estimate,
            is_available, current_job, last_completion, fail_count, cooldown_remaining
    GET  /api/codex/jobs?status=X&slot_id=X
         -> filtered job list (max 100)
    GET  /api/codex/queue
         -> pending jobs in priority order
    POST /api/codex/dispatch
         Body: {task_description, role, priority}
         -> {job_id, slot_id, status: pending}
    POST /api/codex/control
         Body: {action: drain|pause|disable|retry|cancel, slot_id, job_id}
         -> {ok, message}
    GET  /api/codex/health
         -> per-slot health score, stuck jobs, cooldown status
    GET  /api/codex/audit
         -> last 50 lines of codex_dispatch_audit.jsonl (redacted)
  All endpoints: _redact_sensitive on every returned dict
  Do NOT remove or break existing /api/* endpoints
  Commit: "feat: /api/codex/* operator endpoints in bridge.py"
  CLAUDE.md update.

---  SLICE 6: apps/web-ui/src/app/codex-accounts/page.tsx — Live UI  ---

  Poll every 5s: /api/codex/slots, /api/codex/queue, /api/codex/health
  ACCOUNT LIST PANEL:
    - slot_id, label, role (color-coded badge per role)
    - status badge: active (green) / idle (blue) / cooldown (orange) / disabled (red)
    - quota progress bar (estimate from metadata)
    - current_job (if running, show description + duration)
    - last_completion timestamp
    - fail_count (red text if > 3)
  LIVE WORK PANEL:
    - Running jobs: slot badge, task_description, started_at, elapsed duration
    - Pending queue: priority order, assigned role, estimated slot
    - Failed jobs (last 10): slot, failure_reason, retry button
  CONTROLS PANEL:
    - Per-slot: [Drain] [Pause] [Disable] [Force-Retry] buttons
    - Global: [Dispatch New Job] form — description + role select + priority slider
    - Global: [Clear All Cooldowns] button
  HEALTH PANEL:
    - per-slot health indicator (green/yellow/red dot)
    - stuck jobs count (orange warning if > 0)
    - quota burn rate per slot
    - last 10 dispatch decisions (from /api/codex/audit)
  TypeScript types must match API response exactly.
  Use existing Tailwind classes, no new npm packages.
  Commit: "feat: live /codex-accounts operator UI — slots queue health controls"
  CLAUDE.md update.

---  SLICE 7: server/codex_workspace.py — Per-slot worktree isolation  ---

  Check: git worktree list
  Target worktree paths:
    worktrees/atlas/  branch: codex/atlas
    worktrees/forge/  branch: codex/forge
    worktrees/nexus/  branch: codex/nexus
    worktrees/shield/ branch: codex/shield
    worktrees/spark/  branch: codex/spark
  Implement:
    ensure_worktree(slot_id) -> path (creates if not exists)
    get_worktree_path(slot_id) -> str
    cleanup_worktree(slot_id, job_id) — removes job-specific temp branches
    list_worktrees() -> dict slot_id -> path
  Add worktrees/ to .gitignore
  Update codex_orchestrator dispatch():
    - call ensure_worktree(slot_id) before job start
    - set CODEX_HOME = worktree path
    - set GIT_WORK_TREE = worktree path
  Add: tests/test_codex_workspace.py
  Commit: "feat: per-slot git worktree isolation in codex_workspace"
  CLAUDE.md update.

---  SLICE 8: server/bridge.py — Telegram /codex-* commands  ---

  Add only if command does not already exist:
    /codex-durum
      -> GET /api/codex/slots internally
      -> Turkish summary: "5 slot durumu:\n- atlas: idle\n- forge: running..."
    /codex-kuyruk
      -> GET /api/codex/queue
      -> Turkish: "Kuyrukta N is var:\n1. [priority] [role] [desc]..."
    /codex-baslat <role> <aciklama>
      -> POST /api/codex/dispatch
      -> Turkish: "Is kuyruga eklendi: JOB_ID — slot: forge"
    /codex-saglik
      -> GET /api/codex/health
      -> Turkish health summary + stuck jobs warning
    /codex-hesaplar
      -> per-slot: label, role, status, quota estimate — Turkish
  All Telegram responses: max 400 chars, truncate with "..." if longer
  Commit: "feat: /codex-* Telegram commands in bridge.py"
  CLAUDE.md update.

---  SLICE 9: Final integration test + handoff  ---

  Run full test suite:
    python -m pytest tests/test_account_manager.py \
      tests/test_codex_task_router.py \
      tests/test_codex_job_manager.py \
      tests/test_codex_orchestrator.py \
      tests/test_codex_workspace.py \
      tests/test_codex_health.py \
      tests/test_codex_management.py \
      -v --tb=short
  Fix all failures before continuing.

  Run smoke test:
    python -c "
    import sys; sys.path.insert(0,'server')
    from account_manager import AccountManager
    from codex_task_router import CodexTaskRouter
    from codex_job_manager import CodexJobManager
    am = AccountManager()
    slots = am.list_slots()
    assert len(slots) == 5, f'FAIL: expected 5 slots got {len(slots)}'
    router = CodexTaskRouter()
    slot = router.route_task({'role':'backend','description':'smoke'})
    print(f'route_task backend -> {slot}')
    jm = CodexJobManager()
    jid = jm.enqueue({'role':'backend','description':'smoke test job'})
    j = jm.get_job(jid)
    assert j['status'] == 'pending'
    print('ALL SMOKE TESTS PASSED')
    "

  Write OPS/208_HANDOFF.md:
    - completed slices list
    - known remaining gaps
    - how to run: python server/bridge.py then open /codex-accounts
    - API endpoint summary table
    - slot role reference table
    - how to resume from this point
    - known risks

  Final CLAUDE.md update:
    ### Multi-Codex Control Plane (Tab-2 Codex Sprint)
    - Durum: TAMAMLANDI
    - Slices: 1-8 tamamlandi
    - Tests: pytest N passed
    - Operator UI: http://localhost:8081/codex-accounts
    - Telegram: /codex-durum /codex-kuyruk /codex-baslat /codex-saglik
    - Handoff: OPS/208_HANDOFF.md

  Final commit: "feat: multi-codex control plane complete — 5-slot scheduler, queue, worktree, UI, Telegram"

================================================================================
ANTI-HALLUCINATION RULES
================================================================================

- Do NOT create a third Codex account registry
- Do NOT replace state/codex-accounts/ or config/account_registry.json
- Do NOT invent slot names — only: atlas, forge, nexus, shield, spark
- Do NOT expose auth tokens in API responses or logs
- Do NOT claim success without a passing pytest run
- Do NOT skip OPS/ artifact creation
- Do NOT skip CLAUDE.md updates
- Do NOT add npm/pip packages not already in package.json / requirements.txt
- Do NOT break existing bridge.py backward-compat endpoints
- Do NOT push to main/master branch

================================================================================
GO. PLAN FIRST. EXECUTE AUTONOMOUSLY. TEST. COMMIT. UPDATE CLAUDE.MD. HANDOFF.
================================================================================
"""

# ============================================================
# TAB 3 — AGENTS.md 9-Agent Canonical Implementation
# ============================================================
TAB3 = r"""================================================================================
CODEX TAB-3 — JARVIS AGENTS.MD 9-AGENT CANONICAL IMPLEMENTATION
FINAL HARDCORE EXECUTION PROMPT
Repo: C:\Users\sergen\Desktop\jarvis-mission-control
Mode: PLAN-FIRST -> AUTO-EXECUTE -> VALIDATE -> CLAUDE.MD UPDATE
================================================================================

YOU ARE: Elite AI Software Engineer + Systems Architect + Implementer
LANGUAGE: Turkish for user output, English for code/paths/configs
REPO: C:\Users\sergen\Desktop\jarvis-mission-control

================================================================================
ABSOLUTE RULES
================================================================================

1.  READ AGENTS.md FIRST — it is the canonical spec, do not deviate from it
2.  PLAN FIRST — create OPS/ artifacts before any code
3.  EXECUTE AUTONOMOUSLY — implement all 9 agents + bridge routing + voice hook
4.  VALIDATE — pytest after every agent batch
5.  CLAUDE.MD UPDATE — after every phase, update CLAUDE.md, commit separately
6.  NEVER expose API keys or tokens in logs or stdout
7.  NEVER break existing bridge.py endpoints (backward-safe only)
8.  NEVER touch master_launcher.py without explicit user approval
9.  NEVER claim success without passing tests
10. COMMIT after every implementation batch

================================================================================
CLAUDE.MD UPDATE RULE — NON-NEGOTIABLE
================================================================================

After every phase:
  1. Read CLAUDE.md
  2. Find or create: ### AGENTS.md 9-Agent Canonical (Tab-3 Codex Sprint)
  3. Update: status, completed agents, remaining, next step
  4. Commit: "chore: update CLAUDE.md — agents.md canonical phase N progress"

================================================================================
AGENTS.MD SPEC — READ THIS FIRST
================================================================================

Read AGENTS.md fully before writing any code.
The 9 canonical agents defined there are:
  1. PlannerAgent         — Goal -> structured plan, agent assignment
  2. RepoAnalystAgent     — git log + file scan -> health report
  3. DeveloperAgent       — Feature/bug -> code change via Claude Code CLI
  4. ReviewerAgent        — git diff -> review report (read-only)
  5. DebugAgent           — Error message -> root cause analysis
  6. ReleaseAgent         — git log -> changelog + semver suggestion
  7. DocsAgent            — Code/command -> documentation update
  8. VoiceNarratorAgent   — Technical output -> 2-3 sentence TTS text
  9. MissionControlAgent  — Monitor all agents, detect stuck tasks

These 9 agents are THE spec. Do not add, remove, or rename them.

================================================================================
EXISTING CODE — READ BEFORE TOUCHING
================================================================================

  AGENTS.md                    canonical spec (read-only reference)
  server/bridge.py             command router (backward-safe only)
  server/agent_loop.py         existing agent loop
  server/model_router.py       LLM routing (use this for all LLM calls)
  hey_jarvis.py                voice assistant (add voice hook here)
  server/agents/               existing agent directory
  server/agents/clones/        7-agent swarm (different from these 9 canonical)
  config/model_router.yml      model routing config
  .env                         API keys (never log)

NOTE: The 9 canonical agents are DIFFERENT from the 7 swarm clone agents.
  - Swarm clones (seda/mert/buse/etc): dialogue agents, voice conversation
  - Canonical agents (planner/developer/etc): task execution agents
  Do not confuse or merge them.

================================================================================
PHASE 1 — PLAN MODE
================================================================================

STEP 1.1: Read AGENTS.md fully — extract spec for all 9 agents
STEP 1.2: Read server/agent_loop.py — understand current agent execution pattern
STEP 1.3: Read server/model_router.py — understand how LLM calls are made
STEP 1.4: Read server/bridge.py — find existing /agent endpoint or Telegram routing
STEP 1.5: Read hey_jarvis.py — find TTS function signature for voice hook
STEP 1.6: Check server/agents/canonical/ — does it exist? If yes, what is there?
STEP 1.7: Check tests/ for existing agent tests

CREATE PLANNING ARTIFACTS:

  OPS/300_AGENTS_AUDIT.md
    - AGENTS.md spec summary per agent
    - What already exists in server/agents/
    - Gap per agent: missing implementation
    - bridge.py current /agent routing state

  OPS/301_AGENTS_IMPLEMENTATION_PLAN.md
    - Base class design (SubAgent pattern)
    - Per-agent: file path, run() signature, LLM prompt strategy
    - Voice hook design (VoiceNarratorAgent -> hey_jarvis.py)
    - Bridge routing design (/agent endpoint + keyword map)
    - Test strategy per agent

  OPS/302_AGENTS_ROLLOUT_PLAN.md
    - Batch 1: Core agents (Planner, RepoAnalyst, Developer)
    - Batch 2: Review/Debug agents (Reviewer, DebugAgent)
    - Batch 3: Output agents (Release, Docs, VoiceNarrator)
    - Batch 4: Control (MissionControl) + bridge routing + voice hook

After OPS/ artifacts: SWITCH TO BUILD MODE.

================================================================================
PHASE 2 — BUILD MODE
================================================================================

---  BASE CLASS: server/agents/canonical/__init__.py + base.py  ---

  Base class CanonicalAgent:
    agent_id: str           (matches AGENTS.md ID)
    name: str
    role: str
    model_preference: str   (from config, default "groq/llama-3.3-70b")

    async def run(task: str, context: dict = {}) -> dict:
      Returns: {agent_id, output, status: ok|error, timestamp}
      All LLM calls go through server/model_router.py

    def _call_llm(prompt: str, system: str, max_tokens: int) -> str:
      Uses model_router — never calls API directly

    def _log_result(result: dict):
      Appends to server/logs/canonical_agents.jsonl
      NEVER logs API keys or sensitive context fields

  Commit: "feat: CanonicalAgent base class in server/agents/canonical/"
  CLAUDE.md update.

---  BATCH 1: PlannerAgent, RepoAnalystAgent, DeveloperAgent  ---

  server/agents/canonical/planner.py
    PlannerAgent(CanonicalAgent)
    agent_id = "planner"
    run(task, context) -> structured plan dict:
      {goals, agents_needed, steps, estimated_complexity, priority}
    LLM prompt: structured JSON output, Türkçe description
    Uses: model_router Groq/Gemini

  server/agents/canonical/repo_analyst.py
    RepoAnalystAgent(CanonicalAgent)
    agent_id = "repo_analyst"
    run(task, context) -> repo health dict:
      {recent_commits, changed_files, health_score, warnings, recommendations}
    Uses: subprocess git log, git diff --stat (read-only)
    Never writes to repo

  server/agents/canonical/developer.py
    DeveloperAgent(CanonicalAgent)
    agent_id = "developer"
    run(task, context) -> implementation result:
      {files_changed, description, status}
    Strategy: generate code via LLM, write to specific target files
    Context must include: target_file, change_description
    Safety: only writes to files explicitly in context["target_file"]

  Add: tests/test_canonical_batch1.py
  Commit: "feat: PlannerAgent, RepoAnalystAgent, DeveloperAgent"
  CLAUDE.md update.

---  BATCH 2: ReviewerAgent, DebugAgent  ---

  server/agents/canonical/reviewer.py
    ReviewerAgent(CanonicalAgent)
    agent_id = "reviewer"
    run(task, context) -> review report:
      {issues, suggestions, severity_counts, overall_verdict}
    Uses: git diff (read-only subprocess) + LLM analysis
    Never modifies code

  server/agents/canonical/debug_agent.py
    DebugAgent(CanonicalAgent)
    agent_id = "debug"
    run(task, context) -> root cause analysis:
      {error_type, likely_cause, affected_files, suggested_fix, confidence}
    Input: context["error_message"] or context["stack_trace"]
    Uses: LLM with error analysis prompt

  Add: tests/test_canonical_batch2.py
  Commit: "feat: ReviewerAgent, DebugAgent"
  CLAUDE.md update.

---  BATCH 3: ReleaseAgent, DocsAgent, VoiceNarratorAgent  ---

  server/agents/canonical/release_agent.py
    ReleaseAgent(CanonicalAgent)
    agent_id = "release"
    run(task, context) -> release info:
      {changelog_entries, suggested_version, breaking_changes, highlights}
    Uses: git log --oneline -20 (subprocess) + LLM
    Suggests semver bump based on commit types

  server/agents/canonical/docs_agent.py
    DocsAgent(CanonicalAgent)
    agent_id = "docs"
    run(task, context) -> documentation:
      {doc_type, content, target_file_suggestion}
    Input: context["code"] or context["command"] or context["description"]
    Generates markdown documentation

  server/agents/canonical/voice_narrator.py
    VoiceNarratorAgent(CanonicalAgent)
    agent_id = "voice_narrator"
    run(task, context) -> TTS-ready text:
      {tts_text, original_length, compressed_length}
    Input: any raw technical output
    Output: 2-3 Turkish sentences, max 200 chars, spoken-language style
    No jargon, no code blocks, no markdown in output

  Add: tests/test_canonical_batch3.py
  Commit: "feat: ReleaseAgent, DocsAgent, VoiceNarratorAgent"
  CLAUDE.md update.

---  BATCH 4: MissionControlAgent  ---

  server/agents/canonical/mission_control.py
    MissionControlAgent(CanonicalAgent)
    agent_id = "mission_control"
    run(task, context) -> system health report:
      {
        agents: {agent_id: status},
        stuck_tasks: [],
        last_activity_per_agent: {},
        overall_health: ok|degraded|critical,
        recommendations: []
      }
    Reads: server/logs/canonical_agents.jsonl for recent activity
    Detects stuck: agent with no activity > 10 min = stuck warning
    Detects failed: agent with 3+ consecutive errors = critical

  Add: tests/test_canonical_batch4.py
  Commit: "feat: MissionControlAgent"
  CLAUDE.md update.

---  BRIDGE ROUTING: POST /agent endpoint  ---

  Read server/bridge.py fully.
  Add POST /agent endpoint (if not exists, backward-safe):

    POST /agent
    Body: {agent: "planner", task: "...", context: {...}}
    Response: canonical agent run() output as JSON

    Handler:
      from agents.canonical import CANONICAL_AGENTS
      agent = CANONICAL_AGENTS.get(body["agent"])
      if not agent: return 404
      result = asyncio.run(agent.run(body["task"], body.get("context", {})))
      return 200, result

  AGENT_KEYWORDS for Telegram auto-routing:
    "planner":       ["plan yap", "hedef", "gorev olustur", "ne yapayim"]
    "repo_analyst":  ["repo analiz", "saglik raporu", "git durum", "kod durumu"]
    "developer":     ["kod yaz", "implement", "feature ekle", "degistir"]
    "reviewer":      ["review", "incele", "pr kontrol", "kod incele"]
    "debug":         ["hata", "debug", "neden calısmiyor", "fix"]
    "release":       ["release", "changelog", "versiyon", "ne degisti"]
    "docs":          ["dokumantasyon", "readme guncelle", "acikla"]
    "mission_control": ["sistem durumu", "agent saglik", "ne calisiyor"]
    "voice_narrator": []  # internal only

  Add Telegram routing: if message matches keyword -> dispatch to agent -> TTS if available

  Commit: "feat: /agent endpoint + keyword routing in bridge.py"
  CLAUDE.md update.

---  VOICE HOOK: VoiceNarrator -> hey_jarvis.py  ---

  Read hey_jarvis.py — find TTS function (likely tts_speak or piper_speak).
  After any command produces output, pipe to VoiceNarratorAgent:

    # Add to hey_jarvis.py
    from server.agents.canonical.voice_narrator import VoiceNarratorAgent

    _narrator = VoiceNarratorAgent()

    async def speak_agent_result(raw_output: str):
        result = await _narrator.run(raw_output, {})
        tts_text = result.get("tts_text", raw_output[:200])
        await tts_speak(tts_text)  # existing TTS function

  Add: import guard (try/except ImportError) — if narrator fails, fallback to raw output[:200]
  Commit: "feat: VoiceNarratorAgent hook in hey_jarvis.py"
  CLAUDE.md update.

---  FINAL: Integration test + handoff  ---

  Run:
    python -m pytest tests/test_canonical_batch1.py \
      tests/test_canonical_batch2.py \
      tests/test_canonical_batch3.py \
      tests/test_canonical_batch4.py \
      -v --tb=short

  Run smoke test:
    python -c "
    import sys, asyncio
    sys.path.insert(0, '.')
    from server.agents.canonical import CANONICAL_AGENTS
    print('Registered agents:', list(CANONICAL_AGENTS.keys()))
    assert len(CANONICAL_AGENTS) == 9, f'Expected 9, got {len(CANONICAL_AGENTS)}'
    async def test():
        planner = CANONICAL_AGENTS['planner']
        r = await planner.run('Jarvis sistemini test et', {})
        print('Planner result status:', r['status'])
        narrator = CANONICAL_AGENTS['voice_narrator']
        r2 = await narrator.run('Test sonucu: 5 ajan calisiyor, 1 hata', {})
        print('Narrator TTS:', r2['tts_text'])
        mc = CANONICAL_AGENTS['mission_control']
        r3 = await mc.run('sistem durumu', {})
        print('MissionControl health:', r3['overall_health'])
    asyncio.run(test())
    print('ALL SMOKE TESTS PASSED')
    "

  Bridge smoke:
    curl -s -X POST http://localhost:8081/agent \
      -H Content-Type:application/json \
      -d '{\"agent\":\"planner\",\"task\":\"Jarvis durumunu raporla\"}' | python -m json.tool

  Write OPS/308_HANDOFF.md:
    - 9 agents: list, file, method signature
    - bridge /agent endpoint: request/response format
    - Telegram keyword routing table
    - Voice hook: how to test
    - How to add a new canonical agent
    - Known limitations

  Final CLAUDE.md update:
    ### AGENTS.md 9-Agent Canonical (Tab-3 Codex Sprint)
    - Durum: TAMAMLANDI
    - Ajanlar: planner, repo_analyst, developer, reviewer, debug, release, docs, voice_narrator, mission_control
    - Bridge: POST /agent endpoint aktif
    - Voice: VoiceNarrator hook hey_jarvis.py icinde
    - Tests: pytest N passed
    - Handoff: OPS/308_HANDOFF.md

  Final commit: "feat: AGENTS.md 9-agent canonical implementation — bridge routing + voice hook"

================================================================================
ANTI-HALLUCINATION RULES
================================================================================

- Do NOT rename or merge the 9 AGENTS.md canonical agents
- Do NOT confuse canonical agents with swarm clone agents (seda/mert/etc)
- Do NOT call LLM APIs directly — always use model_router.py
- Do NOT expose API keys
- Do NOT modify swarm clone agents (server/agents/clones/)
- Do NOT break existing bridge.py endpoints
- Do NOT claim success without passing tests
- Do NOT add npm/pip packages not already present

================================================================================
GO. READ AGENTS.MD. PLAN. EXECUTE. TEST. COMMIT. UPDATE CLAUDE.MD. HANDOFF.
================================================================================
"""

# Write files
out2 = DESKTOP / "CODEX_TAB2_MULTI_ACCOUNT.txt"
out3 = DESKTOP / "CODEX_TAB3_AGENTS_CANONICAL.txt"

out2.write_text(TAB2, encoding="utf-8")
out3.write_text(TAB3, encoding="utf-8")

print(f"Tab2: {out2} — {len(TAB2.splitlines())} lines")
print(f"Tab3: {out3} — {len(TAB3.splitlines())} lines")
print("DONE")
