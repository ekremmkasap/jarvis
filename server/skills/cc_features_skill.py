"""
Jarvis Skill — Claude Code Features (claude-code-new-features-early-2026)
Yeni CC özelliklerini Jarvis'e entegre eder: parallel agents, subagents, hooks.
"""
from pathlib import Path

REPO_DIR  = Path(__file__).parent.parent.parent / "external-repos" / "claude-code-new-features-early-2026"
CHEATSHEET = REPO_DIR / "CHEATSHEET.md"


def get_cheatsheet(section: str = "") -> str:
    if not CHEATSHEET.exists():
        return "❌ Cheatsheet bulunamadı."
    text = CHEATSHEET.read_text(encoding="utf-8")

    if section:
        # Bölüm bul
        pattern = f"## {section}"
        idx = text.lower().find(section.lower())
        if idx == -1:
            return f"❌ Bölüm bulunamadı: `{section}`"
        snippet = text[idx:idx+1000]
        return f"📖 **CC Features — {section}**\n\n{snippet}"

    # İlk 1500 karakter
    return f"📖 **Claude Code 2026 Cheatsheet**\n\n{text[:1500]}\n\n_Tam liste için `/cc-features [bolum]`_"


def list_new_features() -> str:
    if not REPO_DIR.exists():
        return "❌ claude-code-new-features repo bulunamadı."

    features = []
    for md in REPO_DIR.rglob("*.md"):
        if md.name not in ("README.md", "CHEATSHEET.md", "CLAUDE.md"):
            features.append(md.stem)

    lines = ["⚡ **Claude Code Yeni Özellikler (2026)**", ""]
    key_features = [
        "Parallel subagents — birden fazla agent aynı anda",
        "Agent memory scopes — user / project / local",
        "Coordinator mode — CLAUDE_CODE_COORDINATOR_MODE",
        "Swarm workers — swarmWorkerHandler",
        "Team Create/Delete tools",
        "SendMessage tool",
        "Hook types: PreToolUse, PostToolUse, Stop, UserPromptSubmit",
        "CLAUDE.md frontmatter (allowed_tools, model vb.)",
    ]
    for f in key_features:
        lines.append(f"  ✨ {f}")
    lines.append(f"\nRepo: `external-repos/claude-code-new-features-early-2026`")
    lines.append("`/cc-cheatsheet` ile tam referans")
    return "\n".join(lines)
