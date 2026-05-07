from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

try:
    from server.skills.obsidian_sync_skill import get_obsidian_vault_dir
except ImportError:
    from obsidian_sync_skill import get_obsidian_vault_dir


ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT_DIR / "server" / "logs" / "buse_content.jsonl"
CONTENT_DIR = Path("personas/buse/content")
SUPPORTED_STYLES = ("instagram", "linkedin", "email", "telegram")
SUPPORTED_GOALS = ("dm_bait", "link_click", "comment_bait", "follow")

STYLE_PRESETS: dict[str, dict[str, str]] = {
    "instagram": {
        "amount": "5.000",
        "duration": "7 gun",
        "result": "daha cok DM almak",
        "secret": "ilk satirin teklif degil merak olmasi",
        "pain": "icerik var ama etkilesim yok",
        "solution": "tek teklifli bir akisa gecis",
    },
    "linkedin": {
        "amount": "25.000",
        "duration": "30 gun",
        "result": "daha nitelikli lead toplamak",
        "secret": "ilk paragrafta tek bir metrik kullanmak",
        "pain": "iyi urun olmasina ragmen talep daginik",
        "solution": "mesaj ve teklifin ayni hizada calismasi",
    },
    "email": {
        "amount": "12.000",
        "duration": "14 gun",
        "result": "geri donusleri toparlamak",
        "secret": "konu satirinda sonucu one almak",
        "pain": "mail gidiyor ama cevap gelmiyor",
        "solution": "kisa acilis ve net teklif yapisi",
    },
    "telegram": {
        "amount": "8.000",
        "duration": "10 gun",
        "result": "daha hizli geri donus almak",
        "secret": "ilk mesajda tek faydaya odaklanmak",
        "pain": "mesaj atiliyor ama aksiyon cikmiyor",
        "solution": "kisa, net ve tek kelimelik yanit akisi",
    },
}

CTA_PRESETS: dict[str, dict[str, str]] = {
    "instagram": {
        "comment_prefix": "Yorumlara",
        "dm_prefix": "DM'den",
        "dm_keyword": "PLAN",
        "comment_keyword": "LISTE",
        "value": "mini rehberi",
        "link_click": "Link bio'da. Tiklayip ornek akisi gorun.",
        "follow": "Bu tip icerikler icin takip et ve seriyi kacirma.",
    },
    "telegram": {
        "comment_prefix": "Sohbete",
        "dm_prefix": "Mesajdan",
        "dm_keyword": "AKIS",
        "comment_keyword": "OZET",
        "value": "kontrol listesini",
        "link_click": "Alttaki linke dokun, tam akisi ac.",
        "follow": "Kanalda kal; yeni icerikler geldikce ilk sen gor.",
    },
    "linkedin": {
        "comment_prefix": "Yorumlara",
        "dm_prefix": "Mesajdan",
        "dm_keyword": "CASE",
        "comment_keyword": "BRIEF",
        "value": "ornek case'i",
        "link_click": "Yoruma biraktigim linke tiklayin, detayi gorun.",
        "follow": "Benzer vaka analizleri icin profili takip edin.",
    },
}


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-") or "icerik"


def _normalize_style(style: str) -> str:
    candidate = str(style or "instagram").strip().lower()
    return candidate if candidate in SUPPORTED_STYLES else "instagram"


def _normalize_goal(goal: str) -> str:
    candidate = str(goal or "").strip().lower()
    return candidate if candidate in SUPPORTED_GOALS else ""


def _normalize_platform(platform: str) -> str:
    candidate = str(platform or "instagram").strip().lower()
    return candidate if candidate in CTA_PRESETS else "instagram"


