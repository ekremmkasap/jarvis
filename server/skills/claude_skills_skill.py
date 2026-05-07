"""
Jarvis Skill — Claude Skills (223 production-ready skills)
external-repos/claude-skills/ içindeki skill'leri Jarvis'e sunar.
"""
import os, json
from pathlib import Path

REPO_DIR = Path(__file__).parent.parent.parent / "external-repos" / "claude-skills"


def _scan_skills():
    skills = {}
    if not REPO_DIR.exists():
        return skills
    for dept_dir in REPO_DIR.iterdir():
        if not dept_dir.is_dir() or dept_dir.name.startswith("."):
            continue
        dept = dept_dir.name
        skills[dept] = []
        for skill_dir in dept_dir.iterdir():
            if skill_dir.is_dir():
                skills[dept].append(skill_dir.name)
    return skills


def list_skills(dept: str = "") -> str:
    skills = _scan_skills()
    if not skills:
        return "❌ claude-skills repo bulunamadı"

    if dept:
        dept_key = next((k for k in skills if dept.lower() in k.lower()), None)
        if not dept_key:
            return f"❌ Departman bulunamadı: `{dept}`\nMevcut: {', '.join(skills.keys())}"
        items = skills[dept_key]
        lines = [f"🎯 **Claude Skills — {dept_key}** ({len(items)} skill)", ""]
        lines += [f"  • `{s}`" for s in sorted(items)[:20]]
        if len(items) > 20:
            lines.append(f"  ... +{len(items)-20} daha")
        return "\n".join(lines)

    lines = ["📦 **Claude Skills Kütüphanesi**", ""]
    total = 0
    for d, items in sorted(skills.items()):
        lines.append(f"  `{d}` — {len(items)} skill")
        total += len(items)
    lines.append(f"\nToplam: **{total} skill** | Kullanım: `/cs-liste [dept]`")
    return "\n".join(lines)


def use_skill(skill_name: str, context: str = "", call_llm=None) -> str:
    """Belirli bir skill'i context ile çalıştır."""
    skills = _scan_skills()
    found_path = None
    for dept, items in skills.items():
        if skill_name.lower() in [i.lower() for i in items]:
            found_path = REPO_DIR / dept / skill_name
            break

    if not found_path:
        return f"❌ Skill bulunamadı: `{skill_name}`\n`/cs-liste` ile tüm skill'lere bak."

    # SKILL.md veya README.md oku
    skill_md = found_path / "SKILL.md"
    if not skill_md.exists():
        skill_md = found_path / "README.md"
    if not skill_md.exists():
        return f"❌ Skill dosyası yok: `{skill_name}`"

    skill_content = skill_md.read_text(encoding="utf-8")[:2000]

    if not call_llm:
        return f"📋 **Skill: {skill_name}**\n\n{skill_content[:800]}"

    prompt = f"Bu skill'i kullanarak şu görevi yap:\n\nSkill:\n{skill_content}\n\nGörev: {context}\n\nTürkçe çıktı ver."
    try:
        result = call_llm(prompt)
        return f"⚡ **{skill_name}** → {context}\n\n{result}"
    except Exception as e:
        return f"❌ LLM hatası: {e}"


def search_skills(query: str) -> str:
    skills = _scan_skills()
    query_lower = query.lower()
    matches = []
    for dept, items in skills.items():
        for item in items:
            if query_lower in item.lower():
                matches.append(f"`{dept}/{item}`")
    if not matches:
        return f"🔍 Sonuç yok: `{query}`"
    lines = [f"🔍 **Arama: {query}** ({len(matches)} sonuç)", ""]
    lines += matches[:15]
    return "\n".join(lines)
