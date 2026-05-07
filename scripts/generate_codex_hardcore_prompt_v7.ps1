$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
$opsDir = Join-Path $root 'OPS'
$outFile = Join-Path $opsDir 'CODEX_5H_HARDCORE_PROMPT_V7_24K.txt'
$reportFile = Join-Path $opsDir '71_PROMPT_BUILD_CHECKPOINT_V7.md'
$targetLines = 24000

New-Item -ItemType Directory -Path $opsDir -Force | Out-Null

$lines = New-Object 'System.Collections.Generic.List[string]'

function Add([string]$text) {
    $script:lines.Add($text) | Out-Null
}

function AddBlock([string]$text) {
    foreach ($line in ($text -split "`r?`n")) {
        Add $line
    }
}

function AddHeader([string]$title) {
    Add ('=' * 100)
    Add $title
    Add ('=' * 100)
}

function AddRuleBlock([string]$prefix, [string[]]$entries) {
    foreach ($entry in $entries) {
        Add "$prefix $entry"
    }
}

AddBlock @'
<system-reminder>
Build Mode - Execution Prompt
You are not in plan-only mode.
You are allowed to read, edit, run targeted validations, update repo artifacts, and leave behind exact continuity checkpoints.
Prompt language must remain English.
Operator-facing checkpoint notes and progress reports may be Turkish when that improves continuity.
If remaining model quota or budget drops to 10 or below, immediately persist an exact checkpoint to OPS/90_LOW_QUOTA_CHECKPOINT_V7.md.
If remaining model quota or budget drops to 5 or below, stop expansion work, persist an exact resume package to OPS/91_RESUME_HANDOFF_V7.md, and leave exact next commands and exact next files.
Do not let the session die without a written checkpoint.
</system-reminder>
'@

AddHeader 'CODEX 5-HOUR HARDCORE JARVIS ULTRA EXECUTION PROMPT V7 - 24K EDITION'

AddBlock @'
You are Codex operating inside C:\Users\sergen\Desktop\jarvis-mission-control.
You must use the entire current Codex conversation history as active evidence and working memory.
You must continue from the actual current repo state, not a clean-slate fiction.
You are in execution mode.
You are here to recover truth, run the highest ROI fixes, harvest the highest ROI donor patterns, and leave behind a restart-proof evidence trail.
This prompt intentionally combines aggressive adversarial audit mode, low-narration hardcore coding mode, artifact-first continuity mode, hierarchical multi-agent mission control mode, and self-heal / self-correct / self-improve discipline.
The user wants Jarvis to move toward stronger Telegram connectivity, stronger OpenClaw profile coherence, watchdog and restart-proof runtime behavior, more truthful queue health, stronger memory and self-improvement, self-coding capability, stronger voice continuity, stronger hologram direction, safe PC-mode control, external intelligence lanes, and a future SaaS ascent path.
Truth outranks ambition.
'@

$latestCheckpointClaims = @(
    'Historical checkpoint claim: OPS/CODEX_5H_HARDCORE_PROMPT_V2.txt was re-verified at 10000 lines.',
    'Historical checkpoint claim: OPS/12_5H_HARDCORE_MASTER_ROADMAP.md was re-verified at 3509 lines.',
    'Historical checkpoint claim: OPS/13_EXECUTION_RUNLOG.md through OPS/19_NEXT_SHIFT_HANDOFF.md were reconciled.',
    'Historical checkpoint claim: tests.test_dashboard should be treated as current-pass evidence.',
    'Historical checkpoint claim: the old 117/117 passing claim was downgraded to UNVERIFIED.',
    'Historical checkpoint claim: openclaw_web_only.cmd was recorded as a bridge --web-only wrapper.',
    'Historical checkpoint claim: server/bridge.py now writes server/data/bridge_heartbeat.json and server/data/bridge.lock.',
    'Historical checkpoint claim: server/watchdog.py now has the producer path it expected.',
    'Historical checkpoint claim: master_launcher.py heading was narrowed to actual behavior.',
    'Historical checkpoint claim: the highest remaining ROI item was watchdog live smoke, restart semantics, and exact 117/117 re-proof.'
)

