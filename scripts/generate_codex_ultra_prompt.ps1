$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$opsDir = Join-Path $root 'OPS'
$outFile = Join-Path $opsDir 'CODEX_3H_ULTRA_PROMPT.txt'

New-Item -ItemType Directory -Path $opsDir -Force | Out-Null

$lines = New-Object 'System.Collections.Generic.List[string]'

function Add([string]$text) {
    $script:lines.Add($text) | Out-Null
}

function Add-Header([string]$title) {
    Add ('=' * 78)
    Add $title
    Add ('=' * 78)
}

Add-Header 'CODEX ULTRA 3-HOUR JARVIS WAR-ROOM PROMPT'
Add 'You are Codex operating inside C:\Users\sergen\Desktop\jarvis-mission-control.'
Add 'You must use the entire current Codex conversation history as evidence.'
Add 'You must not ask the user to repost logs, history, outputs, or summaries.'
Add 'You must continue from the real current state rather than restarting from scratch.'
Add 'You must behave like a lead operator in a 3-hour war-room sprint.'
Add 'You must use 8 total work lanes including the main orchestrator lane.'
Add 'You must discover and use Jarvis-local Codex subagents where available.'
Add 'You must create a deeply operational roadmap and execute against it.'
Add 'You must not hallucinate, inflate status, or trust unsupported claims.'
Add 'You must not expose secrets, tokens, passwords, API keys, or credentials.'
Add 'You must not push, force-push, reset hard, or delete unrelated work.'
Add 'You must not produce a shallow summary and stop.'
Add 'You must not report success before all gates are closed or hard-blocked with evidence.'
Add 'The final roadmap artifact must be operationally dense, not padded filler.'
Add 'The output language for human-facing artifacts should be Turkish unless code or commands require English.'
Add 'Inline code, commands, file paths, model IDs, JSON keys, and shell snippets should remain in English.'
Add 'Assume the user wants execution, not brainstorming.'
Add 'Assume the user wants continuity with the prior Claude/Codex work.'
Add 'Assume the user cares about truth over optics.'
Add 'Assume the user will distrust unsupported completion claims.'
Add 'Your job is to replace noise with a verified operational picture.'
Add 'Primary mission part A: perform a forensic audit of the last 24 hours using repo evidence plus session evidence.'
Add 'Primary mission part B: execute a 3-hour stabilization and integration sprint based on that audit.'
Add 'Primary mission part C: leave behind a 3000-4000 line roadmap that another operator can execute without losing context.'
Add 'You are not allowed to collapse this into a generic project plan.'
Add 'You are not allowed to ignore the OpenClaw and Telegram lane.'
Add 'You are not allowed to ignore runtime drift between orchestrator, bridge, launcher, and autonomous loop.'
Add 'You are not allowed to ignore subagent discovery.'
Add 'You are not allowed to trust README or completion reports above logs and code.'
Add 'You are not allowed to treat py_compile success as production readiness.'
Add 'You are not allowed to treat a passing message send as full conversational readiness.'
Add 'You are not allowed to treat one profile working as proof that all profiles work.'
Add 'You are not allowed to treat one commit summary as proof of end-to-end functionality.'
Add 'You must write all major findings to files under OPS/ so context compaction or rate limits do not destroy progress.'
Add 'You must checkpoint every 15-20 minutes of meaningful work.'
Add 'You must separate truth from narrative.'
Add 'You must separate code that exists from code that is actually wired into runtime.'
Add 'You must separate tests that exist from tests that cover real runtime paths.'
Add 'You must separate completed work from claimed work.'
Add 'You must explicitly mark confidence levels.'
Add 'You must classify major claims as VERIFIED, MOSTLY VERIFIED, PARTIAL, CONTRADICTED, or UNVERIFIED.'
Add 'You must prefer small correct improvements over large speculative rewrites.'
Add 'You must preserve user work and unrelated diffs.'
Add 'You must not hide brokenness behind roadmap language.'
Add 'You must not use marketing words like production-ready unless the evidence truly supports them.'
Add 'You must be able to defend every important statement with a file, command, log, test, or status output.'

Add-Header 'MANDATORY OUTPUT ARTIFACTS'
$artifactSpecs = @(
    @{File='OPS/00_LAST24_FACT_AUDIT.md'; Purpose='evidence-backed truth map of the last 24 hours'; Key='facts, timestamps, evidence, confidence, contradictions'},
    @{File='OPS/00_SUBAGENT_MAP.md'; Purpose='mapping of 8-agent topology to local subagents or simulated lanes'; Key='lane id, source, role, mode, deliverables'},
    @{File='OPS/01_3H_ULTRA_ROADMAP.md'; Purpose='3000-4000 line operational roadmap'; Key='phases, commands, owners, checks, fallbacks'},
    @{File='OPS/02_EXECUTION_RUNLOG.md'; Purpose='chronological execution log'; Key='timestamps, actions, outputs, blockers, decisions'},
    @{File='OPS/03_CLAIMS_VS_REALITY.md'; Purpose='claim verification matrix'; Key='claim, evidence, status, confidence, next step'},
    @{File='OPS/04_RUNTIME_CANON.md'; Purpose='single authoritative runtime map'; Key='entrypoints, ports, owners, dependencies, limitations'},
    @{File='OPS/05_OPENCLAW_TELEGRAM_STATE.md'; Purpose='OpenClaw and Telegram exact state'; Key='profiles, pairing, channels, model auth, delivery path'},
    @{File='OPS/06_NEXT_3H_HANDOFF.md'; Purpose='next shift handoff'; Key='resume point, first commands, blockers, validation path'}
)
foreach ($artifact in $artifactSpecs) {
    Add "Artifact file: $($artifact.File)"
    Add "Purpose: $($artifact.Purpose)"
    Add "Must include: $($artifact.Key)"
    Add 'Must redact secrets and tokens.'
    Add 'Must be written during the run, not retrofitted only at the end.'
    Add 'Must be updated whenever a major finding changes the operating picture.'
}

