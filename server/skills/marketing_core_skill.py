"""Marketing Core skill — Buse persona üzerinden landing/copy/CTA/lead magnet üretir."""
from __future__ import annotations

from typing import Any


def _fallback(goal: str) -> str:
    return (
        f"MARKETING — {goal[:80]}\n"
        "- Headline: Değer önerisini 1 cümlede söyle\n"
        "- Subheadline: Hedef kitle + fayda\n"
        "- CTA: 'Ücretsiz dene' / 'Demo iste'\n"
        "- Lead magnet: 7 günlük ücretsiz deneme + kurulum rehberi PDF\n"
        "- Copy bloklari: problem → çözüm → kanit → sosyal kanit → aksiyon"
    )


def run_marketing_core(goal: str, context: dict[str, Any] | None = None) -> str:
    context = context or {}
    try:
        from skills.buse_content_skill import generate_content  # type: ignore
    except Exception:
        try:
            from server.skills.buse_content_skill import generate_content  # type: ignore
        except Exception:
            generate_content = None  # type: ignore

    if callable(generate_content):
        try:
            out = generate_content(goal, context=context)  # type: ignore[misc]
            if out:
                return f"MARKETING CORE — {goal[:80]}\n{out}"
        except Exception:
            pass
    return _fallback(goal)
