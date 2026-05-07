param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsList
)

$scriptPath = Join-Path $PSScriptRoot "tools\codex_accounts.py"
python $scriptPath @ArgsList
