from __future__ import annotations

"""
Token optimization skill.

Structured around Sean Kochel's 21 practical vibe-coding tips as surfaced by
public summary pages and a public LinkedIn post. The bridge command exposes the
tips as a stable local reference instead of relying on external network calls.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OptimizationTip:
    index: int
    title: str
    why: str
    action: str
    danger: str


TIPS: tuple[OptimizationTip, ...] = (
    OptimizationTip(1, "Use documented stacks", "Well-known stacks reduce hallucination risk and debugging cost.", "Prefer mature frameworks, documented SDKs, and standard deployment paths.", "Exotic stacks increase prompt repair churn."),
    OptimizationTip(2, "Plan extensively", "Front-loaded planning reduces context waste and rework.", "Spend most of the project on architecture, specs, states, and acceptance criteria.", "Jumping into code too early burns tokens on avoidable ambiguity."),
    OptimizationTip(3, "Manage context wisely", "Focused context improves answer quality and keeps prompts smaller.", "Pass only the files, constraints, and history needed for the current step.", "Large unfocused prompts hide the real problem."),
    OptimizationTip(4, "Commit between conversations", "Small checkpoints make rollback cheap and learning faster.", "Commit after each stable unit of progress or before changing direction.", "Long uncommitted sessions trap mistakes inside noisy diffs."),
    OptimizationTip(5, "Store solutions in system memory", "Recurring fixes should become reusable operating knowledge.", "Save solved patterns, edge cases, and preferred conventions into memory or docs.", "Re-solving the same problem wastes tokens every time."),
    OptimizationTip(6, "Ask for multiple perspectives", "Alternative solutions reveal tradeoffs before implementation.", "Request at least two approaches and ask the model to compare them.", "Accepting the first answer can lock you into a weak path."),
    OptimizationTip(7, "Evaluate against standards", "A solution is only good if it survives quality checks.", "Review output against best practices, team rules, and production expectations.", "Working code can still be fragile, insecure, or unmaintainable."),
    OptimizationTip(8, "Choose the right model", "Different models win on different tasks, cost, and latency.", "Use smaller models for formatting and larger ones for planning or debugging.", "Using one model for everything is expensive and inefficient."),
    OptimizationTip(9, "Establish project rules", "Rules create consistency across many AI-generated changes.", "Define file structure, naming, testing, dependency, and security rules early.", "No shared rules means every prompt has to restate the basics."),
    OptimizationTip(10, "Plan tasks granularly", "Smaller tasks reduce context width and make validation easier.", "Break work into reviewable subtasks with clear outputs and stopping points.", "Broad tasks invite broad, messy code generation."),
    OptimizationTip(11, "Design first", "Good UX and screen states prevent wasteful visual rewrites.", "Map screens, variants, edge states, and user feeling before coding UI.", "Coding UI before design leads to repeated redesign prompts."),
    OptimizationTip(12, "Pick tools that fit you", "The best tool is the one you can operate reliably.", "Match editor, agent, and workflow complexity to your skill level and budget.", "Copying expert setups can create unnecessary friction."),
    OptimizationTip(13, "Create custom modes", "Reusable task-specific prompts compress repeated instruction overhead.", "Maintain focused modes for planning, debugging, refactoring, and review.", "Starting from zero every time inflates token use."),
    OptimizationTip(14, "Keep docs current", "Current documentation keeps future prompts shorter and more accurate.", "Update README, runbooks, rules, and architecture notes when code changes.", "Outdated docs poison future generations."),
    OptimizationTip(15, "Use early returns and logging", "Simple control flow and observability shorten debugging loops.", "Prefer guard clauses and targeted logs around critical branches.", "Opaque functions force expensive exploratory prompting."),
    OptimizationTip(16, "Use checkpoint restores", "Recovery should be cheaper than repair.", "Save snapshots before risky edits and restore fast when the branch drifts.", "Trying to salvage a broken context wastes time and tokens."),
    OptimizationTip(17, "Understand before accepting", "Blind acceptance creates hidden debt.", "Ask the model to explain non-trivial code and verify the reasoning.", "Unknown code paths become tomorrow's production outage."),
    OptimizationTip(18, "Ship MVP first", "The smallest useful product gives the fastest learning loop.", "Implement the simplest version that delivers real user value.", "Gold-plating too early bloats scope and context."),
    OptimizationTip(19, "Define your stack boundaries", "Hard boundaries prevent accidental tool sprawl.", "List allowed dependencies and the decision rule for adding new tech.", "Uncontrolled dependency growth creates maintenance drag."),
    OptimizationTip(20, "Run security checks", "Speed without safety is a liability.", "Review auth, secrets, input validation, permissions, and known vulnerabilities regularly.", "Skipping security review invites silent risk accumulation."),
    OptimizationTip(21, "Start new conversations when needed", "Fresh contexts recover quality after drift.", "Reset the conversation when the model starts anchoring on stale assumptions.", "Dragging old context forward causes low-signal prompts and bad edits."),
)


def _list_summary() -> str:
    lines = ["Claude Hile - 21 Token/Context Tips", ""]
    for tip in TIPS:
        lines.append(f"{tip.index}. {tip.title}")
    lines.append("")
    lines.append("Kullanim: /claude-hile [1-21]")
    return "\n".join(lines)


def _format_tip(tip: OptimizationTip) -> str:
    return "\n".join(
        [
            f"Claude Hile #{tip.index}: {tip.title}",
            "",
            f"Neden: {tip.why}",
            f"Uygula: {tip.action}",
            f"Risk: {tip.danger}",
        ]
    )


def get_tip(index: int) -> OptimizationTip:
    if index < 1 or index > len(TIPS):
        raise ValueError("Tip index out of range.")
    return TIPS[index - 1]


def claude_hile_command(argument: str = "") -> str:
    raw = argument.strip().lower()
    if not raw:
        return _list_summary()

    if raw in {"all", "tum", "liste"}:
        return "\n\n".join(_format_tip(tip) for tip in TIPS)

    try:
        index = int(raw)
    except ValueError:
        return "Kullanim: /claude-hile [1-21]"

    try:
        return _format_tip(get_tip(index))
    except ValueError:
        return "Kullanim: /claude-hile [1-21]"
