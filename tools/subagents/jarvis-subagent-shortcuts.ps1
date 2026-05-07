Set-StrictMode -Version Latest

function Get-JarvisRepoRoot {
    Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
}

function Get-JarvisTargetText {
    param(
        [string]$Scope
    )

    $repoRoot = Get-JarvisRepoRoot
    if ($Scope) {
        return "the Jarvis repo at $repoRoot, focused on $Scope"
    }

    return "the Jarvis repo at $repoRoot"
}

function Write-JarvisPrompt {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Text,
        [switch]$Copy
    )

    if ($Copy) {
        try {
            Set-Clipboard -Value $Text
        }
        catch {
            Write-Warning "Clipboard copy failed: $($_.Exception.Message)"
        }
    }

    $Text
}

function jarvis-sub-help {
    @"
Jarvis subagent shortcut commands:
  jarvis-sub.cmd help
  jarvis-sub.cmd map -Task <task> [-Scope <file-or-area>] [-Copy]
  jarvis-sub.cmd debug -Problem <problem> [-Scope <file-or-area>] [-Evidence <text>] [-Copy]
  jarvis-sub.cmd review -ReviewScope <scope> [-Scope <file-or-area>] [-Copy]
  jarvis-sub.cmd bug -Problem <problem> [-Scope <file-or-area>] [-Evidence <text>] [-Copy]
  jarvis-sub.cmd fix -Task <task> [-Scope <file-or-area>] [-Implementer <agent>] [-Copy]
  jarvis-sub.cmd audit -AuditScope <scope> [-Scope <file-or-area>] [-Topic <topic>] [-Copy]
  jarvis-sub.cmd flow -Task <task> [-Scope <file-or-area>] [-Copy]
  jarvis-sub.cmd search -Question <question> [-Scope <file-or-area>] [-Copy]
  jarvis-sub.cmd docs -Topic <topic> -Question <question> [-Version <version>] [-Copy]
  jarvis-sub.cmd organize -Task <task> [-Copy]
  jarvis-sub.cmd python -Task <task> [-Scope <file-or-area>] [-Copy]
  jarvis-sub.cmd ps51 -Task <task> [-Scope <file-or-area>] [-Copy]
  jarvis-sub.cmd pwsh -Task <task> [-Scope <file-or-area>] [-Copy]
  jarvis-sub.cmd tool -Task <task> [-Scope <file-or-area>] [-Copy]
  jarvis-sub.cmd mcp -Task <task> [-Scope <file-or-area>] [-Copy]
  jarvis-sub.cmd ai -Task <task> [-Scope <file-or-area>] [-Copy]
  jarvis-sub.cmd backend -Task <task> [-Scope <file-or-area>] [-Copy]
  jarvis-sub.cmd frontend -Task <task> [-Scope <file-or-area>] [-Copy]
  jarvis-sub.cmd wininfra -Issue <issue> [-Scope <file-or-area>] [-Copy]

Direct wrapper commands:
  tools\subagents\jarvis-sub-help.cmd
  tools\subagents\jarvis-sub-map.cmd "login timeout handling" -Scope "server/bridge.py" -Copy
  tools\subagents\jarvis-sub-debug.cmd "watchdog restart loop" -Scope "server/watchdog.py" -Evidence "heartbeat age goes null" -Copy
  tools\subagents\jarvis-sub-review.cmd "task bus hardening patch" -Scope "server/skills/task_bus.py" -Copy
  tools\subagents\jarvis-sub-bug.cmd "voice bridge failure" -Scope "services/voice" -Evidence "timeout after wake word" -Copy
  tools\subagents\jarvis-sub-fix.cmd "router fallback bug" -Scope "server/bridge.py" -Implementer backend-developer -Copy
  tools\subagents\jarvis-sub-audit.cmd "provider routing changes" -Scope "server/bridge.py" -Topic "routing and safety" -Copy
  tools\subagents\jarvis-sub-flow.cmd "mission dispatch path" -Scope "server/bridge.py" -Copy
  tools\subagents\jarvis-sub-search.cmd "where gateway health is computed" -Scope "server" -Copy
  tools\subagents\jarvis-sub-docs.cmd "OpenAI Responses API" -Question "structured output defaults" -Version latest -Copy
  tools\subagents\jarvis-sub-organize.cmd "split the next Jarvis mission-control feature into clean subagent threads" -Copy
  tools\subagents\jarvis-sub-backend.cmd "task routing bug" -Scope "server/bridge.py" -Copy
  tools\subagents\jarvis-sub-frontend.cmd "dashboard panel regression" -Scope "apps/web-ui/src" -Copy
  tools\subagents\jarvis-sub-ai.cmd "tool-call fallback issue" -Scope "server/services" -Copy

Notes:
  - Commands target this repo by default; use -Scope to narrow to a file, module, or area.
  - -Copy sends the generated prompt to the Windows clipboard.
  - If owner area is unclear, start with search or map before fix/back-end/front-end shortcuts.
  - These commands do not execute subagents; they generate delegation prompts for Codex.
  - Paste the generated text into Codex and explicitly delegate with the named agent.
  - OpenCode restart is not required for this shortcut flow.
  - If .codex/agents changes and Codex does not see new agents, refresh the Codex session.
  - start_jarvis.bat --subagent-help prints this help without launching the watchdog.
"@
}

