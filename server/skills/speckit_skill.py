"""
Jarvis Skill — Spec Kit (github/spec-kit)
Spec-driven development: specify → plan → tasks → implement
"""
import json, os
from pathlib import Path
from datetime import datetime

SPECS_DIR = Path(__file__).parent.parent.parent / "specs"
REPO_DIR  = Path(__file__).parent.parent.parent / "external-repos" / "spec-kit"


def _load_templates():
    """spec-kit'ten specify/plan/tasks template'lerini yükle."""
    tpl = {}
    for name in ["specify", "plan", "tasks"]:
        p = REPO_DIR / "specs" / f"{name}.md"
        if p.exists():
            tpl[name] = p.read_text(encoding="utf-8")[:500]
    return tpl


def spec_specify(feature: str, call_llm=None) -> str:
    if not feature:
        return "Kullanim: /spec-specify [ozellik-adi]"
    spec_dir = SPECS_DIR / feature.replace(" ", "-").lower()
    spec_dir.mkdir(parents=True, exist_ok=True)
    spec_path = spec_dir / "specify.md"

    content = f"""# Spec: {feature}
Tarih: {datetime.now().strftime('%Y-%m-%d')}

## İstek
{feature}

## Kapsam
- [ ] Tanımlanacak

## Başarı Kriterleri
- [ ] Tanımlanacak

## Kapsam Dışı
- [ ] Tanımlanacak
"""
    if call_llm:
        try:
            llm_out = call_llm(
                f"'{feature}' özelliği için spec yaz: istek, kapsam, başarı kriterleri. Türkçe, kısa."
            )
            content = f"# Spec: {feature}\nTarih: {datetime.now().strftime('%Y-%m-%d')}\n\n{llm_out}"
        except Exception:
            pass

    spec_path.write_text(content, encoding="utf-8")
    return (
        f"📋 **Spec Oluşturuldu**\n"
        f"Özellik: `{feature}`\n"
        f"Dosya: `specs/{feature.replace(' ','-').lower()}/specify.md`\n\n"
        f"Sonraki adım: `/spec-plan {feature}`"
    )


def spec_plan(feature: str, call_llm=None) -> str:
    if not feature:
        return "Kullanim: /spec-plan [ozellik-adi]"
    spec_dir = SPECS_DIR / feature.replace(" ", "-").lower()
    specify_path = spec_dir / "specify.md"
    context = specify_path.read_text(encoding="utf-8") if specify_path.exists() else f"Özellik: {feature}"

    plan_content = f"# Plan: {feature}\n\n## Teknik Kararlar\n- [ ] \n\n## Entegrasyonlar\n- [ ] \n\n## Riskler\n- [ ] \n"
    if call_llm:
        try:
            plan_content = call_llm(
                f"Bu spec için teknik plan yaz:\n{context}\nTürkçe, madde madde."
            )
        except Exception:
            pass

    plan_path = spec_dir / "plan.md"
    spec_dir.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(plan_content, encoding="utf-8")
    return (
        f"🗺️ **Plan Oluşturuldu**\n`specs/{feature.replace(' ','-').lower()}/plan.md`\n\n"
        f"Sonraki: `/spec-tasks {feature}`"
    )


def spec_tasks(feature: str, call_llm=None) -> str:
    if not feature:
        return "Kullanim: /spec-tasks [ozellik-adi]"
    spec_dir = SPECS_DIR / feature.replace(" ", "-").lower()
    plan_path = spec_dir / "plan.md"
    context = plan_path.read_text(encoding="utf-8") if plan_path.exists() else f"Özellik: {feature}"

    tasks_content = f"# Görevler: {feature}\n\n- [ ] T1: \n- [ ] T2: \n- [ ] T3: \n"
    if call_llm:
        try:
            tasks_content = call_llm(
                f"Bu plandan uygulanabilir görev listesi çıkar:\n{context}\nTürkçe, checkbox formatında."
            )
        except Exception:
            pass

    tasks_path = spec_dir / "tasks.md"
    tasks_path.write_text(tasks_content, encoding="utf-8")
    return (
        f"✅ **Görevler Oluşturuldu**\n`specs/{feature.replace(' ','-').lower()}/tasks.md`\n\n"
        f"Sonraki: `/spec-implement {feature}`"
    )


def spec_list() -> str:
    if not SPECS_DIR.exists():
        return "📁 Henüz spec yok. `/spec-specify [ozellik]` ile başla."
    specs = [d.name for d in SPECS_DIR.iterdir() if d.is_dir()]
    if not specs:
        return "📁 Spec klasörü boş."
    lines = ["📋 **Mevcut Spec'ler:**", ""]
    for s in sorted(specs):
        files = list((SPECS_DIR / s).glob("*.md"))
        phase = "specify" if not files else files[-1].stem
        lines.append(f"  • `{s}` → faz: `{phase}`")
    return "\n".join(lines)
