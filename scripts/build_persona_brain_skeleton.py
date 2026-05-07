"""Build JARVIS-Brain/personas/<id>/ skeleton from config/agents.yaml.

Idempotent: reruns do not overwrite existing non-identity files.
Only 00-Identity.md and skill-ref index are always regenerated from config.
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTS_YAML = REPO_ROOT / "config" / "agents.yaml"

DEFAULT_VAULT = Path("C:/Users/sergen/Desktop/JARVIS-Brain")
VAULT = Path(os.environ.get("OBSIDIAN_VAULT_PATH") or DEFAULT_VAULT)

SUBDIRS = [
    "02-Knowledge",
    "03-Projects",
    "04-Memory",
    "05-Skills-Refs",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def _identity_markdown(pid: str, p: dict) -> str:
    name = p.get("name", pid)
    role = p.get("role", "")
    color = p.get("color", "")
    voice = p.get("voice", "")
    slot = p.get("codex_slot", "")
    greeting = p.get("greeting", "")
    system_prompt = str(p.get("system_prompt", "")).strip()
    skills = p.get("skills", []) or []
    sub_agents = p.get("sub_agents", []) or []
    triggers = p.get("triggers", []) or []
    handoff = p.get("handoff_targets", []) or []
    tone = p.get("tone_guide", {}) or {}
    limits = p.get("domain_limits", {}) or {}
    llm = p.get("llm_profile", {}) or {}
    req_flag = p.get("requires_flag", "") or ""

    restricted = limits.get("restricted_topics", []) or []
    fallback = limits.get("fallback_persona", "")

    lines = [
        "---",
        f"persona_id: {pid}",
        f"name: {name}",
        f"role: {role}",
        f"voice: {voice}",
        f"color: '{color}'",
        f"codex_slot: {slot}",
        f"requires_flag: {req_flag or 'none'}",
        f"generated_at: {_now_iso()}",
        "---",
        "",
        f"# {name} — Dijital Kimlik",
        "",
        f"**Rol**: {role}",
        f"**Ses**: {voice} | **Renk**: {color} | **Codex Slot**: {slot}",
        "",
    ]
    if req_flag:
        lines += [f"> **Erişim**: Bu persona yalnızca `{req_flag}=1` ile görünür (internal).", ""]

    lines += [
        "## Karşılama",
        f"> {greeting}",
        "",
        "## Tetikleyiciler",
        ", ".join(f"`{t}`" for t in triggers) or "_(tanımlanmadı)_",
        "",
        "## Yetki Alanı",
        "",
        f"**Beceriler ({len(skills)})**: " + (", ".join(skills) if skills else "_(yok)_"),
        "",
        f"**Alt Ajanlar ({len(sub_agents)})**: " + (", ".join(sub_agents) if sub_agents else "_(yok)_"),
        "",
        f"**Handoff hedefleri**: " + (", ".join(handoff) if handoff else "_(yok)_"),
        "",
        "## Ton Rehberi",
        f"- Formality: {tone.get('formality', '-')}",
        f"- Technical depth: {tone.get('technical_depth', '-')}",
        f"- Emoji: {tone.get('emoji_use', False)}",
        "",
        "## Sınırlar",
        f"- Yasak konular: {', '.join(restricted) if restricted else '_(yok)_'}",
        f"- Fallback persona: `{fallback or '-'}`",
        "",
        "## LLM Profili",
        f"- Provider: `{llm.get('provider', '-')}` / Model: `{llm.get('model', '-')}`",
        f"- Fallback model: `{llm.get('fallback_model', '-')}`",
        f"- Model chain: `{llm.get('model_chain', '-')}`",
        "",
        "## Sistem Promptu (canonical)",
        "",
        "```",
        system_prompt or "(tanımlı değil)",
        "```",
        "",
        "---",
        "",
        "> Bu dosya `config/agents.yaml` üzerinden otomatik üretilir. Elle düzenleme **yapılmaz**; değişiklikler yaml'a yazılır.",
        "",
    ]
    return "\n".join(lines)


def _seed_daily_log(pid: str, name: str) -> str:
    return (
        f"# {name} — Günlük Log\n\n"
        "> Her gün bu personanın aldığı kararlar, başlattığı işler, handoff ettiği görevler buraya append edilir.\n"
        "> Format: `### YYYY-MM-DD HH:MM UTC\\n- olay\\n- aksiyon`\n\n"
        f"### {_now_iso()}\n"
        f"- Persona dijital beyin iskeleti oluşturuldu.\n"
    )


def _seed_readme(pid: str, name: str, purpose: str) -> str:
    return (
        f"# {name} — {purpose}\n\n"
        f"> `JARVIS-Brain/personas/{pid}/` altındaki bu klasörün amacı: {purpose.lower()}.\n"
        "> Dosya isimlendirme: `YYYY-MM-DD-kisa-baslik.md` veya konuya göre klasörleme.\n"
    )


def _skills_index(pid: str, p: dict) -> str:
    name = p.get("name", pid)
    skills = p.get("skills", []) or []
    sub_agents = p.get("sub_agents", []) or []
    surfaces = p.get("skill_surfaces", []) or []
    lines = [
        f"# {name} — Skill Referansları",
        "",
        "Bu klasör **kullanılan skill çıktılarının index'i**. Her skill çağrısı sonrası sonuç özeti buraya atılır.",
        "",
        "## Aktif Beceriler",
    ]
    if skills:
        lines += [f"- `{s}`" for s in skills]
    else:
        lines += ["_(yok)_"]
    lines += ["", "## Alt Ajanlar"]
    if sub_agents:
        lines += [f"- `{s}`" for s in sub_agents]
    else:
        lines += ["_(yok)_"]
    lines += ["", "## Skill Surface'leri"]
    if surfaces:
        lines += [f"- `{s}`" for s in surfaces]
    else:
        lines += ["_(yok)_"]
    lines += [
        "",
        "## Son Çağrılar",
        "",
        "_(henüz yok — her skill çağrısı buraya yeni satır ekler)_",
        "",
    ]
    return "\n".join(lines)


def build(vault_root: Path = VAULT) -> dict:
    if not AGENTS_YAML.exists():
        raise SystemExit(f"config/agents.yaml bulunamadı: {AGENTS_YAML}")

    data = yaml.safe_load(AGENTS_YAML.read_text(encoding="utf-8")) or {}
    personas = data.get("personas", {}) or {}
    if not personas:
        raise SystemExit("agents.yaml içinde 'personas:' bloğu boş.")

    root = vault_root / "personas"
    root.mkdir(parents=True, exist_ok=True)

    report = {"vault": str(vault_root), "personas": [], "created": 0, "updated": 0, "skipped": 0}

    for pid, p in personas.items():
        name = p.get("name", pid)
        pdir = root / pid
        pdir.mkdir(parents=True, exist_ok=True)

        # 00-Identity.md — always overwrite from yaml (authoritative)
        identity = pdir / "00-Identity.md"
        identity.write_text(_identity_markdown(pid, p), encoding="utf-8")
        ident_action = "updated"

        # 01-Daily-Log.md — create only if missing
        log = pdir / "01-Daily-Log.md"
        if not log.exists():
            log.write_text(_seed_daily_log(pid, name), encoding="utf-8")
            log_action = "created"
        else:
            log_action = "kept"

        # subdirs with README
        purposes = {
            "02-Knowledge": "Domain bilgisi (konu notları, terimler, kaynaklar)",
            "03-Projects": "Aktif projeler (müşteri işleri, kampanyalar, araştırmalar)",
            "04-Memory": "Konuşma özetleri (günlük dosyalar: YYYY-MM-DD.md)",
        }
        for sub in ["02-Knowledge", "03-Projects", "04-Memory"]:
            subdir = pdir / sub
            subdir.mkdir(exist_ok=True)
            readme = subdir / "README.md"
            if not readme.exists():
                readme.write_text(_seed_readme(pid, name, purposes[sub]), encoding="utf-8")

        # 05-Skills-Refs — always regen index (authoritative from config)
        skillref_dir = pdir / "05-Skills-Refs"
        skillref_dir.mkdir(exist_ok=True)
        (skillref_dir / "README.md").write_text(_skills_index(pid, p), encoding="utf-8")

        report["personas"].append({
            "id": pid,
            "path": str(pdir),
            "identity": ident_action,
            "daily_log": log_action,
        })
        if log_action == "created":
            report["created"] += 1
        else:
            report["skipped"] += 1

    return report


if __name__ == "__main__":
    rep = build()
    print(f"Vault: {rep['vault']}")
    print(f"Processed {len(rep['personas'])} personas")
    for entry in rep["personas"]:
        print(f"  [{entry['id']}] {entry['path']} — identity={entry['identity']}, daily_log={entry['daily_log']}")