function jarvis-sub-map {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Task,
        [string]$Scope,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use code-mapper to trace the owning code path for $Task in $target and return entrypoints, key files, branch points, side effects, and the next file to inspect."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-debug {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Problem,
        [string]$Scope,
        [string]$Evidence,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use debugger to investigate $Problem in $target"
    if ($Evidence) {
        $text += " using this evidence: $Evidence"
    }
    $text += ", and return the most likely cause, supporting evidence, disconfirming checks, and the smallest safe fix direction."

    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-review {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$ReviewScope,
        [string]$Scope,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use reviewer to review $ReviewScope in $target for correctness, regressions, security issues, and missing tests, and return findings first with file references ordered by severity."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-bug {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Problem,
        [string]$Scope,
        [string]$Evidence,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use code-mapper first to trace the owning path for $Problem in $target"
    if ($Evidence) {
        $text += " using this evidence: $Evidence"
    }
    $text += ", then use debugger on the confirmed path. Return the ordered owning path, strongest root-cause hypothesis, disconfirming checks, and the best next fixing agent."

    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-fix {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Task,
        [string]$Scope,
        [string]$Implementer,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $owner = "the closest implementation specialist"
    if ($Implementer) {
        $owner = $Implementer
    }

    $text = "Use code-mapper first to confirm the owning path for $Task in $target, then use $owner to implement the smallest safe fix. Return changed files, validation performed, and residual risk."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-audit {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$AuditScope,
        [string]$Scope,
        [string]$Topic,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use reviewer and docs-researcher in parallel to audit $AuditScope in $target"
    if ($Topic) {
        $text += " with special attention to $Topic"
    }
    $text += ", then summarize concrete risks, doc-backed constraints, missing tests, and the highest-priority fixes with file references."

    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-flow {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Task,
        [string]$Scope,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use search-specialist first to narrow the likely owner areas for $Task in $target, then use code-mapper to trace the confirmed end-to-end flow. Return the ordered path, branch points, side effects, and the next file to inspect."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-search {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Question,
        [string]$Scope,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use search-specialist to search $target for the highest-signal material related to $Question, rank the best hits, and tell me the next file or source to read."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-docs {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Topic,
        [Parameter(Mandatory = $true)]
        [string]$Question,
        [string]$Version,
        [switch]$Copy
    )

    $text = "Use docs-researcher to verify the documented behavior of $Topic for $Question"
    if ($Version) {
        $text += " in $Version"
    }
    $text += ", and return the answer with exact references, defaults, caveats, and ambiguity notes."

    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-organize {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Task,
        [switch]$Copy
    )

    $text = "Use agent-organizer to split $Task into the smallest clean subagent workflow for Jarvis Mission Control, keep the parent on the critical path, and return the lineup, local vs delegated work, dependency order, and prompt skeletons."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-python {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Task,
        [string]$Scope,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use python-pro to own the Python change for $Task in $target, implement the smallest safe fix, validate one success path and one failure path, and return changed files plus any remaining assumptions."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-ps51 {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Task,
        [string]$Scope,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use powershell-5.1-expert to handle $Task in $target, preserve Windows PowerShell 5.1 semantics, implement the smallest safe fix, and return changed files, compatibility notes, and any elevation requirements."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-pwsh {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Task,
        [string]$Scope,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use powershell-7-expert to handle $Task in $target, optimize for pwsh and cross-platform behavior, implement the smallest safe fix, and return changed files plus runtime and module caveats."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-tool {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Task,
        [string]$Scope,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use tooling-engineer to fix or improve the developer workflow around $Task in $target, implement the smallest practical change, and return changed files plus remaining integration checks."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-mcp {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Task,
        [string]$Scope,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use mcp-developer to handle $Task in $target, focus on schema and runtime contract fidelity plus error handling, implement the smallest safe change, and return changed files plus live validation needs."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-ai {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Task,
        [string]$Scope,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use ai-engineer to fix $Task in $target, trace the path from input shaping through model and tool calls to output handling, fix the real contract or orchestration problem, and return changed files plus targeted validation notes."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-backend {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Task,
        [string]$Scope,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use backend-developer to implement or fix $Task in $target, trace the entrypoint and side effects first, make the smallest coherent change, and return changed files plus success and failure validation notes."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-frontend {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Task,
        [string]$Scope,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use frontend-developer to implement or fix $Task in $target, map the component, state, and data boundary first, make the smallest coherent UI change, and return changed files plus edge-case and accessibility notes."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}

function jarvis-sub-wininfra {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory = $true)]
        [string]$Issue,
        [string]$Scope,
        [switch]$Copy
    )

    $target = Get-JarvisTargetText -Scope $Scope
    $text = "Use windows-infra-admin to analyze $Issue for $target in read-only mode and return the smallest safe recommendation, evidence, rollback considerations, and live validation needs."
    Write-JarvisPrompt -Text $text -Copy:$Copy
}