$currentRepoTruth = @(
    'Current repo truth: OPS/60 through OPS/70 V5 artifacts exist and form a newer truth set.',
    'Current repo truth: OPS/jarvis.txt-v4v5.txt currently exists at 20000 lines.',
    'Current repo truth: server/runtime_config.py contains apply_runtime_cli_overrides().',
    'Current repo truth: server/bridge.py consumes apply_runtime_cli_overrides() and logs when web-only mode is forced.',
    'Current repo truth: tests/test_runtime_config.py exists and covers the web-only CLI override path.',
    'Current repo truth: services/orchestrator/task_queue.py contains snapshot() and queue persistence logic.',
    'Current repo truth: services/orchestrator/main.py exposes queue_snapshot, queued_by_priority, awaiting_confirmation, and queue_state_file in /health.',
    'Current repo truth: tests/test_orchestrator_health.py exists and covers health snapshot exposure.',
    'Current repo truth: a targeted 25-test pass was previously observed for dashboard, runtime_config, task_queue, and orchestrator health.',
    'Current repo truth: watchdog live smoke and full restart semantics are still not re-proven.',
    'Current repo truth: OpenClaw and Telegram end-to-end reply truth is still not cleanly closed.',
    'Current repo truth: apps/desktop-hologram currently exposes assets and node_modules while older scan outputs reference missing source files.',
    'Current repo truth: apps/desktop-hologram/node_modules/electron/package.json currently reports version 28.3.3.'
)

AddHeader 'INHERITED HISTORY AND CURRENT VERIFIED STATE'
AddRuleBlock 'Carry forward:' $latestCheckpointClaims
AddRuleBlock 'Carry forward:' $currentRepoTruth

$reliable = @(
    'server/skills/memory_skill.py',
    'server/agents/self_healer.py',
    'services/voice/voice_service.py',
    'tests/test_task_queue.py',
    'tests/test_memory_skill.py',
    'tests/test_self_healer.py',
    'tests/test_dashboard.py',
    'heartbeat and lock producer additions'
)

$partial = @(
    'services/orchestrator/task_queue.py',
    'services/orchestrator/agent_runner.py',
    'services/orchestrator/main.py',
    'openclaw.cmd migration path'
)

$risky = @(
    'openclaw_web_only.cmd',
    'install_openclaw_startup.cmd'
)

AddHeader 'MANDATORY CLASSIFICATION BASELINE'
AddRuleBlock 'Reliable baseline:' $reliable
AddRuleBlock 'Partially correct baseline:' $partial
AddRuleBlock 'Risky or needs repair baseline:' $risky
Add 'Do not silently discard this baseline.'
Add 'Either preserve it or update it with stronger evidence.'

$absolutePriorities = @(
    'OpenClaw and Telegram truth comes first.',
    'Hologram ownership and startup failure root-cause comes second.',
    'Watchdog live smoke and restart semantics proof comes third.',
    'Queue restart truth and queue health semantics come fourth.',
    'Repo cleanup actionability comes fifth.',
    'Voice interruption diagnosis comes sixth.',
    'Memory, self-improvement, and self-coding direction comes seventh.',
    'Source repo donor intake comes eighth.',
    'Social intelligence agent planning comes ninth.',
    'SaaS ascent path comes tenth.'
)

AddHeader 'ABSOLUTE TOP PRIORITY ORDER'
AddRuleBlock 'Priority:' $absolutePriorities
Add 'If lower-value expansion work obscures unresolved OpenClaw or Telegram truth, you failed.'