Add-Header 'FIVE GATES THAT MUST BE CLOSED'
$gates = @(
    'Gate 1: Last-24h audit complete',
    'Gate 2: Canonical runtime map complete',
    'Gate 3: OpenClaw and Telegram delivery truth resolved',
    'Gate 4: Persistence and recovery review complete',
    'Gate 5: Docs, tests, and handoff aligned'
)
foreach ($gate in $gates) {
    Add $gate
    Add 'Do not mark this gate complete without direct evidence.'
    Add 'If blocked, record exact blocker, evidence, and next step.'
    Add 'If partially complete, do not collapse it into done.'
    Add 'Every gate must be represented in OPS/01_3H_ULTRA_ROADMAP.md and OPS/02_EXECUTION_RUNLOG.md.'
}

Add-Header 'SOURCE OF TRUTH HIERARCHY'
$truthHierarchy = @(
    'Level 1: live runtime evidence such as processes, ports, health endpoints, logs, status screens, sent messages, and actual failures',
    'Level 2: current code paths, imports, config loading, startup logic, queue logic, memory logic, model routing logic, and tests',
    'Level 3: git evidence such as current branch, diffs, recent commits, recent file changes, and file timestamps',
    'Level 4: current Codex session history including prior analyses, prior claims, terminal outputs, and agent reports',
    'Level 5: documentation and generated reports such as README, AGENTS.md, WEEK reports, and summary files'
)
foreach ($item in $truthHierarchy) {
    Add $item
    Add 'If two levels conflict, trust the higher level.'
    Add 'If runtime and docs conflict, docs are wrong until updated.'
    Add 'If code exists but no runtime path reaches it, classify it as code-present not runtime-proven.'
}

Add-Header 'NON-NEGOTIABLE EXECUTION RULES'
$rules = @(
    'Use the full existing conversation history in this Codex session as evidence.',
    'Do not ask the user to repost the past 24 hours of logs or analysis.',
    'Do not assume Week 3 completion reports are accurate without verification.',
    'Do not assume OpenClaw dev profile and main profile behave the same.',
    'Do not assume Telegram direct send equals agent reply readiness.',
    'Do not assume master launcher ownership boundaries are fixed unless verified.',
    'Do not assume queue persistence is correct unless restart behavior is verified.',
    'Do not assume self-healer is Windows-safe unless generated commands are inspected.',
    'Do not assume bridge memory is cross-platform unless the actual path logic proves it.',
    'Do not assume docs drift is solved until README, AGENTS.md, and env examples align to code.',
    'Prefer targeted tests and targeted commands over wide expensive sweeps.',
    'Use small correct changes and verify them immediately.',
    'Record every meaningful finding in OPS artifacts so context compaction does not erase it.',
    'Use local subagents if available; simulate them explicitly if not.',
    'Maintain 8 total lanes including the main lead lane.',
    'If you simulate a lane, say so in OPS/00_SUBAGENT_MAP.md and OPS/02_EXECUTION_RUNLOG.md.',
    'Never print secrets in the roadmap, run log, audit, or final summary.',
    'If a command output contains a secret, redact it before persisting it in artifacts.',
    'If a profile or model is broken, say it is broken.',
    'If a feature is half-wired, call it half-wired, not nearly done.',
    'If a test suite is absent, say absent.',
    'If pytest is missing, do not fake pytest coverage.',
    'If only py_compile passed, say syntax-only validation.',
    'If a generated report contradicts runtime evidence, explicitly mark the contradiction.',
    'If the user requested a 3-hour uninterrupted run, structure your work to survive rate limits and context compaction.'
)
foreach ($rule in $rules) {
    Add "Rule: $rule"
}

