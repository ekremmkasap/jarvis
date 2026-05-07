"""
sabri_campaign_skill.py — Sabri (reklam ajansı persona) kampanya pipeline.

Mert Durmazer (Digital Academy) framework referansıyla:
  brief alma → copy üretim → görsel prompt → kampanya planı

Template-based; LLM bağımlılığı yok, offline çalışır.
"""
from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT_DIR / "state" / "agent_memory" / "sabri" / "briefs"
LOG_PATH = ROOT_DIR / "server" / "logs" / "sabri_campaign.jsonl"

SUPPORTED_PLATFORMS = ("meta", "google", "linkedin", "instagram", "tiktok")

CHAR_LIMITS: dict[str, dict[str, int]] = {
    "meta":      {"headline": 40,  "primary": 125, "description": 30},
    "google":    {"headline": 30,  "primary": 90,  "description": 90},
    "linkedin":  {"headline": 70,  "primary": 150, "description": 70},
    "instagram": {"headline": 50,  "primary": 180, "description": 50},
    "tiktok":    {"headline": 40,  "primary": 100, "description": 50},
}

TONE_STYLES: dict[str, dict[str, str]] = {
    "samimi":    {"hook": "Merhaba!", "cta_prefix": "Hadi birlikte", "voice": "arkadaş gibi"},
    "kurumsal":  {"hook": "Keşfedin.", "cta_prefix": "Hemen başlayın", "voice": "profesyonel ton"},
    "enerjik":   {"hook": "Dur bir saniye!", "cta_prefix": "Şimdi kaçırma", "voice": "enerjik ve çarpıcı"},
    "premium":   {"hook": "Seçkin bir deneyim.", "cta_prefix": "Ayrıcalığa adım atın", "voice": "lüks ton"},
}

VISUAL_STYLE_HINTS = {
    "samimi":   "warm natural lighting, candid lifestyle photography, golden hour",
    "kurumsal": "clean editorial studio, soft diffused light, neutral palette, modern minimalism",
    "enerjik":  "vibrant neon palette, dynamic motion blur, high-contrast editorial",
    "premium":  "cinematic rim lighting, matte black background, luxury product photography",
}

GOAL_KEYWORDS: dict[str, list[str]] = {
    "awareness":   ["tanınırlık", "marka bilinirliği", "yeni müşteri", "görünürlük", "awareness", "tanit"],
    "conversion":  ["satış", "dönüşüm", "sipariş", "satın al", "çevrim", "conversion", "satis"],
    "lead":        ["lead", "kayıt", "form", "demo", "iletişim", "başvuru", "basvuru"],
    "engagement":  ["etkileşim", "yorum", "paylaşım", "topluluk", "etkilesim"],
}

PLATFORM_MIX_BY_GOAL: dict[str, dict[str, int]] = {
    "awareness":  {"meta": 40, "google": 20, "instagram": 25, "tiktok": 15},
    "conversion": {"meta": 35, "google": 40, "instagram": 15, "tiktok": 10},
    "lead":       {"linkedin": 40, "google": 35, "meta": 25},
    "engagement": {"instagram": 40, "tiktok": 35, "meta": 25},
}


def _slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return slug or "musteri"