AddHeader 'MANDATORY OPENCLAW AND TELEGRAM FIRST DIRECTIVE'
AddBlock @'
You must prioritize the following before broader expansion planning:
- Which OpenClaw profile should be canonical right now: main, dev, or split.
- Whether direct Telegram send works right now.
- Whether agent-generated Telegram reply works right now.
- Whether pairing is complete.
- Whether authorization is complete.
- Whether model configuration is coherent.
- Whether auth configuration is coherent.
- What exact minimum operator workflow is trustworthy right now.
- What exactly blocks end-to-end conversational reliability.
- What should be fixed first in the next sprint.
Treat direct send and agent-generated reply as separate realities.
Do not collapse them into one green status.
If one works and the other fails, mark Telegram as PARTIAL.
'@

AddHeader 'MANDATORY HOLOGRAM AND DESKTOP EMBODIMENT DIRECTIVE'
AddBlock @'
You must explicitly inspect and reason about the hologram stack.
Current contradiction to challenge:
- master_launcher.py currently launches npm start inside apps/desktop-hologram.
- current filesystem surface shows apps/desktop-hologram with assets and node_modules only.
- older local scan evidence such as JARVIS_FAST_SCAN.txt and 06_js_imports.txt references package.json, main.js, preload.js, renderer.js, styles.css, README.md, and index.html under apps/desktop-hologram.
- current node_modules evidence still exposes Electron 28.3.3.
You must determine whether this is ownership drift, partial deletion, partial checkout, cache-only residue, duplicate launch path confusion, or permissions and cache breakage.
You must connect this analysis to cache move failure, cache creation failure, GPU cache creation failure, access denied behavior, and possible duplicate process startup.
If source files are missing locally, do not invent them.
Instead, classify the current hologram surface as contradictory and define the highest ROI next fix path.
'@

$mandatoryArtifacts = @(
    'OPS/80_LAST24_FORENSIC_AUDIT_V7.md',
    'OPS/81_SOURCE_REPO_INTAKE_MAP_V7.md',
    'OPS/82_HIERARCHY_AND_SUBAGENT_MAP_V7.md',
    'OPS/83_5H_HARDCORE_MASTER_ROADMAP_V7.md',
    'OPS/84_EXECUTION_RUNLOG_V7.md',
    'OPS/85_CLAIMS_VS_REALITY_V7.md',
    'OPS/86_RUNTIME_CANON_V7.md',
    'OPS/87_OPENCLAW_TELEGRAM_MODEL_STATE_V7.md',
    'OPS/88_HOLOGRAM_VOICE_PC_MODE_DIRECTION_V7.md',
    'OPS/89_MEMORY_SELF_IMPROVEMENT_SOCIAL_V7.md',
    'OPS/90_LOW_QUOTA_CHECKPOINT_V7.md',
    'OPS/91_RESUME_HANDOFF_V7.md',
    'OPS/92_SAAS_ASCENT_AND_GROWTH_V7.md'
)

AddHeader 'MANDATORY V7 ARTIFACTS'
AddRuleBlock 'Artifact:' $mandatoryArtifacts
Add 'Create them early.'
Add 'Keep them current.'
Add 'Do not leave placeholder content.'

$sourceTruthHierarchy = @(
    'Level 1: live runtime evidence such as processes, ports, health endpoints, logs, actual sends, actual replies, actual crashes, and actual warnings.',
    'Level 2: current code such as startup logic, runtime branching, wrapper behavior, queue logic, memory path logic, Telegram handling, OpenClaw handling, hologram startup logic, and tests.',
    'Level 3: git evidence such as current diff, recent commits, branch, and working tree state.',
    'Level 4: conversation evidence such as previous analyses, checkpoint notes, and operator feedback.',
    'Level 5: docs and reports such as README, AGENTS.md, completion reports, integration summaries, and scan outputs.'
)

AddHeader 'STRICT SOURCE OF TRUTH HIERARCHY'
AddRuleBlock 'Hierarchy:' $sourceTruthHierarchy
Add 'If sources conflict, trust the higher level.'