Add-Header '8-AGENT TOPOLOGY'
$lanes = @(
    @{Id='L0'; Name='Main Lead Orchestrator'; Source='Codex main agent'; Goal='Own final truth, integration direction, and gate closure'; Deliverables='all OPS artifacts, final synthesis'},
    @{Id='L1'; Name='Evidence Miner'; Source='local search-specialist or equivalent'; Goal='Mine session history, logs, commits, and status outputs'; Deliverables='fact inventory, contradiction seeds'},
    @{Id='L2'; Name='Topology Mapper'; Source='local code-mapper or equivalent'; Goal='Map runtime ownership, entrypoints, ports, queues, dependencies'; Deliverables='runtime canon inputs'},
    @{Id='L3'; Name='Backend Integrator'; Source='local backend-developer or equivalent'; Goal='Make minimal runtime and persistence fixes'; Deliverables='targeted code patches'},
    @{Id='L4'; Name='Debugger'; Source='local debugger or equivalent'; Goal='Reproduce and classify launcher, OpenClaw, Telegram, and model failures'; Deliverables='failure tree, repro commands'},
    @{Id='L5'; Name='AI Runtime Integrator'; Source='local ai-engineer or equivalent'; Goal='Resolve OpenClaw profile, model, auth, and delivery confusion'; Deliverables='OpenClaw/Telegram state doc'},
    @{Id='L6'; Name='Docs Reconciler'; Source='local documentation-engineer or equivalent'; Goal='Align README, AGENTS, env examples, and handoff docs to reality'; Deliverables='doc updates, reconciliation notes'},
    @{Id='L7'; Name='Adversarial Reviewer'; Source='local reviewer or equivalent'; Goal='Challenge weak evidence, inflated claims, and hidden drift'; Deliverables='claims-vs-reality challenges, residual risks'}
)
foreach ($lane in $lanes) {
    Add "Lane ID: $($lane.Id)"
    Add "Lane Name: $($lane.Name)"
    Add "Lane Source: $($lane.Source)"
    Add "Lane Goal: $($lane.Goal)"
    Add "Lane Deliverables: $($lane.Deliverables)"
    Add 'Lane Input Discipline: use only repo evidence and current conversation history.'
    Add 'Lane Output Discipline: every claim must attach to a file, command, log, test, commit, or status output.'
    Add 'Lane Handoff Rule: update OPS/02_EXECUTION_RUNLOG.md after each meaningful discovery.'
    Add 'Lane Anti-Overlap Rule: avoid duplicate analysis; if overlap happens, consolidate and cite the stronger evidence.'
    Add 'Lane Escalation Rule: if a contradiction affects a major claim or runtime recommendation, escalate to L0 immediately.'
    Add 'Lane Stop Condition: only stop when assigned checks are complete, blocked with proof, or superseded by stronger evidence.'
    Add 'Lane Redaction Rule: do not persist secrets.'
    Add 'Lane Verification Rule: a green status line is not sufficient without contextual meaning.'
    Add 'Lane Confidence Rule: state low, medium, or high confidence for major conclusions.'
    Add 'Lane Failure Mode 1: missing files or mismatched docs.'
    Add 'Lane Failure Mode 2: runtime path exists but is not canonical.'
    Add 'Lane Failure Mode 3: model or auth path is configured but unusable.'
    Add 'Lane Failure Mode 4: claimed completion is not supported by runtime evidence.'
    Add 'Lane Failure Mode 5: lane blocked by missing dependency or external auth.'
    Add 'Lane Required Artifact Update: at least one OPS file per meaningful lane output.'
    Add 'Lane Summary Template: what was checked, what was found, what remains uncertain, what changed.'
    Add 'Lane Evidence Template: exact command or file path plus the line or behavior that matters.'
    Add 'Lane Risk Template: classify resulting risk as high, medium, or low.'
    Add 'Lane Recovery Template: if interrupted, note exact next command and file to reopen.'
}

Add-Header 'SUBAGENT DISCOVERY DIRECTIVE'
$subagentTargets = @(
    '.codex/agents/',
    'tools/subagents/',
    'tools/subagents/README.md',
    'tools/subagents/jarvis-subagent-shortcuts.ps1',
    'docs/SUBAGENT_MAPPING.md',
    'external-repos/awesome-codex-subagents/',
    'server/config/agent_manifests.json',
    'AGENTS.md',
    'CLAUDE.md if present',
    'any Codex or Claude adapter docs in external-repos or docs/'
)
foreach ($target in $subagentTargets) {
    Add "Inspect subagent target: $target"
    Add 'Determine whether it contains executable subagents, prompt generators, or only reference docs.'
    Add 'Record whether the lane is truly executable or simulated.'
}

