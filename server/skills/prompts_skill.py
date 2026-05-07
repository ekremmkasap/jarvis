"""
Jarvis Skill — Prompts.chat (f/prompts.chat)
170+ kategorize edilmiş AI prompt şablonları.
"""
import json, re
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent.parent / "external-repos" / "prompts-chat"


def _load_prompts():
    prompts = []
    readme = REPO_DIR / "README.md"
    if not readme.exists():
        return prompts
    text = readme.read_text(encoding="utf-8", errors="ignore")
    # ## Act as ... pattern'lerini çıkar
    pattern = re.compile(r'## Act as (.+?)\n.*?> (.+?)(?=\n## |\Z)', re.DOTALL)
    for m in pattern.finditer(text):
        title = m.group(1).strip()
        prompt_text = m.group(2).strip()[:300]
        prompts.append({"title": title, "prompt": prompt_text})
    return prompts


def list_prompts(query: str = "") -> str:
    prompts = _load_prompts()
    if not prompts:
        return "❌ Prompts repo bulunamadı veya boş."

    if query:
        matches = [p for p in prompts if query.lower() in p["title"].lower()]
        if not matches:
            return f"🔍 Sonuç yok: `{query}`"
        lines = [f"🔍 **Prompt Ara: {query}** ({len(matches)} sonuç)", ""]
        for p in matches[:10]:
            lines.append(f"  • **{p['title']}**")
            lines.append(f"    _{p['prompt'][:100]}..._")
            lines.append("")
        return "\n".join(lines)

    lines = [f"📝 **Prompts Kataloğu** ({len(prompts)} şablon)", ""]
    for p in prompts[:20]:
        lines.append(f"  • {p['title']}")
    if len(prompts) > 20:
        lines.append(f"\n... +{len(prompts)-20} daha | `/prompt-ara [konu]` ile ara")
    return "\n".join(lines)


def get_prompt(title: str) -> str:
    prompts = _load_prompts()
    match = next((p for p in prompts if title.lower() in p["title"].lower()), None)
    if not match:
        return f"❌ Prompt bulunamadı: `{title}`\n`/prompt-liste` ile tüm şablonlara bak."
    return (
        f"📝 **{match['title']}**\n\n"
        f"```\n{match['prompt'][:1000]}\n```\n\n"
        f"Bu promptu kopyala ve AI'a ver."
    )
