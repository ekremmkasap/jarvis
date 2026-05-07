from __future__ import annotations

import json
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT_DIR / "config" / "skill_registry.json"
SKILLS_DIR = ROOT_DIR / "server" / "skills"
SECTION_ORDER = ("core", "research", "restricted", "excluded")


def _load_registry() -> dict[str, list[dict[str, str]]]:
    if not CONFIG_PATH.exists():
        return {section: [] for section in SECTION_ORDER}
    with CONFIG_PATH.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    registry: dict[str, list[dict[str, str]]] = {}
    for section in SECTION_ORDER:
        raw_items = payload.get(section, [])
        if isinstance(raw_items, list):
            registry[section] = [item for item in raw_items if isinstance(item, dict)]
        else:
            registry[section] = []
    return registry


def _humanize(skill_name: str) -> str:
    return skill_name.replace("_", " ").replace("-", " ").title()


def _discover_active_skills() -> list[dict[str, str]]:
    skills: list[dict[str, str]] = []
    for path in sorted(SKILLS_DIR.glob("*_skill.py")):
        if path.name == "skill_registry_skill.py":
            continue
        skill_id = path.stem.replace("_skill", "").replace("_", "-")
        skills.append(
            {
                "id": skill_id,
                "name": _humanize(path.stem.replace("_skill", "")),
                "status": "active",
                "target": str(path.relative_to(ROOT_DIR)).replace("\\", "/"),
            }
        )
    return skills


def _format_entry(entry: dict[str, str]) -> str:
    label = entry.get("name") or entry.get("id") or "unknown"
    skill_id = entry.get("id", "-")
    status = entry.get("status", "-")
    target = entry.get("target", "").strip()
    note = entry.get("note", "").strip()

    parts = [f"- `{skill_id}` | {label} | `{status}`"]
    if target:
        parts.append(f"-> `{target}`")
    if note:
        parts.append(f"({note})")
    return " ".join(parts)


def _format_section(title: str, items: list[dict[str, str]]) -> str:
    if not items:
        return f"*{title}*\n- Kayit yok"
    lines = [f"*{title}* ({len(items)})"]
    lines.extend(_format_entry(item) for item in items)
    return "\n".join(lines)


def _search_entries(
    query: str,
    active_skills: list[dict[str, str]],
    registry: dict[str, list[dict[str, str]]],
) -> list[dict[str, str]]:
    query_lower = query.lower()
    results: list[dict[str, str]] = []

    for item in active_skills:
        haystack = " ".join(
            [
                item.get("id", ""),
                item.get("name", ""),
                item.get("target", ""),
                item.get("status", ""),
            ]
        ).lower()
        if query_lower in haystack:
            result = dict(item)
            result["section"] = "active"
            results.append(result)

    for section in SECTION_ORDER:
        for item in registry.get(section, []):
            haystack = " ".join(
                [
                    item.get("id", ""),
                    item.get("name", ""),
                    item.get("target", ""),
                    item.get("status", ""),
                    item.get("note", ""),
                ]
            ).lower()
            if query_lower in haystack:
                result = dict(item)
                result["section"] = section
                results.append(result)
    return results


def _search_external_catalog(query: str) -> str:
    try:
        from agent_catalog_skill import search_agent

        return search_agent(query)
    except Exception:
        return ""


def _catalog_stats() -> str:
    try:
        from agent_catalog_skill import catalog_stats

        return catalog_stats()
    except Exception:
        return ""


def _render_full_registry(
    active_skills: list[dict[str, str]],
    registry: dict[str, list[dict[str, str]]],
) -> str:
    lines = [
        "*Jarvis Skill Registry*",
        "",
        f"Aktif skill: {len(active_skills)}",
        f"Curated kayit: {sum(len(registry.get(section, [])) for section in SECTION_ORDER)}",
        "",
        _format_section("Active", active_skills),
    ]
    for section in SECTION_ORDER:
        lines.extend(["", _format_section(section.title(), registry.get(section, []))])

    stats = _catalog_stats()
    if stats:
        lines.extend(["", stats])

    return "\n".join(lines)


def _render_section(section: str, registry: dict[str, list[dict[str, str]]]) -> str:
    return _format_section(section.title(), registry.get(section, []))


def _render_search(
    query: str,
    active_skills: list[dict[str, str]],
    registry: dict[str, list[dict[str, str]]],
) -> str:
    if not query:
        return "Kullanim: /skills ara [kelime]"

    results = _search_entries(query, active_skills, registry)
    lines = [f"*Skill Arama:* `{query}`", ""]
    if results:
        lines.append(f"Registry sonucu: {len(results)}")
        for item in results[:30]:
            section = item.get("section", "registry")
            lines.append(f"{_format_entry(item)} [{section}]")
    else:
        lines.append("Registry sonucu bulunamadi.")

    external = _search_external_catalog(query)
    if external:
        lines.extend(["", external])

    return "\n".join(lines)


def run(args: str = "", context: dict | None = None) -> str:
    del context
    registry = _load_registry()
    active_skills = _discover_active_skills()
    normalized = (args or "").strip()
    if not normalized:
        return _render_full_registry(active_skills, registry)

    lowered = normalized.lower()
    if lowered in SECTION_ORDER:
        return _render_section(lowered, registry)

    if lowered.startswith("ara"):
        _, _, query = normalized.partition(" ")
        return _render_search(query.strip(), active_skills, registry)

    return _render_search(normalized, active_skills, registry)
