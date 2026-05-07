from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timezone
from typing import Any


CONFIDENCE_THRESHOLD = 0.8

INTENT_RULES: dict[str, dict[str, Any]] = {
    "research": {
        "persona": "mert",
        "strong": ["arastir", "ebay", "trendyol", "rakip", "pazar", "fiyat"],
        "support": ["karsilastir", "trend", "ozetle", "listele", "incele"],
    },
    "code": {
        "persona": "seda",
        "strong": ["kod", "python", "bug", "debug", "stack trace", "refactor", "api", "repo"],
        "support": ["incele", "duzelt", "fix", "test", "pr", "hata"],
    },
    "social": {
        "persona": "buse",
        "strong": ["instagram", "post", "reklam", "seo", "kampanya", "landing"],
        "support": ["copy", "icerik", "caption", "cta", "story", "paylasim"],
    },
    "aws": {
        "persona": "sabrican",
        "strong": ["aws", "ec2", "s3", "docker", "deploy", "kubernetes", "sunucu"],
        "support": ["listele", "restart", "log", "ci", "cd", "ops"],
    },
    "youtube": {
        "persona": "eren",
        "strong": ["youtube", "thumbnail", "transkript", "izlenme"],
        "support": ["video", "kanal", "shorts", "baslik"],
    },
    "strategy": {
        "persona": "sabri",
        "strong": ["strateji", "marka", "vizyon", "konumlandirma", "buyume", "offer"],
        "support": ["fikir", "roadmap", "plan", "konum", "hedef"],
    },
    "security": {
        "persona": "luna",
        "strong": ["guvenlik", "security", "audit", "zafiyet", "pentest", "secret", "token"],
        "support": ["log", "redact", "izin", "anahtar", "risk"],
    },
}

PERSONA_INTENTS = {
    intent_name: str(rule.get("persona") or "").strip()
    for intent_name, rule in INTENT_RULES.items()
    if str(rule.get("persona") or "").strip()
}

INTENT_KEYWORDS = {
    intent_name: [*rule.get("strong", []), *rule.get("support", [])]
    for intent_name, rule in INTENT_RULES.items()
}

_TURKISH_TRANSLATION = str.maketrans(
    {
        "ı": "i",
        "İ": "i",
        "ş": "s",
        "Ş": "s",
        "ğ": "g",
        "Ğ": "g",
        "ü": "u",
        "Ü": "u",
        "ö": "o",
        "Ö": "o",
        "ç": "c",
        "Ç": "c",
    }
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_text(value: str) -> str:
    text = str(value or "").strip().translate(_TURKISH_TRANSLATION).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9\s/]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _tokenize(normalized_text: str) -> list[str]:
    return [token for token in normalized_text.split(" ") if token]


def _keyword_matches(normalized_text: str, tokens: list[str], keyword: str) -> bool:
    clean_keyword = _normalize_text(keyword)
    if not clean_keyword:
        return False

    if " " in clean_keyword or "/" in clean_keyword:
        return clean_keyword in normalized_text

    if clean_keyword in tokens:
        return True

    if len(clean_keyword) <= 2:
        return False

    return any(token.startswith(clean_keyword) for token in tokens)


def _find_matches(normalized_text: str, keywords: list[str]) -> list[str]:
    tokens = _tokenize(normalized_text)
    matches: list[str] = []
    for keyword in keywords:
        clean_keyword = _normalize_text(keyword)
        if clean_keyword and _keyword_matches(normalized_text, tokens, clean_keyword):
            matches.append(clean_keyword)
    return matches


def _score_matches(strong_matches: list[str], support_matches: list[str]) -> float:
    if not strong_matches and not support_matches:
        return 0.0
    return min(0.97, 0.52 + (0.22 * len(strong_matches)) + (0.14 * len(support_matches)))


def detect_intent(text: str) -> tuple[str, float, list[str]]:
    normalized_text = _normalize_text(text)
    if not normalized_text or normalized_text.startswith("/"):
        return "general", 0.0, []

    best_intent = "general"
    best_score = 0.0
    best_matches: list[str] = []

    for intent_name, rule in INTENT_RULES.items():
        strong_matches = _find_matches(normalized_text, list(rule.get("strong") or []))
        support_matches = [
            match
            for match in _find_matches(normalized_text, list(rule.get("support") or []))
            if match not in strong_matches
        ]
        score = _score_matches(strong_matches, support_matches)
        combined_matches = [*strong_matches, *support_matches]

        if score > best_score:
            best_intent = intent_name
            best_score = score
            best_matches = combined_matches
            continue

        if score == best_score and len(combined_matches) > len(best_matches):
            best_intent = intent_name
            best_matches = combined_matches

    if best_score <= 0.0:
        return "general", 0.0, []

    return best_intent, round(best_score, 2), best_matches


def analyze_message(text: str, current_persona: str = "jarvis") -> dict[str, Any]:
    detected_intent, confidence, matches = detect_intent(text)
    current = str(current_persona or "jarvis").strip().lower() or "jarvis"
    target_persona = PERSONA_INTENTS.get(detected_intent)

    if confidence < CONFIDENCE_THRESHOLD:
        target_persona = None

    return {
        "raw_message": str(text or "").strip(),
        "detected_intent": detected_intent,
        "target_persona": target_persona,
        "confidence": confidence,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "auto_switched": bool(target_persona and target_persona != current),
        "current_persona": current,
        "matches": matches,
        "ts": _now_iso(),
    }


def route_to_persona(
    intent_result: dict[str, Any],
    current_persona: str,
    chat_id: int | None = None,
) -> str | None:
    del chat_id

    payload = intent_result if isinstance(intent_result, dict) else {}
    target_persona = str(payload.get("target_persona") or "").strip().lower()
    current = str(current_persona or payload.get("current_persona") or "jarvis").strip().lower() or "jarvis"

    try:
        confidence = float(payload.get("confidence") or 0.0)
    except (TypeError, ValueError):
        confidence = 0.0

    if not target_persona or confidence < CONFIDENCE_THRESHOLD:
        return None
    if target_persona == current:
        return None
    return target_persona


def format_switch_message(
    intent_result: dict[str, Any],
    persona: dict[str, Any] | None = None,
) -> str:
    payload = intent_result if isinstance(intent_result, dict) else {}
    detected_intent = str(payload.get("detected_intent") or "general").strip()
    persona_name = str(
        (persona or {}).get("name") or payload.get("target_persona") or "Jarvis"
    ).strip()
    intent_labels = {
        "research": "arastirma modu",
        "code": "kod modu",
        "social": "icerik modu",
        "aws": "ops modu",
        "youtube": "video modu",
        "strategy": "strateji modu",
        "security": "guvenlik modu",
    }
    return (
        f"{persona_name} moduna geciyorum - "
        f"{intent_labels.get(detected_intent, 'yardim modu')}."
    )


__all__ = [
    "CONFIDENCE_THRESHOLD",
    "INTENT_KEYWORDS",
    "INTENT_RULES",
    "PERSONA_INTENTS",
    "analyze_message",
    "detect_intent",
    "format_switch_message",
    "route_to_persona",
]