AddHeader 'HIERARCHICAL AGENT FABRIC'
AddBlock @'
The user wants a hierarchy, not a flat list.
You must operate as if one top-level CEO controller coordinates multiple Codex execution tabs, each tab coordinates a lane, each lane owns specialist subagents, and each specialist can fan out to worker agents when supported.
Mandatory hierarchy:
- Layer 0: one CEO controller.
- Layer 1: ten lane directors.
- Layer 2: fifty core specialist agents, five per lane.
- Layer 2 optional overflow: up to three additional overflow specialists per lane when needed, allowing five to eight specialists per lane.
- Layer 3: fifty to one hundred worker agents beneath the specialist layer when tooling supports it.
If true subagent execution is not available, simulate this structure explicitly and honestly.
Do not fake actual spawned work.
Do not describe prompt generators as autonomous agents.
'@

$laneNames = @(
    'Main Lead Orchestrator',
    'Evidence Miner',
    'Runtime Cartographer',
    'Backend Stabilizer',
    'Failure Hunter',
    'OpenClaw and Model Integrator',
    'Voice and Hologram Designer',
    'Memory and Self-Improvement Architect',
    'Social and External Intelligence Agent',
    'Adversarial Verifier'
)

$lanePurposes = @(
    'Own sequencing, priority, cross-lane coherence, gate closure, and final synthesis.',
    'Mine claims, logs, tests, diffs, scans, and historical notes into hard evidence units.',
    'Map launcher, bridge, watchdog, orchestrator, OpenClaw, Telegram, voice, hologram, and dashboard ownership.',
    'Drive minimal safe fixes, tie code paths to proof paths, and protect ROI.',
    'Classify failure modes, attack fake greens, and separate cosmetic noise from structural breakage.',
    'Own OpenClaw profiles, pairing, authorization, auth, model truth, direct send, and agent reply truth.',
    'Own voice interruption diagnosis, hologram root-cause mapping, embodiment direction, and safe PC-mode interaction quality.',
    'Own memory durability, self-heal realism, self-coding direction, and remembered-change architecture.',
    'Own GitHub, YouTube, social-media, AI-news, daily digest, and integration recommendation lanes.',
    'Attack overclaims, weak proofs, stale docs, fake readiness, and silent scope inflation.'
)

$laneSpecialists = @(
    @('mission-ceo','dependency-chief','checkpoint-keeper','scope-killer','closeout-synthesizer'),
    @('history-miner','runlog-miner','diff-miner','scan-miner','claim-source-miner'),
    @('entrypoint-mapper','owner-mapper','wrapper-mapper','port-path-mapper','staleness-mapper'),
    @('web-only-stabilizer','queue-stabilizer','watchdog-stabilizer','cleanup-stabilizer','validation-stabilizer'),
    @('green-check-hunter','restart-failure-hunter','telegram-failure-hunter','hologram-failure-hunter','artifact-drift-hunter'),
    @('profile-auditor','telegram-direct-send-auditor','telegram-reply-auditor','pairing-auth-auditor','model-auth-auditor'),
    @('voice-interruption-diagnostician','voice-state-machine-designer','hologram-root-cause-analyst','embodiment-designer','pc-mode-safety-designer'),
    @('memory-durability-auditor','self-heal-safety-auditor','self-coding-architect','change-memory-architect','failure-memory-architect'),
    @('github-intelligence-architect','youtube-intelligence-architect','social-news-architect','daily-digest-architect','integration-recommendation-architect'),
    @('claim-downgrader','doc-drift-attacker','runtime-proof-attacker','scope-inflation-attacker','readiness-language-attacker')
)

$laneOverflow = @(
    @('budget-sentinel','handoff-arbiter','truth-escalator'),
    @('artifact-verifier','test-proof-miner','status-screen-miner'),
    @('bridge-boundary-mapper','hologram-drift-mapper','telemetry-path-mapper'),
    @('config-override-auditor','health-endpoint-auditor','regression-sentinel'),
    @('assertion-severity-hunter','permission-hunter','operator-trap-hunter'),
    @('workflow-designer','post-send-stability-auditor','profile-conflict-resolver'),
    @('microsoft-donor-scout','mark35-donor-scout','launcher-drift-auditor'),
    @('integration-memory-architect','improvement-loop-designer','ops-memory-bridger'),
    @('thirty-day-donor-scout','source-repo-classifier','trend-ranking-architect'),
    @('checkpoint-optimism-attacker','test-relevance-attacker','handoff-hardener')
)