Add-Header 'LAST 24 HOURS CLAIM SET TO VERIFY'
$claims = @(
    'Week 3 is complete',
    'All five CALEB agents delivered',
    '117/117 tests passing',
    'Production ready',
    '24/7 autonomous operation active',
    'Claude Code integration complete',
    'Codex background agents completed their work',
    'Monitoring dashboard is real-time and usable',
    'Telegram intelligence is operational',
    'Gemini function calling is integrated',
    'Advanced learning rules are active',
    'Bridge is the canonical runtime',
    'FastAPI orchestrator is the canonical runtime',
    'Autonomous loop is real and usable',
    'Launcher behavior is fixed',
    'Queue persistence is real',
    'Queue priority is real not cosmetic',
    'Confirm flow is safe',
    'Memory is cross-platform',
    'Self-healer is Windows-safe',
    'README now matches runtime',
    'AGENTS.md now matches runtime',
    'OpenClaw dev profile Telegram is working',
    'OpenClaw agent delivery works end-to-end',
    'OpenClaw direct send works',
    'OpenClaw profile split is understood',
    'Main profile is more stable than dev',
    'Dev profile is the right place to continue',
    'Subagents are available and usable',
    'Local Codex subagent shortcuts are real execution tools',
    'Week 3 completion report is trustworthy',
    'Generated scan files are useful evidence',
    'Bridge memory is enabled and reliable',
    'Runtime state is unified',
    'System is not merely a pile of scripts',
    'There is one canonical path for Telegram operations',
    'There is one canonical path for task orchestration',
    'There is one canonical path for autonomous improvement',
    'OpenClaw model configuration is coherent',
    'OpenClaw auth configuration is coherent',
    'Jarvis can answer from Telegram reliably',
    'Launcher no longer creates orphaned processes',
    'Docs drift is under control',
    'Tests cover the important runtime risks',
    'Residual risks are understood',
    'The system can survive the next 24 hours with low operator intervention'
)
foreach ($claim in $claims) {
    Add "Claim under test: $claim"
    Add 'Locate the exact statement in session history, docs, reports, commits, or chat outputs.'
    Add 'Find the strongest runtime evidence that supports or weakens it.'
    Add 'Find the strongest code evidence that supports or weakens it.'
    Add 'Find the strongest test evidence that supports or weakens it.'
    Add 'Classify the claim as VERIFIED, MOSTLY VERIFIED, PARTIAL, CONTRADICTED, or UNVERIFIED.'
    Add 'Record the confidence level and the next verification or fix action.'
}

Add-Header 'EVIDENCE INVENTORY TEMPLATE'
$evidenceSources = @(
    'git status',
    'git diff for touched files',
    'git log recent commits',
    'master_launcher.py',
    'server/watchdog.py',
    'server/bridge.py',
    'server/bridge_server.py',
    'server/runtime_config.py',
    'server/runtime_state.py',
    'server/model_router.py',
    'server/autonomous_loop.py',
    'services/orchestrator/main.py',
    'services/orchestrator/task_queue.py',
    'services/orchestrator/agent_runner.py',
    'services/orchestrator/safety.py',
    'server/skills/memory_skill.py',
    'server/agents/self_healer.py',
    'server/agents/self_learning_agent.py',
    'server/monitoring/learning_integration.py',
    'server/telegram/telegram_intelligence.py',
    'README.md',
    'AGENTS.md',
    '.env.example',
    'WEEK2_PROGRESS.md',
    'WEEK3_ROADMAP.md',
    'WEEK3_COMPLETION.md',
    'INTEGRATION_SUMMARY.md',
    '01_structure.txt',
    '02_depth2.txt',
    '03_critical_files.txt',
    '04_system_map.txt',
    '05_imports.txt',
    '06_js_imports.txt',
    '07_env_usage.txt',
    '08_todos.txt',
    'OpenClaw status outputs in current session',
    'Telegram direct send output in current session',
    'OpenClaw agent failure output in current session',
    'launcher logs in current session',
    'bridge heartbeat and lock files if present'
)
foreach ($source in $evidenceSources) {
    Add "Evidence source: $source"
    Add 'What this source can prove: ownership, wiring, runtime truth, test coverage, or documentation drift.'
    Add 'What this source cannot prove by itself: end-to-end reliability without corroboration.'
    Add 'How to use it: inspect directly, cross-reference with logs, compare with claims, and record confidence.'
    Add 'What to redact: secrets, tokens, personal identifiers unless operationally necessary and then partially masked.'
    Add 'What artifact to update after inspection: run log, fact audit, claims-vs-reality, runtime canon, or roadmap.'
}

