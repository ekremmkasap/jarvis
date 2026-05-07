"""
Jarvis Skill — Agent Catalog
awesome-agent-skills + awesome-codex-subagents'tan agent/skill arama.
Jarvis Corp worker'larına otomatik skill ataması için kullanılır.
"""
import os, re
from pathlib import Path

REPO_SKILLS   = Path(__file__).parent.parent.parent / "external-repos" / "awesome-agent-skills"
REPO_CODEX    = Path(__file__).parent.parent.parent / "external-repos" / "awesome-codex-subagents"
REPO_AGENCY   = Path(__file__).parent.parent.parent / "external-repos" / ".." / ".." / ".." / "Desktop" / "Yeni klasör" / "agency-agents"
CLAUDE_SKILLS = Path(__file__).parent.parent.parent / "external-repos" / "claude-skills"


def search_agent(query: str) -> str:
    """Tüm kataloglarda agent/skill ara."""
    if not query:
        return "Kullanim: /agent-ara [rol veya konu]"

    query_lower = query.lower()
    results = []

    # 1. claude-skills
    if CLAUDE_SKILLS.exists():
        for dept in CLAUDE_SKILLS.iterdir():
            if dept.is_dir():
                for skill in dept.iterdir():
                    if skill.is_dir() and query_lower in skill.name.lower():
                        results.append(f"📦 `claude-skills/{dept.name}/{skill.name}`")

    # 2. awesome-codex-subagents
    if REPO_CODEX.exists():
        for toml in (REPO_CODEX / "categories").rglob("*.toml"):
            if query_lower in toml.stem.lower():
                results.append(f"🤖 `codex/{toml.parent.name}/{toml.stem}`")

    # 3. agency-agents
    agency_dir = Path("C:/Users/sergen/Desktop/Yeni klasör/agency-agents")
    if agency_dir.exists():
        for md in agency_dir.rglob("*.md"):
            if query_lower in md.stem.lower():
                results.append(f"🏢 `agency-agents/{md.parent.name}/{md.stem}`")

    if not results:
        return f"🔍 Sonuç yok: `{query}`\nDaha geniş terim dene."

    lines = [f"🔍 **Agent Ara: {query}** ({len(results)} sonuç)", ""]
    lines += results[:20]
    if len(results) > 20:
        lines.append(f"\n... +{len(results)-20} daha")
    return "\n".join(lines)


def recommend_for_task(task: str) -> str:
    """Göreve göre en uygun agent/skill öner."""
    task_lower = task.lower()

    # Keyword → kategori eşlemesi
    mappings = {
        ("reklam", "kampanya", "ads", "meta", "google ads"): ("marketing", "ad-creative"),
        ("seo", "anahtar kelime", "keyword"): ("marketing", "ai-seo"),
        ("kod", "python", "javascript", "debug", "backend"): ("engineering", "backend-developer"),
        ("test", "qa", "quality"): ("engineering", "code-reviewer"),
        ("strateji", "pazar", "rakip", "analiz"): ("strategy", "market-research"),
        ("video", "youtube", "script", "reel"): ("marketing", "content-creator"),
        ("güvenlik", "security", "audit"): ("engineering", "security-engineer"),
        ("deploy", "devops", "kubernetes", "docker"): ("engineering", "devops-automator"),
        ("satış", "sales", "email"): ("sales", "sales-outbound-strategist"),
        ("içerik", "blog", "copy"): ("marketing", "marketing-content-creator"),
    }

    recommendations = []
    for keywords, (dept, skill) in mappings.items():
        if any(kw in task_lower for kw in keywords):
            recommendations.append((dept, skill))

    if not recommendations:
        return f"💡 Öneri yok. `/agent-ara [konu]` ile manuel ara."

    lines = [f"💡 **Önerilen Agent'lar** — _{task[:50]}_", ""]
    for dept, skill in recommendations[:5]:
        # Codex'te mi var?
        codex_path = REPO_CODEX / "categories"
        for cat_dir in (codex_path.iterdir() if codex_path.exists() else []):
            toml = cat_dir / f"{skill}.toml"
            if toml.exists():
                lines.append(f"  🤖 `codex/{cat_dir.name}/{skill}` (Codex)")
                break
        else:
            lines.append(f"  📦 `claude-skills/{dept}/{skill}`")

    lines.append(f"\n`/cs-kullan [skill-adi] [gorev]` ile çalıştır")
    return "\n".join(lines)


def catalog_stats() -> str:
    stats = {}
    if CLAUDE_SKILLS.exists():
        total = sum(1 for d in CLAUDE_SKILLS.iterdir() if d.is_dir()
                    for s in d.iterdir() if s.is_dir())
        stats["claude-skills"] = total
    if REPO_CODEX.exists():
        total = sum(1 for f in (REPO_CODEX/"categories").rglob("*.toml"))
        stats["codex-subagents"] = total
    agency_dir = Path("C:/Users/sergen/Desktop/Yeni klasör/agency-agents")
    if agency_dir.exists():
        total = sum(1 for f in agency_dir.rglob("*.md") if f.name != "README.md")
        stats["agency-agents"] = total

    lines = ["📊 **Agent Kataloğu İstatistikleri**", ""]
    grand_total = 0
    for src, count in stats.items():
        lines.append(f"  `{src}`: {count} agent/skill")
        grand_total += count
    lines.append(f"\n**Toplam: {grand_total} agent** kullanıma hazır")
    return "\n".join(lines)