AddHeader 'TEN LANE DIRECTORS, FIFTY CORE SPECIALISTS, OPTIONAL OVERFLOW, AND WORKER AGENTS'
Add 'Population target: 1 CEO controller, 10 lane directors, 50 core specialist agents, optional expansion up to 80 specialists, and 50 to 100 worker agents beneath them when tooling supports it.'

for ($i = 0; $i -lt $laneNames.Count; $i++) {
    Add ('Lane ' + $i + ': ' + $laneNames[$i])
    Add ('Lane ' + $i + ' purpose: ' + $lanePurposes[$i])
    Add ('Lane ' + $i + ' must produce exact findings, exact commands, exact files, exact contradictions, and exact artifact updates.')
    foreach ($spec in $laneSpecialists[$i]) {
        Add ('Core specialist: ' + $spec)
        Add 'Core specialist rule: may fan out to one or two worker agents if supported.'
    }
    foreach ($spec in $laneOverflow[$i]) {
        Add ('Overflow specialist: ' + $spec)
        Add 'Overflow specialist rule: activate only when the lane needs five to eight specialists rather than the five-core minimum.'
    }
}

$subagentDiscovery = @(
    '.codex/agents/',
    'tools/subagents/',
    'tools/subagents/README.md',
    'tools/subagents/jarvis-subagent-shortcuts.ps1',
    'docs/SUBAGENT_MAPPING.md',
    'external-repos/awesome-codex-subagents/',
    'server/config/agent_manifests.json'
)

AddHeader 'SUBAGENT INFRASTRUCTURE YOU MUST DISCOVER AND USE HONESTLY'
AddRuleBlock 'Inspect:' $subagentDiscovery
Add 'Current local evidence says .codex/agents exists with a large local catalog.'
Add 'Current local evidence says tools/subagents/jarvis-subagent-shortcuts.ps1 exists.'
Add 'Current local evidence says external-repos/awesome-codex-subagents exists.'
Add 'You must explicitly separate real executable subagents from wrappers, shortcut prompts, registries, catalogs, and donor repos.'

$sourceRepoTargets = @(
    'external-repos/Mark-XXXV',
    'external-repos/ClawRouter',
    'external-repos/OpenHands',
    'external-repos/youtube-mcp-server',
    'external-repos/mcp-server-youtube-transcript',
    'external-repos/awesome-codex-subagents',
    'external-repos/awesome-agent-skills',
    'external-repos/claude-skills',
    'external-repos/claude-code',
    'external-repos/claude-code-hooks-mastery',
    'external-repos/cline',
    'external-repos/crewAI',
    'external-repos/devika',
    'external-repos/aider',
    'external-repos/swarms',
    'mert kaynak/All Of My Claude Skills',
    'jarvis kaynaklar',
    'claude-code-main',
    'agency-agents',
    'agency-agents-new',
    'openhands',
    'youtube-remotion'
)

AddHeader 'SOURCE REPO INTAKE AND DONOR DISCOVERY'
Add 'The user says a very large downloaded code pool exists and should be treated as integration source inventory.'
Add 'The user says there is roughly 520000 lines of downloaded code to consider as donor input.'
Add 'Treat the line-count claim as a claimed scope fact until re-measured.'
AddRuleBlock 'Inspect source root:' $sourceRepoTargets
Add 'If a repo or source root is missing locally, mark it missing.'
Add 'Do not invent repo contents.'
Add 'For every present source root, classify it as runtime candidate, feature donor, architecture donor, prompt donor, reference only, hold for later, or not useful.'
Add 'For every useful source root, define exact value, first safe harvest target, integration risk, and what must not be copied directly.'
Add 'Mark-XXXV style sources matter for PC-control, mute state, voice continuity, visible assistant states, and operator-safe control concepts.'
Add 'Microsoft voice-assistant style sources matter only if actually present locally; otherwise mark missing and move on.'
Add 'Mert-source folders and Claude skill mirrors are donor inventories, not automatic runtime surfaces.'