Add-Header 'SUBSYSTEM AUDIT DIRECTIVES'
$subsystems = @(
    'Master launcher ownership and lifecycle',
    'Watchdog behavior and bridge boot policy',
    'Bridge lock and heartbeat behavior',
    'Bridge web runtime and endpoint surface',
    'Bridge agent runner startup ownership',
    'Bridge OpenCode serve startup ownership',
    'Bridge gateway startup ownership',
    'FastAPI orchestrator entrypoint and health surface',
    'Task queue persistence and priority behavior',
    'Task confirm flow correctness',
    'Agent runner retry and failure behavior',
    'Safety policy and confirmation boundaries',
    'Runtime state JSON persistence',
    'SQLite memory pathing and portability',
    'Self-healer fix generation on Windows vs POSIX',
    'Learning integration and improvement logic',
    'Monitoring dashboard reality vs claims',
    'Telegram intelligence reality vs claims',
    'Autonomous loop reality and usability',
    'OpenClaw main profile',
    'OpenClaw dev profile',
    'OpenClaw pairing state',
    'OpenClaw model and auth state',
    'OpenClaw direct Telegram delivery path',
    'OpenClaw agent-generated Telegram delivery path',
    'Subagent inventory and usability',
    'Documentation drift between README, AGENTS, env examples, and code',
    'Week reports and generated summaries as evidence quality',
    'Test coverage quality for recent critical changes',
    'Canonical runtime recommendation after audit'
)
foreach ($subsystem in $subsystems) {
    Add "Subsystem: $subsystem"
    Add 'Identify the canonical entrypoint.'
    Add 'Identify all competing or duplicate entrypoints.'
    Add 'Identify the default port, file path, process owner, or storage path if applicable.'
    Add 'Identify the exact startup command.'
    Add 'Identify whether this subsystem is runtime-critical, optional, experimental, or docs-only.'
    Add 'Identify the strongest evidence that it currently works.'
    Add 'Identify the strongest evidence that it currently fails or drifts.'
    Add 'Identify whether the current docs describe it accurately.'
    Add 'Identify whether tests cover it meaningfully.'
    Add 'Identify whether the last-24h claims about it are inflated.'
    Add 'Identify the minimum fix if needed.'
    Add 'Identify the medium structural fix if needed.'
    Add 'Identify the explicit stop condition for this lane.'
    Add 'Record the result in OPS/00_LAST24_FACT_AUDIT.md.'
    Add 'Record the claim status in OPS/03_CLAIMS_VS_REALITY.md.'
    Add 'Record the runtime placement in OPS/04_RUNTIME_CANON.md.'
    Add 'If code changes are required, link the exact file and validation plan.'
}

Add-Header '3-HOUR MACRO PLAN'
$macroBlocks = @(
    @{Window='0-30 minutes'; Goal='Bootstrapping, repo truth setup, and lane assignment'},
    @{Window='30-60 minutes'; Goal='Forensic audit of the last 24 hours'},
    @{Window='60-90 minutes'; Goal='Runtime topology and ownership reconciliation'},
    @{Window='90-120 minutes'; Goal='OpenClaw and Telegram stabilization lane'},
    @{Window='120-150 minutes'; Goal='Persistence, memory, self-heal, and platform compatibility review'},
    @{Window='150-180 minutes'; Goal='Docs, tests, adversarial review, handoff, and final synthesis'}
)
foreach ($block in $macroBlocks) {
    Add "Macro block: $($block.Window)"
    Add "Goal: $($block.Goal)"
    Add 'Primary owners: L0 plus one or more specialist lanes.'
    Add 'Mandatory artifact updates: roadmap, run log, and any affected thematic OPS files.'
    Add 'Mandatory output: evidence-backed decisions, not just observations.'
    Add 'Mandatory failure handling: if blocked, record blocker and switch to the next highest ROI lane without losing context.'
    Add 'Mandatory end-state: clear checkpoint line in OPS/02_EXECUTION_RUNLOG.md.'
}

Add-Header '12 MICRO SEGMENTS OF 15 MINUTES EACH'
$segments = @(
    @{Id='S01'; Window='0-15'; Focus='Initialize OPS files, repo state, and subagent discovery'},
    @{Id='S02'; Window='15-30'; Focus='Map session claims and recent repo changes'},
    @{Id='S03'; Window='30-45'; Focus='Build claims-vs-reality matrix'},
    @{Id='S04'; Window='45-60'; Focus='Map runtime ownership and duplicated startup paths'},
    @{Id='S05'; Window='60-75'; Focus='Validate launcher, bridge, orchestrator, and autonomous loop boundaries'},
    @{Id='S06'; Window='75-90'; Focus='Audit OpenClaw profiles, pairing, and Telegram direct delivery'},
    @{Id='S07'; Window='90-105'; Focus='Audit OpenClaw model/auth and agent delivery path'},
    @{Id='S08'; Window='105-120'; Focus='Resolve or hard-block OpenClaw canonical usage path'},
    @{Id='S09'; Window='120-135'; Focus='Review queue persistence, confirm flow, and memory portability'},
    @{Id='S10'; Window='135-150'; Focus='Review self-healer, restart behavior, and platform safety'},
    @{Id='S11'; Window='150-165'; Focus='Reconcile docs and run targeted validations'},
    @{Id='S12'; Window='165-180'; Focus='Adversarial review, final gate closure, and handoff'}
)
foreach ($segment in $segments) {
    Add "Segment: $($segment.Id)"
    Add "Time window: $($segment.Window) minutes"
    Add "Focus: $($segment.Focus)"
    Add 'Step 1: state the exact lane owner or owners.'
    Add 'Step 2: list the exact files or commands to inspect.'
    Add 'Step 3: define the precise success condition.'
    Add 'Step 4: define the most likely blocker.'
    Add 'Step 5: define the fallback path if blocked.'
    Add 'Step 6: define the exact OPS artifact to update.'
    Add 'Step 7: define the confidence required before moving on.'
    Add 'Step 8: define what not to over-claim in this segment.'
    Add 'Step 9: define whether code change is allowed in this segment.'
    Add 'Step 10: define whether a restart is allowed in this segment.'
    Add 'Step 11: define which runtime or profile boundary matters in this segment.'
    Add 'Step 12: define which contradictory report from the prior 24h must be challenged here.'
    Add 'Step 13: define what evidence must be collected before calling the segment complete.'
    Add 'Step 14: define the exact run log entry to append at segment end.'
    Add 'Step 15: define the handoff note required if context compaction interrupts work.'
    Add 'Detailed objective A: identify what is known before this segment starts.'
    Add 'Detailed objective B: identify what remains unknown.'
    Add 'Detailed objective C: reduce one major ambiguity.'
    Add 'Detailed objective D: improve one high-value artifact.'
    Add 'Detailed objective E: leave behind at least one reusable finding.'
    Add 'Evidence requirement A: at least one direct command output or log snippet.'
    Add 'Evidence requirement B: at least one direct code reference if the segment concerns runtime behavior.'
    Add 'Evidence requirement C: at least one claim classification update if the segment addresses a report or claim.'
    Add 'Risk note A: do not broaden scope past the current segment without recording why.'
    Add 'Risk note B: do not conflate profile-specific success with global success.'
    Add 'Risk note C: do not mark code as live if no live path reaches it.'
    Add 'Validation target A: syntax or import checks if code changes occur.'
    Add 'Validation target B: targeted runtime check if startup or delivery behavior changes.'
    Add 'Validation target C: docs diff if documentation changes occur.'
    Add 'Artifact update A: append run log timestamp, what changed, why, and the confidence.'
    Add 'Artifact update B: if the segment changes the canonical runtime story, update OPS/04_RUNTIME_CANON.md immediately.'
    Add 'Artifact update C: if the segment resolves or deepens a contradiction, update OPS/03_CLAIMS_VS_REALITY.md immediately.'
    Add 'Escalation trigger A: hidden secret appears in output; redact before persisting.'
    Add 'Escalation trigger B: a claim previously marked done becomes contradicted by runtime evidence.'
    Add 'Escalation trigger C: a change risks breaking the user’s current working path.'
    Add 'Stop condition A: success condition met with evidence.'
    Add 'Stop condition B: blocker recorded with proof and next action defined.'
    Add 'Stop condition C: segment time budget exhausted and a checkpoint is written.'
}

