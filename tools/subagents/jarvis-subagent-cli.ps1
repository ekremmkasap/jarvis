param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$Mode,

    [string]$Task,
    [string]$Problem,
    [string]$ReviewScope,
    [string]$AuditScope,
    [string]$Question,
    [string]$Topic,
    [string]$Version,
    [string]$Scope,
    [string]$Evidence,
    [string]$Implementer,
    [string]$Issue,
    [switch]$Copy
)

. "$PSScriptRoot\jarvis-subagent-shortcuts.ps1"

$normalizedMode = $Mode.ToLowerInvariant()

switch ($normalizedMode) {
    "help" {
        jarvis-sub-help
    }
    "map" {
        if (-not $Task) { throw "jarvis-sub map requires -Task" }
        jarvis-sub-map -Task $Task -Scope $Scope -Copy:$Copy
    }
    "debug" {
        if (-not $Problem) { throw "jarvis-sub debug requires -Problem" }
        jarvis-sub-debug -Problem $Problem -Scope $Scope -Evidence $Evidence -Copy:$Copy
    }
    "review" {
        if (-not $ReviewScope) { throw "jarvis-sub review requires -ReviewScope" }
        jarvis-sub-review -ReviewScope $ReviewScope -Scope $Scope -Copy:$Copy
    }
    "bug" {
        if (-not $Problem) { throw "jarvis-sub bug requires -Problem" }
        jarvis-sub-bug -Problem $Problem -Scope $Scope -Evidence $Evidence -Copy:$Copy
    }
    "fix" {
        if (-not $Task) { throw "jarvis-sub fix requires -Task" }
        jarvis-sub-fix -Task $Task -Scope $Scope -Implementer $Implementer -Copy:$Copy
    }
    "audit" {
        if (-not $AuditScope) { throw "jarvis-sub audit requires -AuditScope" }
        jarvis-sub-audit -AuditScope $AuditScope -Scope $Scope -Topic $Topic -Copy:$Copy
    }
    "flow" {
        if (-not $Task) { throw "jarvis-sub flow requires -Task" }
        jarvis-sub-flow -Task $Task -Scope $Scope -Copy:$Copy
    }
    "search" {
        if (-not $Question) { throw "jarvis-sub search requires -Question" }
        jarvis-sub-search -Question $Question -Scope $Scope -Copy:$Copy
    }
    "docs" {
        if (-not $Topic) { throw "jarvis-sub docs requires -Topic" }
        if (-not $Question) { throw "jarvis-sub docs requires -Question" }
        jarvis-sub-docs -Topic $Topic -Question $Question -Version $Version -Copy:$Copy
    }
    "organize" {
        if (-not $Task) { throw "jarvis-sub organize requires -Task" }
        jarvis-sub-organize -Task $Task -Copy:$Copy
    }
    "python" {
        if (-not $Task) { throw "jarvis-sub python requires -Task" }
        jarvis-sub-python -Task $Task -Scope $Scope -Copy:$Copy
    }
    "ps51" {
        if (-not $Task) { throw "jarvis-sub ps51 requires -Task" }
        jarvis-sub-ps51 -Task $Task -Scope $Scope -Copy:$Copy
    }
    "pwsh" {
        if (-not $Task) { throw "jarvis-sub pwsh requires -Task" }
        jarvis-sub-pwsh -Task $Task -Scope $Scope -Copy:$Copy
    }
    "tool" {
        if (-not $Task) { throw "jarvis-sub tool requires -Task" }
        jarvis-sub-tool -Task $Task -Scope $Scope -Copy:$Copy
    }
    "mcp" {
        if (-not $Task) { throw "jarvis-sub mcp requires -Task" }
        jarvis-sub-mcp -Task $Task -Scope $Scope -Copy:$Copy
    }
    "ai" {
        if (-not $Task) { throw "jarvis-sub ai requires -Task" }
        jarvis-sub-ai -Task $Task -Scope $Scope -Copy:$Copy
    }
    "backend" {
        if (-not $Task) { throw "jarvis-sub backend requires -Task" }
        jarvis-sub-backend -Task $Task -Scope $Scope -Copy:$Copy
    }
    "frontend" {
        if (-not $Task) { throw "jarvis-sub frontend requires -Task" }
        jarvis-sub-frontend -Task $Task -Scope $Scope -Copy:$Copy
    }
    "wininfra" {
        if (-not $Issue) { throw "jarvis-sub wininfra requires -Issue" }
        jarvis-sub-wininfra -Issue $Issue -Scope $Scope -Copy:$Copy
    }
    default {
        throw "Unknown jarvis-sub mode: $Mode"
    }
}