$claimAudit = @(
    'Whether the historical 10000-line V2 prompt count still matches the current file exactly.',
    'Whether the historical 3509-line roadmap count still matches the current file exactly or whether line drift exists.',
    'Whether tests.test_dashboard remains meaningful current-pass evidence.',
    'Whether 117/117 remains UNVERIFIED and must be either reproven or retired.',
    'Whether web-only support is truly runtime-real across bridge and wrappers.',
    'Whether watchdog restart semantics are now correct or merely partially prepared.',
    'Whether queue persistence is code-real, test-real, or runtime-real.',
    'Whether queue priority is semantically correct in actual runtime behavior.',
    'Whether memory is truly cross-platform.',
    'Whether self-healer is Windows-safe enough for incremental trust.',
    'Whether voice interruption remains an active defect.',
    'Whether the hologram stack is canonical, duplicated, stale, missing, or contradictory.',
    'Whether the huge downloaded repo pool can materially strengthen Jarvis in the near term.',
    'Whether Jarvis is credibly on a path toward self-coding and self-remembering operation.',
    'Whether Jarvis has any honest path toward SaaS ascent from this base.'
)

AddHeader 'MANDATORY CLAIMS TO RE-AUDIT'
AddRuleBlock 'Re-audit claim:' $claimAudit

$nextPriorities = @(
    'Priority 1: verify, preserve, and if needed extend real --web-only support in server/bridge.py and its wrappers.',
    'Priority 2: verify, preserve, and if needed extend queue health semantics, queue lifecycle truth, and queue restart truth.',
    'Priority 3: produce a repo cleanup plan with exact committable, artifact-only, and ignore-only groups.',
    'Priority 4: run or design watchdog live smoke and restart semantics proof.',
    'Priority 5: re-audit OpenClaw main and dev profile behavior, pairing, authorization, direct send, and agent reply truth.',
    'Priority 6: verify queue restart and persistence proof rather than trusting state-file presence alone.',
    'Priority 7: diagnose voice interruption and missing state surfaces.',
    'Priority 8: root-cause hologram startup drift, missing source ownership, and cache or permission issues.',
    'Priority 9: intake donor repos and classify immediate versus deferred value.',
    'Priority 10: define GitHub, YouTube, social-media, AI-news, memory, self-coding, and SaaS growth lanes without overstating maturity.'
)

AddHeader 'REQUIRED NEXT-STEP PRIORITIES INSIDE THIS PROMPT'
AddRuleBlock 'Next-step rule:' $nextPriorities

$hours = @(
    'Hour 1: forensic reconstruction, claim re-baselining, source repo inventory, hierarchy lock, and artifact initialization.',
    'Hour 2: runtime canon, launcher and hologram ownership, bridge and watchdog proof paths, queue semantics and wrapper truth.',
    'Hour 3: OpenClaw and Telegram deep audit of profiles, pairing, auth, direct send, and agent reply.',
    'Hour 4: memory, self-improvement, self-coding, voice continuity, hologram direction, and PC-mode safety architecture.',
    'Hour 5: social intelligence design, SaaS ascent framing, targeted revalidation, low-budget checkpoint hardening, and final handoff.'
)

AddHeader 'FIVE HOUR EXECUTION PHASES'
AddRuleBlock 'Execution hour:' $hours
Add 'Every hour must close with updated artifacts, explicit proof notes, and unresolved contradictions if any remain.'