Add-Header 'OPENCLAW AND TELEGRAM MANDATORY DIRECTIVES'
$openclawChecks = @(
    'Determine whether the canonical operating path should be main profile, dev profile, split profile, or pause pending cleanup.',
    'Determine whether Telegram direct send works in dev profile.',
    'Determine whether Telegram direct send works in main profile.',
    'Determine whether pairing is complete for the user chat id.',
    'Determine whether unauthorized command messages were due to pairing, policy, or wrong profile.',
    'Determine whether agent-generated delivery works in dev profile.',
    'Determine whether agent-generated delivery works in main profile.',
    'Determine whether model auth is missing for anthropic in dev profile.',
    'Determine whether the configured dev model alias is recognized by the gateway runtime.',
    'Determine whether main profile model configuration is more stable than dev profile model configuration.',
    'Determine whether the recommended user workflow should explicitly use one profile only.',
    'Determine the exact minimum commands that reliably send a Telegram message.',
    'Determine the exact minimum commands that reliably generate and deliver an agent reply.',
    'Determine whether the libuv Windows assertion after Telegram send is cosmetic or destabilizing.',
    'Determine whether the gateway stays healthy after direct message send.',
    'Determine whether the gateway stays healthy after agent reply attempts.',
    'Determine whether OpenClaw auth profiles are inherited or isolated in the current profile layout.',
    'Determine whether any fix should be applied in repo docs to prevent user confusion between profiles.'
)
foreach ($check in $openclawChecks) {
    Add "OpenClaw directive: $check"
    Add 'Collect exact command evidence.'
    Add 'Collect exact status or log evidence.'
    Add 'Record exact recommendation in OPS/05_OPENCLAW_TELEGRAM_STATE.md.'
}

Add-Header 'PERSISTENCE, MEMORY, AND SELF-HEAL DIRECTIVES'
$stabilityChecks = @(
    'Verify task queue persistence file path and existence.',
    'Verify queued tasks survive restart.',
    'Verify running tasks are recovered sanely after restart.',
    'Verify confirm flow only revives awaiting tasks.',
    'Verify task priority changes the actual dequeue order.',
    'Verify queue size reporting reflects persisted queue reality.',
    'Verify bridge JSON runtime memory path.',
    'Verify SQLite long-term memory path is cross-platform.',
    'Verify memory imports do not break bridge on Windows.',
    'Verify hardcoded Linux-only paths are eliminated or quarantined.',
    'Verify self-healer missing-binary fixes on Windows do not use POSIX-only commands.',
    'Verify self-healer permission fixes on Windows do not use chmod.',
    'Verify self-healer port-in-use fixes on Windows do not use head or grep chains.',
    'Verify self-healer network check is platform-appropriate.',
    'Verify documentation reflects the actual queue and memory paths.',
    'Verify tests exist for queue, memory, and self-healer behavior if recent changes touched them.'
)
foreach ($check in $stabilityChecks) {
    Add "Stability directive: $check"
    Add 'If true, record proof.'
    Add 'If false, define minimum fix and verification path.'
    Add 'If partially true, document the boundary explicitly.'
}

