from __future__ import annotations

from typing import Any


def route_task(goal: str) -> dict[str, Any]:
    text = str(goal or "").strip().lower()
    result = {
        "tool": "jarvis",
        "label": "Jarvis",
        "reason": "Genel kontrol ve yonlendirme gorevi.",
        "confidence": "medium",
    }

    if any(token in text for token in ("site yap", "proje kur", "full project", "tam modul", "auth sistemi", "sifirdan")):
        return {
            "tool": "openhands",
            "label": "OpenHands",
            "reason": "Agir insaat ve tam proje kurulum isleri icin en uygun motor.",
            "confidence": "high",
        }

    if any(token in text for token in ("fix", "duzelt", "refactor", "rename", "kullanilmayan", "temizle")):
        return {
            "tool": "aider",
            "label": "Aider",
            "reason": "Hizli yama, kucuk/orta duzeltme ve repo ici temizleme icin uygun.",
            "confidence": "high",
        }

    if any(token in text for token in ("css", "sayfa", "yan menu", "ui", "duzenle", "edit", "update", "run")):
        return {
            "tool": "cline",
            "label": "Cline",
            "reason": "Interaktif gelistirme, dosya + terminal odakli duzeltmeler icin uygun.",
            "confidence": "high",
        }

    if any(token in text for token in ("generate", "batch", "50", "100", "test verisi", "test senaryosu", "seri uretim", "worker")):
        return {
            "tool": "codex",
            "label": "OpenCode / Codex",
            "reason": "Seri uretim ve hizli worker tipi isler icin uygun.",
            "confidence": "high",
        }

    if any(token in text for token in ("transcript", "youtube", "trend video", "scrape", "webden cek", "mcp", "analiz video")):
        return {
            "tool": "mcp",
            "label": "MCP / Ingestion",
            "reason": "Dis veri cekme, transcript ve scraping odakli isler icin uygun.",
            "confidence": "medium",
        }

    if any(token in text for token in ("design", "mimari", "architecture", "review", "analiz et", "reasoning", "buyuk analiz")):
        return {
            "tool": "claude",
            "label": "Claude",
            "reason": "Mimari, review, sentez ve derin dusunce gereken isler icin uygun.",
            "confidence": "high",
        }

    if any(token in text for token in ("simulate", "simulasyon", "god view", "reaction", "what if", "rol yap")):
        return {
            "tool": "jarvis_simulation",
            "label": "Jarvis Simulation",
            "reason": "Senaryo tabanli coklu ajan simulasyonu gerektiren isler.",
            "confidence": "medium",
        }

    return result


def build_tool_routing_report(goal: str) -> str:
    decision = route_task(goal)
    lines = [
        "TOOL ROUTING",
        f"Hedef: {goal[:120]}",
        f"Arac: {decision['label']} ({decision['tool']})",
        f"Guven: {decision['confidence']}",
        f"Gerekce: {decision['reason']}",
    ]
    try:
        from external_repo_registry import recommend_external_repos
    except Exception:
        try:
            from server.services.external_repo_registry import recommend_external_repos
        except Exception:
            recommend_external_repos = None  # type: ignore[assignment]
    if recommend_external_repos:
        try:
            repos = recommend_external_repos(
                goal,
                primary_tool=str(decision.get("tool") or ""),
                limit=3,
            )
        except Exception:
            repos = []
        if repos:
            lines.append("")
            lines.append("Repo onerileri:")
            for entry in repos:
                lines.append(
                    f"- {entry.get('label', '-')} [{entry.get('status', '-')}] -> {entry.get('path', '-')}"
                )
    return "\n".join(lines)
