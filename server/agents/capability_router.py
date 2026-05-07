"""
Jarvis Corp — Capability Router
"Bu işi hangi repo/skill yapmalı?" sorusunu cevaplar.
Repolar bu router üzerinden birbirine bağlanır.
"""
import json
from pathlib import Path

REGISTRY_PATH = Path(__file__).parent.parent.parent / "config" / "capability_registry.json"


def _load_registry():
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return json.load(f)


def route(task: str, department: str = "") -> dict:
    """
    Görev metnine göre en uygun repo + skill + komut öner.
    Returns: {"repo": str, "skill": str, "command": str, "alternatives": [...]}
    """
    registry = _load_registry()
    task_lower = task.lower()
    cap_map = registry.get("capability_map", {})
    repos = registry.get("repos", {})

    # Capability eşleştirme
    matched_caps = []
    for cap, cap_repos in cap_map.items():
        if any(word in task_lower for word in cap.split("-")):
            matched_caps.extend(cap_repos)

    # Keyword → repo direkt eşleştirme
    keyword_repo = {
        "kod": "aider", "code": "aider", "python": "aider", "debug": "aider",
        "vscode": "cline", "cline": "cline",
        "docker": "openhands", "sandbox": "openhands", "özerk": "openhands",
        "araştır": "devika", "research": "devika",
        "ekip": "crewai", "crew": "crewai", "çok ajan": "crewai",
        "swarm": "swarms", "paralel": "swarms",
        "youtube": "youtube-transcript-api", "transkript": "youtube-transcript-api",
        "spec": "spec-kit", "plan": "spec-kit",
        "hook": "claude-code-hooks-mastery",
        "prompt": "prompts-chat",
        "skill ara": "awesome-agent-skills",
        "otomasyon": "CLI-Anything", "komut": "bypass-core",
        "izin": "bypass-core", "güvenlik": "bypass-core",
        "reklam": "claude-skills", "pazarlama": "claude-skills",
        "yönlendir": "ClawRouter", "router": "ClawRouter",
        "iş": "paperclip", "girişim": "paperclip",
    }

    primary_repo = None
    for kw, repo in keyword_repo.items():
        if kw in task_lower:
            primary_repo = repo
            break

    if not primary_repo and matched_caps:
        primary_repo = matched_caps[0]

    if not primary_repo:
        primary_repo = "bypass-core"  # default

    repo_data = repos.get(primary_repo, {})
    alternatives = list(set(matched_caps) - {primary_repo})[:3]

    return {
        "repo": primary_repo,
        "skill": repo_data.get("skill", ""),
        "commands": repo_data.get("commands", []),
        "primary_command": repo_data.get("commands", ["/swarm"])[0],
        "department": repo_data.get("department", "operations"),
        "works_with": repo_data.get("works_with", []),
        "alternatives": alternatives,
        "capabilities": repo_data.get("capabilities", [])
    }


def get_repo_network(repo_name: str) -> str:
    """Bir reponun iletişim ağını göster."""
    registry = _load_registry()
    repos = registry.get("repos", {})
    repo = repos.get(repo_name)
    if not repo:
        return f"❌ Repo bulunamadı: `{repo_name}`"

    works_with = repo.get("works_with", [])
    lines = [
        f"🔗 **{repo_name} — Bağlantı Ağı**",
        f"Durum: `{repo.get('status','?')}`",
        f"Departman: `{repo.get('department','?')}`",
        f"Yetenekler: {', '.join(repo.get('capabilities',[])[:4])}",
        f"Komutlar: {' '.join(repo.get('commands',[]))}",
        "",
        "**İletişim kurduğu repolar:**"
    ]
    for r in works_with:
        partner = repos.get(r, {})
        status_icon = "🟢" if partner.get("status") == "integrated" else "🔵"
        lines.append(f"  {status_icon} `{r}` — {', '.join(partner.get('capabilities',[])[:2])}")
    return "\n".join(lines)


def full_network_map() -> str:
    """Tüm repo ağını görselleştir."""
    registry = _load_registry()
    repos = registry.get("repos", {})

    dept_groups = {}
    for name, data in repos.items():
        dept = data.get("department", "other")
        dept_groups.setdefault(dept, []).append((name, data))

    dept_emoji = {
        "engineering": "⚙️", "marketing": "📣", "operations": "🔄",
        "strategy": "🎯", "security": "🔒", "all": "🌐", "other": "📦"
    }

    lines = ["🕸️ **Jarvis Corp — Repo Ağ Haritası**", ""]
    total = 0
    for dept, items in sorted(dept_groups.items()):
        em = dept_emoji.get(dept, "📦")
        lines.append(f"{em} **{dept.upper()}**")
        for name, data in items:
            st = "🟢" if data.get("status") == "integrated" else "🔵"
            cmds = " ".join(data.get("commands", [])[:2])
            lines.append(f"  {st} `{name}` → {cmds}")
            total += 1
        lines.append("")

    lines.append(f"Toplam: **{total} repo** entegre")
    return "\n".join(lines)


def recommend_pipeline(goal: str) -> str:
    """Hedef için çok-repo pipeline öner."""
    task_lower = goal.lower()
    pipelines = {
        "reklam kampanyası": ["devika", "claude-skills", "prompts-chat", "bypass-core"],
        "kod yaz":           ["spec-kit", "aider", "cline", "bypass-core"],
        "youtube":           ["youtube-transcript-api", "devika", "claude-skills"],
        "araştır":           ["devika", "paperclip", "awesome-agent-skills"],
        "çok ajan":          ["crewai", "swarms", "bypass-core"],
    }

    matched = None
    for key, pipeline in pipelines.items():
        if any(word in task_lower for word in key.split()):
            matched = (key, pipeline)
            break

    if not matched:
        r = route(goal)
        return (
            f"🔀 **Önerilen Repo:** `{r['repo']}`\n"
            f"Komut: `{r['primary_command']} {goal}`\n"
            f"Alternatifler: {', '.join(r['alternatives'])}"
        )

    key, pipeline = matched
    lines = [f"🔀 **Pipeline: {key}** → {goal[:40]}", ""]
    for i, repo in enumerate(pipeline, 1):
        registry = _load_registry()
        data = registry["repos"].get(repo, {})
        cmd = data.get("commands", ["?"])[0]
        lines.append(f"  {i}. `{repo}` → `{cmd}`")
    return "\n".join(lines)