$segments = @(
    'Baseline checkpoint lock','Current repo truth reconciliation','Reliable bucket recheck','Partial bucket recheck','Risk bucket recheck',
    'Subagent root discovery','Fifty-specialist hierarchy map','Worker-population rule definition','Wrapper versus runtime truth audit','Bridge watchdog producer contract audit',
    'Watchdog restart proof design','Queue snapshot semantics audit','Queue restart proof design','OpenClaw profile split audit','Telegram direct send audit',
    'Telegram agent reply audit','Auth and model coherence audit','Hologram ownership drift audit','Voice interruption hypothesis map','Memory durability audit',
    'Self-heal safety audit','Mark-XXXV donor harvest plan','Social and AI-news lane design','SaaS ascent framing','Low-budget handoff hardening'
)

AddHeader 'TWENTY FIVE MICRO-SEGMENTS'
for ($i = 0; $i -lt $segments.Count; $i++) {
    $idx = $i + 1
    Add ('Segment ' + $idx + ' title: ' + $segments[$i])
    Add ('Segment ' + $idx + ' must define exact lane owner, support lane, files, commands, contradiction, success criteria, fallback, and handoff note.')
}

$futureAgents = @(
    'GitHub intelligence agent',
    'YouTube intelligence agent',
    'Social-media and AI-news agent',
    '24-hour digest and integration recommendation agent',
    'Memory writeback agent',
    'Self-coding proposal agent',
    'Self-coding verification agent',
    'Voice continuity agent',
    'Hologram and embodiment agent',
    'PC-mode control safety agent',
    'SaaS packaging and operator workflow agent'
)

AddHeader 'FUTURE AGENT FABRIC TO DESIGN'
foreach ($agent in $futureAgents) {
    Add ('Future agent: ' + $agent)
    Add 'Define mission, inputs, outputs, memory writeback, operator review point, and integration risk.'
}

$antiHallucination = @(
    'If a source repo is not present locally, mark it missing.',
    'If a video or inspiration source is not locally mirrored or documented, do not invent its contents.',
    'If a wrapper promises a mode the runtime does not parse, classify it as misleading.',
    'If direct send works but agent-generated reply fails, classify Telegram as PARTIAL.',
    'If tests do not cover the active runtime path, classify their evidence value as weak or partial.',
    'If a giant repo exists but is not integrated, classify it as source inventory only.',
    'If py_compile passes without runtime proof, classify it as syntax-only validation.',
    'If docs are cleaner than runtime, docs are wrong until fixed.',
    'If a feature is exciting but unsupported, move it into future direction rather than current capability.',
    'If a checkpoint or report overstates success, preserve the contradiction.'
)

AddHeader 'ANTI-HALLUCINATION RULES'
AddRuleBlock 'Rule:' $antiHallucination

$expansionDomains = @(
    'OpenClaw truth','Telegram direct send','Telegram agent reply','Watchdog restart semantics','Bridge heartbeat and lock contract','Queue snapshot semantics',
    'Queue persistence and restart proof','Repo cleanup actionability','Voice interruption','Hologram ownership drift','Hologram cache and permission failures',
    'Memory durability','Self-healer Windows safety','Self-coding direction','Mark-XXXV PC-control donor path','Microsoft voice-assistant donor path',
    'Mert-source donor path','GitHub intelligence lane','YouTube intelligence lane','Social-media and AI-news lane','Daily digest recommendation loop',
    'SaaS ascent path','Subagent execution reality','Low-quota checkpointing'
)

$expansionEvidence = @(
    'live runtime evidence','current code evidence','git evidence','conversation evidence','docs and report evidence',
    'scan-file evidence','test evidence','wrapper evidence','health endpoint evidence','process ownership evidence'
)

$expansionContradictions = @(
    'wrapper language may overstate runtime behavior','checkpoint optimism may outrun current reality','code presence may outrun runtime proof',
    'source inventory may be mistaken for integration','direct send may be mistaken for conversational reliability',
    'narrow tests may be mistaken for whole-system health','missing hologram source may be hidden by stale scan outputs',
    'queue health metrics may hide lifecycle truth','voice fixes may not solve interruption reality','agent catalogs may be mistaken for real workers'
)