Add-Header 'LAUNCHER AND OWNERSHIP DIRECTIVES'
$launcherChecks = @(
    'Verify whether master_launcher duplicates services already started by bridge or watchdog.',
    'Verify whether bridge itself starts gateway, OpenCode serve, and agent runners.',
    'Verify whether watchdog starts bridge.',
    'Verify whether launcher is monitoring wrapper shells or real child processes.',
    'Verify whether shutdown kills process trees or only wrappers.',
    'Verify whether repeated dead-component warnings are real or bookkeeping artifacts.',
    'Verify whether old child processes can survive shutdown and create port conflicts.',
    'Verify whether the current launcher fix is fully solved, partially solved, or still risky.',
    'Verify whether hologram or voice ownership is duplicated anywhere else.',
    'Verify whether bridge should be the only owner of gateway and agent runners.'
)
foreach ($check in $launcherChecks) {
    Add "Launcher directive: $check"
    Add 'Use code plus process evidence.'
    Add 'If corrected by prior changes, verify with runtime or at least with exact ownership code.'
    Add 'Record the canonical answer in OPS/04_RUNTIME_CANON.md.'
}

Add-Header 'DOCUMENTATION RECONCILIATION DIRECTIVES'
$docsChecks = @(
    'README runtime ports and entrypoints',
    'AGENTS.md architecture ports and ownership notes',
    '.env.example runtime variable naming',
    'OpenClaw usage notes if present',
    'subagent usage docs',
    'week completion reports vs actual runtime',
    'integration summary vs actual code wiring',
    'autonomous loop docs vs actual usability',
    'launcher docs vs actual ownership boundaries',
    'Telegram docs vs actual pairing and channel state'
)
foreach ($doc in $docsChecks) {
    Add "Documentation target: $doc"
    Add 'Determine whether the current docs are accurate, stale, inflated, or contradictory.'
    Add 'Update docs only after the runtime truth is known.'
    Add 'Prefer precision over hype.'
}

Add-Header 'RISK MATRIX INSTRUCTIONS'
$riskAreas = @(
    'launcher orphan processes',
    'bridge lock false conflicts',
    'duplicate service ownership',
    'queue data loss on restart',
    'priority queue cosmetic only',
    'memory path portability failure',
    'self-healer unsafe shell commands',
    'OpenClaw dev/main split confusion',
    'Telegram direct send only partial success',
    'agent delivery blocked by model auth',
    'broken model alias in dev profile',
    'reports overstating completion',
    'docs drift causing wrong operator actions',
    'tests not covering live runtime paths',
    'hidden secret exposure in logs or artifacts',
    'context compaction losing state',
    'rate limit interrupting the sprint',
    'non-canonical runtime advice',
    'bridge and orchestrator both treated as primary',
    'autonomous loop described as ready but not operator-safe',
    'OpenClaw pairing incomplete for command authorization',
    'hologram cache or file permission issues on Windows',
    'voice runtime not verified even if launched',
    'monitoring dashboard unverified beyond docs',
    'Week 3 tests not representing runtime success',
    'generated scan files being noisy rather than useful',
    'subagent shortcuts misread as real execution tools',
    'main profile and dev profile requiring separate operator guidance',
    'manual steps hidden behind status success messages',
    'operator confidence exceeding evidence quality'
)
foreach ($risk in $riskAreas) {
    Add "Risk area: $risk"
    Add 'Assign severity: high, medium, or low.'
    Add 'State what evidence proves the risk exists.'
    Add 'State what change or documentation lowers the risk.'
    Add 'State whether the risk can be reduced inside the 3-hour window.'
    Add 'If not reducible now, add it to OPS/06_NEXT_3H_HANDOFF.md.'
}

Add-Header 'ARTIFACT CONTENT BLUEPRINTS'
foreach ($artifact in $artifactSpecs) {
    Add "Blueprint for $($artifact.File)"
    Add 'Section A: purpose and scope.'
    Add 'Section B: evidence sources used.'
    Add 'Section C: key findings.'
    Add 'Section D: contradictions or caveats.'
    Add 'Section E: confidence level.'
    Add 'Section F: next required action.'
    Add 'Section G: last updated timestamp.'
    Add 'Every section must prefer short dense lines over broad prose.'
    Add 'Every section must remain understandable after context compaction.'
    Add 'Every section must avoid secret leakage.'
}

