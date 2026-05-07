"""
Jarvis Skill — Claude Code Hooks Mastery
Pre/Post tool hook yönetimi + meta-agent + team validation.
"""
import json, os
from pathlib import Path

REPO_DIR  = Path(__file__).parent.parent.parent / "external-repos" / "claude-code-hooks-mastery"
HOOKS_DIR = Path(__file__).parent.parent.parent / ".claude" / "hooks"
SETTINGS  = Path(__file__).parent.parent.parent / ".claude" / "settings.json"


def _load_settings():
    if SETTINGS.exists():
        return json.loads(SETTINGS.read_text(encoding="utf-8"))
    return {}


def _save_settings(data):
    SETTINGS.parent.mkdir(parents=True, exist_ok=True)
    SETTINGS.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def hooks_status() -> str:
    cfg = _load_settings()
    hooks = cfg.get("hooks", {})
    lines = ["🔗 **Claude Code Hooks Durumu**", ""]
    if not hooks:
        lines.append("Aktif hook yok.")
        lines.append("\n`/hook-ekle [pre|post] [tool] [komut]` ile ekle")
        return "\n".join(lines)
    for event, items in hooks.items():
        lines.append(f"**{event}:**")
        if isinstance(items, list):
            for h in items:
                lines.append(f"  • `{h.get('command','?')}`")
        lines.append("")
    return "\n".join(lines)


def hooks_list_examples() -> str:
    """repo'daki örnek hook'ları listele."""
    examples = []
    if REPO_DIR.exists():
        for f in REPO_DIR.rglob("*.py"):
            if "hook" in f.name.lower():
                examples.append(f.relative_to(REPO_DIR))
        for f in REPO_DIR.rglob("*.sh"):
            if "hook" in f.name.lower():
                examples.append(f.relative_to(REPO_DIR))

    lines = ["📚 **Hook Örnekleri** (claude-code-hooks-mastery)", ""]
    if examples:
        for e in examples[:15]:
            lines.append(f"  • `{e}`")
    else:
        lines += [
            "Temel hook tipleri:",
            "  • `PreToolUse` — araç çağrısından önce",
            "  • `PostToolUse` — araç çağrısından sonra",
            "  • `Stop` — Claude durduğunda",
            "  • `UserPromptSubmit` — prompt gönderildiğinde",
        ]
    lines.append(f"\nRepo: `external-repos/claude-code-hooks-mastery`")
    return "\n".join(lines)


def add_hook(event: str, command: str) -> str:
    """settings.json'a hook ekle."""
    valid_events = {"PreToolUse", "PostToolUse", "Stop", "UserPromptSubmit", "Notification"}
    # normalize
    event_map = {
        "pre": "PreToolUse", "pretool": "PreToolUse", "pretooluse": "PreToolUse",
        "post": "PostToolUse", "posttool": "PostToolUse", "posttooluse": "PostToolUse",
        "stop": "Stop", "durdur": "Stop",
        "prompt": "UserPromptSubmit", "submit": "UserPromptSubmit",
    }
    event_key = event_map.get(event.lower(), event)
    if event_key not in valid_events:
        return f"❌ Geçersiz event: `{event}`\nGeçerli: {', '.join(valid_events)}"

    cfg = _load_settings()
    if "hooks" not in cfg:
        cfg["hooks"] = {}
    if event_key not in cfg["hooks"]:
        cfg["hooks"][event_key] = []
    cfg["hooks"][event_key].append({"command": command})
    _save_settings(cfg)
    return f"✅ Hook eklendi: `{event_key}` → `{command}`"