$expansionArtifacts = @(
    'OPS/80_LAST24_FORENSIC_AUDIT_V7.md','OPS/81_SOURCE_REPO_INTAKE_MAP_V7.md','OPS/82_HIERARCHY_AND_SUBAGENT_MAP_V7.md',
    'OPS/83_5H_HARDCORE_MASTER_ROADMAP_V7.md','OPS/84_EXECUTION_RUNLOG_V7.md','OPS/85_CLAIMS_VS_REALITY_V7.md',
    'OPS/86_RUNTIME_CANON_V7.md','OPS/87_OPENCLAW_TELEGRAM_MODEL_STATE_V7.md','OPS/88_HOLOGRAM_VOICE_PC_MODE_DIRECTION_V7.md',
    'OPS/89_MEMORY_SELF_IMPROVEMENT_SOCIAL_V7.md','OPS/90_LOW_QUOTA_CHECKPOINT_V7.md','OPS/91_RESUME_HANDOFF_V7.md','OPS/92_SAAS_ASCENT_AND_GROWTH_V7.md'
)

$expansionActions = @(
    'verify and classify','repair with the smallest coherent change','design the proof path before implementation','downgrade an overclaim',
    'upgrade a claim only if the proof supports it','harvest a donor pattern without bulk-copying','define an operator-safe workflow',
    'write a low-budget checkpoint','write a resume-safe handoff','kill scope drift and return to ROI'
)

AddHeader 'EXPANSION DIRECTIVES'
while ($lines.Count -lt $targetLines) {
    $n = $lines.Count + 1
    $domain = $expansionDomains[($n - 1) % $expansionDomains.Count]
    $evidence = $expansionEvidence[($n - 1) % $expansionEvidence.Count]
    $contradiction = $expansionContradictions[($n - 1) % $expansionContradictions.Count]
    $artifact = $expansionArtifacts[($n - 1) % $expansionArtifacts.Count]
    $action = $expansionActions[($n - 1) % $expansionActions.Count]
    Add ('Expansion directive ' + $n + ': for ' + $domain + ', challenge the contradiction that ' + $contradiction + ', force one exact ' + $evidence + ' probe, drive one exact ' + $action + ', and record the outcome in ' + $artifact + ' without overstating readiness.')
}

if ($lines.Count -ne $targetLines) {
    throw "Prompt line count mismatch. Expected $targetLines, got $($lines.Count)."
}

$lines | Set-Content -Encoding utf8 $outFile

$reportLines = @(
    '# Prompt Build Checkpoint V7',
    '',
    'Durum: tamamlandi',
    ('Tarih: ' + (Get-Date -Format 'yyyy-MM-dd HH:mm:ss')),
    ('Prompt dosyasi: ' + $outFile),
    ('Satir sayisi: ' + $lines.Count),
    'Generator script: scripts/generate_codex_hardcore_prompt_v7.ps1',
    'Dil kurali: prompt English, raporlar Turkish.',
    'Ana vurgu: OpenClaw ve Telegram first, hologram ownership drift, watchdog, queue truth, repo cleanup, memory, self-coding, PC mode, social intelligence, SaaS path.',
    'Ajan hiyerarsisi: 1 CEO, 10 lane director, 50 core specialist, 5-8 specialist per lane, 50-100 worker guideline.',
    'Low quota kurali: OPS/90_LOW_QUOTA_CHECKPOINT_V7.md ve OPS/91_RESUME_HANDOFF_V7.md.',
    'Sonraki adim: prompt dosyasini yeni Codex oturumuna ver veya panoya al.',
    ''
)

$reportLines | Set-Content -Encoding utf8 $reportFile

Write-Host ('Generated: ' + $outFile)
Write-Host ('LineCount: ' + $lines.Count)
Write-Host ('Checkpoint: ' + $reportFile)