Add-Header 'DETAILED VERIFICATION APPENDIX'
$focusAreas = @(
    'master launcher startup sequence', 'watchdog bridge boot policy', 'bridge lock acquisition', 'bridge heartbeat persistence',
    'bridge gateway ownership', 'bridge opencode serve ownership', 'bridge agent runner ownership', 'bridge telegram startup',
    'bridge web server health endpoint', 'bridge runtime config loading', 'bridge model router wiring', 'orchestrator fastapi boot path',
    'orchestrator queue persistence file', 'orchestrator queue recovery on restart', 'orchestrator priority dequeue order', 'orchestrator confirm flow',
    'orchestrator websocket events', 'orchestrator safety confirmation boundary', 'agent runner retry loop', 'agent runner task state persistence',
    'runtime state json behavior', 'memory sqlite path', 'memory json path', 'memory import path stability',
    'self-healer missing binary command generation', 'self-healer module install fallback', 'self-healer permission fixes', 'self-healer network check',
    'self-healer port-in-use fix', 'learning integration trigger path', 'execution metrics collection', 'monitoring dashboard startup path',
    'telegram intelligence route path', 'week 3 dashboard claim', 'week 3 telegram claim', 'week 3 function calling claim',
    'week 3 advanced learning claim', 'week 3 test count claim', 'week 3 completion report credibility', 'integration summary credibility',
    'generated scan file usefulness', 'openclaw main profile gateway', 'openclaw dev profile gateway', 'openclaw pairing request state',
    'openclaw pairing approval state', 'openclaw telegram direct send', 'openclaw agent direct run', 'openclaw agent delivery',
    'openclaw model auth order', 'openclaw dev model alias validity', 'openclaw main model stability', 'openclaw logs evidence quality',
    'subagent inventory reality', 'subagent shortcut execution semantics', 'codex subagent repo availability', 'handoff survival artifacts',
    'docs drift in README', 'docs drift in AGENTS', 'docs drift in env example', 'canonical runtime recommendation'
)
$questions = @(
    'What is the exact file or command that defines this area?',
    'What does the live runtime evidence say about this area?',
    'What does the code say about this area?',
    'What does the most optimistic report claim about this area?',
    'What contradicts that optimistic claim?',
    'What is the current best classification for this area?',
    'What is the minimum safe next action for this area?',
    'What artifact must be updated when this area is resolved?',
    'What confidence level should be assigned to this area right now?',
    'What would falsely make this area look done when it is not?'
)
foreach ($area in $focusAreas) {
    Add "Focus area: $area"
    foreach ($question in $questions) {
        Add "Check: $question"
    }
}

Add-Header 'FINAL DELIVERY RULES'
$deliveryRules = @(
    'Do not finish with a vague summary.',
    'Do not say all good unless you can prove all good.',
    'Do not bury contradictions in footnotes.',
    'Do not hide blockers behind future work language.',
    'Do not give the user a roadmap without also executing meaningful parts of it.',
    'Do not claim production readiness unless runtime truth, tests, docs, and operator workflow all support it.',
    'Do not leave the next operator without exact resume commands.',
    'Do not leave the roadmap under 3000 lines.',
    'Do not exceed 4000 lines by adding useless padding.',
    'Do not ignore the existence of local Codex subagents or their shortcut layer.',
    'Do not skip writing OPS/00_SUBAGENT_MAP.md.',
    'Do not skip writing OPS/05_OPENCLAW_TELEGRAM_STATE.md.',
    'Do not skip classifying major claims.',
    'Do not skip adversarial review.',
    'Do not skip updating the run log during execution.',
    'Do not stop before the five gates are closed or hard-blocked.'
)
foreach ($rule in $deliveryRules) {
    Add "Final rule: $rule"
}

Add-Header 'BEGIN EXECUTION NOW'
Add 'Step 1: create or update the OPS artifact set immediately.'
Add 'Step 2: discover the local subagent inventory and map it to the 8 lanes.'
Add 'Step 3: mine the last 24 hours of session evidence and repo evidence.'
Add 'Step 4: classify major claims with evidence and confidence.'
Add 'Step 5: map runtime ownership and canonical entrypoints.'
Add 'Step 6: resolve or hard-block the OpenClaw and Telegram path.'
Add 'Step 7: review persistence, memory, self-healer, and launcher safety.'
Add 'Step 8: align docs, tests, and handoff artifacts.'
Add 'Step 9: complete the 3000-4000 line roadmap under OPS/01_3H_ULTRA_ROADMAP.md.'
Add 'Step 10: only then produce the final user-facing summary.'
Add 'Begin immediately.'

if ($lines.Count -lt 3900) {
    $appendixIndex = 1
    while ($lines.Count -lt 3900) {
        Add "Extended appendix item ${appendixIndex}: identify one specific assumption that could create a false-positive success signal and define how to invalidate it with direct evidence."
        Add "Extended appendix item ${appendixIndex}: identify one concrete command, file read, log probe, or targeted test that would reduce ambiguity for the current runtime story."
        Add "Extended appendix item ${appendixIndex}: identify one exact artifact line that must be updated if the assumption is disproved."
        Add "Extended appendix item ${appendixIndex}: classify the operational impact if this assumption remains unresolved for the next 24 hours."
        $appendixIndex++
    }
}

if ($lines.Count -gt 4000) {
    throw "Generated prompt is too large: $($lines.Count) lines"
}

$lines | Set-Content -Encoding utf8 $outFile
Write-Host "Generated: $outFile"
Write-Host "LineCount: $($lines.Count)"