def _log_event(action: str, payload: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "persona": "buse",
        "action": action,
        "payload": payload,
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def _resolve_vault_dir(vault_dir: str | Path | None = None) -> Path:
    candidate = Path(vault_dir).expanduser() if vault_dir is not None else get_obsidian_vault_dir()
    if candidate is None:
        raise FileNotFoundError("Obsidian vault path is not configured")
    resolved = candidate.expanduser().resolve(strict=False)
    if not resolved.exists() or not resolved.is_dir():
        raise FileNotFoundError(f"Obsidian vault path is not available: {resolved}")
    return resolved


def _relative_to_vault(path: Path, vault_root: Path) -> str:
    return path.resolve(strict=False).relative_to(vault_root).as_posix()


def _parse_brief_fields(
    product: str,
    audience: str | None,
    goal: str | None,
) -> tuple[str, str, str]:
    clean_product = str(product or "").strip()
    clean_audience = str(audience or "").strip()
    clean_goal = str(goal or "").strip()
    if clean_product and (not clean_audience or not clean_goal) and "|" in clean_product:
        parts = [part.strip() for part in clean_product.split("|", 2)]
        if len(parts) == 3:
            clean_product, clean_audience, clean_goal = parts
    return clean_product, clean_audience, clean_goal


def generate_hook(topic: str, style: str = "instagram") -> dict[str, Any]:
    clean_topic = str(topic or "").strip()
    normalized_style = _normalize_style(style)
    if not clean_topic:
        result = {
            "ok": False,
            "error": "topic_required",
            "message": "Konu bos olamaz.",
            "style": normalized_style,
        }
        _log_event("generate_hook", result)
        return result

    preset = STYLE_PRESETS[normalized_style]
    hooks = [
        f"{preset['amount']} TL'yi {preset['duration']}de {preset['result']}: {clean_topic}",
        f"{clean_topic} konusunda cogu kisinin bilmedigi sey: {preset['secret']}",
        f"Once: {preset['pain']}. Sonra: {clean_topic} ile {preset['solution']}.",
    ]
    result = {
        "ok": True,
        "topic": clean_topic,
        "style": normalized_style,
        "hooks": hooks,
    }
    _log_event("generate_hook", result)
    return result


def generate_cta(goal: str, platform: str = "instagram") -> dict[str, Any]:
    normalized_goal = _normalize_goal(goal)
    normalized_platform = _normalize_platform(platform)
    if not normalized_goal:
        result = {
            "ok": False,
            "error": "goal_required",
            "message": "Gecerli hedef gerekli: dm_bait, link_click, comment_bait, follow",
            "platform": normalized_platform,
        }
        _log_event("generate_cta", result)
        return result

    preset = CTA_PRESETS[normalized_platform]
    if normalized_goal == "comment_bait":
        cta = (
            f"{preset['comment_prefix']} '{preset['comment_keyword']}' yazin, "
            f"{preset['value']} gondereyim."
        )
    elif normalized_goal == "dm_bait":
        cta = (
            f"{preset['dm_prefix']} '{preset['dm_keyword']}' yazin, "
            f"{preset['value']} gondereyim."
        )
    elif normalized_goal == "link_click":
        cta = preset["link_click"]
    else:
        cta = preset["follow"]

    result = {
        "ok": True,
        "goal": normalized_goal,
        "platform": normalized_platform,
        "cta": cta,
    }
    _log_event("generate_cta", result)
    return result


def content_brief(
    product: str,
    audience: str | None = None,
    goal: str | None = None,
    *,
    style: str = "instagram",
    platform: str = "instagram",
    vault_dir: str | Path | None = None,
) -> dict[str, Any]:
    clean_product, clean_audience, clean_goal = _parse_brief_fields(product, audience, goal)
    if not clean_product or not clean_audience or not clean_goal:
        result = {
            "ok": False,
            "error": "brief_fields_required",
            "message": "Urun, kitle ve hedef gerekli. Ornek: urun | kitle | comment_bait",
        }
        _log_event("content_brief", result)
        return result

    hook_result = generate_hook(clean_product, style=style)
    if hook_result.get("ok") is False:
        return hook_result

    cta_result = generate_cta(clean_goal, platform=platform)
    if cta_result.get("ok") is False:
        return cta_result

    body_outline = [
        f"{clean_audience} icin ana problemi ilk 2 cumlede ac.",
        f"{clean_product} ile gelen tek buyuk faydayi netlestir.",
        "Mini ornek, sonuc veya sosyal kanit ekle.",
        f"{clean_goal.replace('_', ' ')} hedefine gecis yapan tek cagrili bir kapanis kur.",
    ]

    note_body = "\n".join(
        [
            f"# {clean_product}",
            "",
            f"- Kitle: {clean_audience}",
            f"- Hedef: {clean_goal}",
            "",
            "## Hook",
            str(hook_result["hooks"][0]),
            "",
            "## Body Outline",
            *[f"- {item}" for item in body_outline],
            "",
            "## CTA",
            str(cta_result["cta"]),
            "",
        ]
    )

    try:
        vault_root = _resolve_vault_dir(vault_dir)
        target_dir = (vault_root / CONTENT_DIR).resolve(strict=False)
        target_dir.mkdir(parents=True, exist_ok=True)
        product_slug = _slugify(clean_product)
        stamp = datetime.now().strftime("%Y-%m-%d")
        note_path = (target_dir / f"{stamp}_{product_slug}.md").resolve(strict=False)
        if vault_root not in note_path.parents and note_path != vault_root:
            raise ValueError("Target path escapes vault root")
        note_path.write_text(note_body, encoding="utf-8")
        saved_to = _relative_to_vault(note_path, vault_root)
    except Exception as exc:
        result = {
            "ok": False,
            "hook": str(hook_result["hooks"][0]),
            "body_outline": body_outline,
            "cta": str(cta_result["cta"]),
            "error": str(exc),
            "message": "Obsidian kaydi yapilamadi.",
        }
        _log_event("content_brief", result)
        return result

    result = {
        "ok": True,
        "hook": str(hook_result["hooks"][0]),
        "body_outline": body_outline,
        "cta": str(cta_result["cta"]),
        "saved_to": saved_to,
    }
    _log_event("content_brief", result)
    return result


__all__ = ["content_brief", "generate_cta", "generate_hook"]