def _log_event(action: str, payload: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "persona": "sabri",
        "action": action,
        "payload": payload,
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _detect_goal(text: str) -> str:
    lower = text.lower()
    for goal, keywords in GOAL_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            return goal
    return "awareness"


def _detect_tone(text: str) -> str:
    lower = text.lower()
    if any(w in lower for w in ("premium", "lüks", "luks", "butik")):
        return "premium"
    if any(w in lower for w in ("kurumsal", "b2b", "profesyonel")):
        return "kurumsal"
    if any(w in lower for w in ("gençlik", "genclik", "tiktok", "gen-z", "z kuşağı", "z kusagi")):
        return "enerjik"
    return "samimi"


def _extract_budget(text: str) -> float | None:
    match = re.search(r"(\d[\d\.,]*)\s*(tl|₺|try|usd|\$)?", text.lower())
    if not match:
        return None
    raw = match.group(1).replace(".", "").replace(",", ".")
    try:
        return float(raw)
    except ValueError:
        return None


def _extract_audience(text: str) -> str:
    for sep in ("hedef kitle:", "kitle:", "audience:"):
        if sep in text.lower():
            idx = text.lower().index(sep) + len(sep)
            return text[idx:].split(".")[0].strip()
    if " için " in text:
        before = text.split(" için ")[0].strip().split(".")[-1]
        return before or "geniş kitle"
    return "geniş kitle"


def _brief_id_from(client: str, ts: datetime) -> str:
    return f"{_slugify(client)}_{ts.strftime('%Y%m%d_%H%M%S')}"


def _save_brief(brief: dict[str, Any]) -> Path:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    brief_id = brief["brief_id"]
    path = STATE_DIR / f"{brief_id}.json"
    path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load_brief(brief_id: str) -> dict[str, Any] | None:
    path = STATE_DIR / f"{brief_id}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def sabri_brief(client_note: str, client_name: str = "") -> dict[str, Any]:
    """Serbest müşteri notundan brief JSON çıkarır ve state'e kaydeder."""
    note = str(client_note or "").strip()
    if not note:
        return {"ok": False, "error": "note_required", "message": "Müşteri notu boş olamaz."}

    ts = datetime.utcnow()
    client = str(client_name or "").strip() or (note[:40].split(".")[0].strip() or "musteri")
    brief = {
        "brief_id": _brief_id_from(client, ts),
        "client": client,
        "created_at": ts.isoformat(),
        "raw_note": note[:1500],
        "brand": client,
        "audience": _extract_audience(note),
        "goal": _detect_goal(note),
        "tone": _detect_tone(note),
        "budget_try": _extract_budget(note),
    }
    saved_path = _save_brief(brief)
    try:
        brief["saved_to"] = str(saved_path.relative_to(ROOT_DIR).as_posix())
    except ValueError:
        brief["saved_to"] = str(saved_path)
    brief["ok"] = True
    _log_event("brief", {"brief_id": brief["brief_id"], "client": client})
    return brief


def sabri_copy(brief_id: str, platform: str = "meta") -> dict[str, Any]:
    """Brief'ten 3 alternatif kampanya copy üretir."""
    platform_key = str(platform or "meta").strip().lower()
    if platform_key not in SUPPORTED_PLATFORMS:
        return {"ok": False, "error": "unsupported_platform",
                "message": f"Desteklenen platformlar: {', '.join(SUPPORTED_PLATFORMS)}"}

    brief = _load_brief(brief_id)
    if brief is None:
        return {"ok": False, "error": "brief_not_found",
                "message": f"Brief bulunamadı: {brief_id}"}

    brand = brief.get("brand", "marka")
    audience = brief.get("audience", "geniş kitle")
    goal = brief.get("goal", "awareness")
    tone = brief.get("tone", "samimi")

    style = TONE_STYLES.get(tone, TONE_STYLES["samimi"])
    limits = CHAR_LIMITS[platform_key]

    variants = [
        {
            "angle": "problem-çözüm",
            "headline": f"{brand}: {audience} için çözüm"[:limits["headline"]],
            "primary":  f"{style['hook']} {audience} olarak en büyük zorluk ne? {brand} tam burada devreye giriyor. "
                        f"{style['cta_prefix']} farkı yaşayın."[:limits["primary"]],
            "cta":      "Hemen Keşfet" if goal == "awareness" else "Şimdi Başla",
        },
        {
            "angle": "sosyal kanıt",
            "headline": f"{brand} farkını kanıtladı"[:limits["headline"]],
            "primary":  f"Binlerce {audience} zaten {brand}'ı seçti. Siz de katılın — "
                        f"{style['cta_prefix']} sonuçları görün."[:limits["primary"]],
            "cta":      "İncelemeleri Gör" if goal != "lead" else "Demo Talep Et",
        },
        {
            "angle": "aciliyet/fırsat",
            "headline": f"{brand} — sınırlı fırsat"[:limits["headline"]],
            "primary":  f"{audience} için bu hafta özel. {brand} ile sonucu 7 günde yaşayın. "
                        f"{style['cta_prefix']} kaçırmayın."[:limits["primary"]],
            "cta":      "Hemen Al" if goal == "conversion" else "Katıl",
        },
    ]

    result = {
        "ok": True,
        "brief_id": brief_id,
        "platform": platform_key,
        "tone": tone,
        "voice": style["voice"],
        "char_limits": limits,
        "variants": variants,
    }
    _log_event("copy", {"brief_id": brief_id, "platform": platform_key, "variant_count": len(variants)})
    return result


def sabri_visual_prompt(brief_id: str) -> dict[str, Any]:
    """Brief'ten 3 görsel üretim prompt'u (Midjourney/DALL-E uyumlu)."""
    brief = _load_brief(brief_id)
    if brief is None:
        return {"ok": False, "error": "brief_not_found",
                "message": f"Brief bulunamadı: {brief_id}"}

    brand = brief.get("brand", "brand")
    audience = brief.get("audience", "audience")
    tone = brief.get("tone", "samimi")
    style_hint = VISUAL_STYLE_HINTS.get(tone, VISUAL_STYLE_HINTS["samimi"])

    prompts = [
        f"Hero product shot of {brand} for {audience}, {style_hint}, "
        f"shallow depth of field, sharp focus on product, commercial advertising, 8k, ultra detailed --ar 1:1",
        f"Lifestyle scene: {audience} enjoying {brand} in real-world context, {style_hint}, "
        f"natural candid expression, editorial magazine quality --ar 4:5",
        f"Bold graphic composition centered on {brand} logo, {style_hint}, "
        f"typography-friendly negative space on the right, modern campaign key visual --ar 16:9",
    ]

    result = {
        "ok": True,
        "brief_id": brief_id,
        "tone": tone,
        "style_hint": style_hint,
        "prompts": prompts,
    }
    _log_event("visual_prompt", {"brief_id": brief_id, "prompt_count": len(prompts)})
    return result


def sabri_campaign_plan(brief_id: str, budget_try: float, days: int = 30) -> dict[str, Any]:
    """Brief + bütçe + süreden kanal mix + takvim tablosu döner."""
    brief = _load_brief(brief_id)
    if brief is None:
        return {"ok": False, "error": "brief_not_found",
                "message": f"Brief bulunamadı: {brief_id}"}

    try:
        budget = float(budget_try)
        duration = max(1, int(days))
    except (TypeError, ValueError):
        return {"ok": False, "error": "invalid_numeric",
                "message": "Bütçe (TL) ve gün sayısı sayı olmalı."}

    goal = brief.get("goal", "awareness")
    mix = PLATFORM_MIX_BY_GOAL.get(goal, PLATFORM_MIX_BY_GOAL["awareness"])

    channel_allocation = []
    for channel, pct in mix.items():
        alloc = round(budget * pct / 100, 2)
        channel_allocation.append({
            "channel": channel,
            "percent": pct,
            "budget_try": alloc,
            "daily_try": round(alloc / duration, 2),
        })

    phases = [
        {"phase": "Hazırlık",      "days": "1-3",                  "focus": "creative + pixel/UTM kurulumu"},
        {"phase": "Launch",        "days": f"4-{min(duration, 10)}", "focus": "test bütçesi, hook varyant testi"},
        {"phase": "Ölçek",         "days": f"{min(duration-5, 11)}-{max(duration-3, 12)}",
                                    "focus": "kazanan creative'i 3x bütçe ile aç"},
        {"phase": "Optimize",      "days": f"son 3 gün",           "focus": "yorgun creative'i kapat, rapor çıkar"},
    ]

    kpi_targets = {
        "awareness":   {"cpm_max": 150, "reach_min": int(budget * 40),    "ctr_min_pct": 1.2},
        "conversion":  {"cpa_max": round(budget / max(10, budget / 50), 2), "roas_min": 2.5, "ctr_min_pct": 2.0},
        "lead":        {"cpl_max": round(budget * 0.015, 2),   "conversion_rate_min_pct": 3.0},
        "engagement":  {"cpe_max": 1.5, "engagement_rate_min_pct": 4.0},
    }.get(goal, {})

    result = {
        "ok": True,
        "brief_id": brief_id,
        "goal": goal,
        "budget_try": budget,
        "duration_days": duration,
        "channel_mix": channel_allocation,
        "phases": phases,
        "kpi_targets": kpi_targets,
    }
    _log_event("campaign_plan", {
        "brief_id": brief_id,
        "budget_try": budget,
        "duration_days": duration,
        "goal": goal,
    })
    return result


__all__ = [
    "sabri_brief",
    "sabri_copy",
    "sabri_visual_prompt",
    "sabri_campaign_plan",
    "SUPPORTED_PLATFORMS",
]
