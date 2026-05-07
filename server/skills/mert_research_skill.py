from __future__ import annotations

import json
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from server.skills.obsidian_sync_skill import get_obsidian_vault_dir
except ImportError:  # pragma: no cover
    from obsidian_sync_skill import get_obsidian_vault_dir


SERVER_DIR = Path(__file__).resolve().parents[1]
LOG_PATH = SERVER_DIR / "logs" / "mert_research.jsonl"
DUCKDUCKGO_ENDPOINT = "https://api.duckduckgo.com/"
HEADERS = {
    "User-Agent": "Jarvis-Mert/1.0",
    "Accept": "application/json",
}
MAX_RESULTS = 5
MAX_TOTAL_CHARS = 3000
RATE_LIMIT_SECONDS = 2.0

_RATE_LIMIT_LOCK = Lock()
_LAST_SEARCH_AT = 0.0
_sleep = time.sleep
_monotonic = time.monotonic


def _slugify(value: str) -> str:
    text = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    safe = []
    for ch in text:
        if ch.isalnum():
            safe.append(ch)
        elif ch in {" ", "-", "_"}:
            safe.append("-")
    slug = "".join(safe).strip("-")
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug or "arastirma"


def _flatten_related_topics(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    flat: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("Topics"), list):
            flat.extend(_flatten_related_topics(item["Topics"]))
            continue
        if item.get("Text") or item.get("FirstURL"):
            flat.append(item)
    return flat


def _respect_rate_limit() -> None:
    global _LAST_SEARCH_AT

    with _RATE_LIMIT_LOCK:
        now = _monotonic()
        wait_seconds = RATE_LIMIT_SECONDS - (now - _LAST_SEARCH_AT)
        if _LAST_SEARCH_AT > 0 and wait_seconds > 0:
            _sleep(wait_seconds)
            now = _monotonic()
        _LAST_SEARCH_AT = now


def _log_search(
    query: str,
    *,
    status: str,
    result_count: int,
    error: str | None = None,
) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "persona": "mert",
        "query": str(query or "").strip(),
        "status": status,
        "result_count": int(result_count or 0),
    }
    if error:
        payload["error"] = str(error)[:500]

    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def _fetch_duckduckgo_payload(query: str) -> dict[str, Any]:
    params = urlencode(
        {
            "q": query,
            "format": "json",
            "no_html": "1",
            "no_redirect": "1",
            "skip_disambig": "1",
        }
    )
    request = Request(f"{DUCKDUCKGO_ENDPOINT}?{params}", headers=HEADERS)
    with urlopen(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _build_result(
    *,
    title: str,
    snippet: str,
    url: str,
    relevance_score: int,
    remaining_chars: int,
) -> dict[str, Any] | None:
    clean_title = " ".join(str(title or "").split())[:180]
    clean_url = " ".join(str(url or "").split())[:400]
    clean_snippet = " ".join(str(snippet or "").split())

    fixed_chars = len(clean_title) + len(clean_url)
    if fixed_chars >= remaining_chars:
        return None

    snippet_budget = max(0, remaining_chars - fixed_chars)
    if len(clean_snippet) > snippet_budget:
        if snippet_budget <= 3:
            clean_snippet = clean_snippet[:snippet_budget]
        else:
            clean_snippet = clean_snippet[: snippet_budget - 3].rstrip() + "..."

    return {
        "title": clean_title or "Baslik yok",
        "snippet": clean_snippet,
        "url": clean_url,
        "relevance_score": int(relevance_score),
    }


def _extract_results(payload: dict[str, Any], *, max_results: int) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []

    abstract = str(payload.get("AbstractText") or "").strip()
    if abstract:
        candidates.append(
            {
                "title": str(payload.get("Heading") or "Ozet Sonuc").strip(),
                "snippet": abstract,
                "url": str(payload.get("AbstractURL") or "").strip(),
                "relevance_score": 100,
            }
        )

    answer = str(payload.get("Answer") or "").strip()
    if answer:
        answer_title = str(payload.get("AnswerType") or "Direkt cevap").strip().title()
        candidates.append(
            {
                "title": answer_title or "Direkt cevap",
                "snippet": answer,
                "url": str(payload.get("AbstractURL") or "").strip(),
                "relevance_score": 90,
            }
        )

    for index, topic in enumerate(_flatten_related_topics(payload.get("RelatedTopics")), start=1):
        raw_text = str(topic.get("Text") or "").strip()
        raw_url = str(topic.get("FirstURL") or "").strip()
        if not raw_text and not raw_url:
            continue

        if " - " in raw_text:
            title, snippet = raw_text.split(" - ", 1)
        else:
            title = raw_text[:90]
            snippet = raw_text

        candidates.append(
            {
                "title": title.strip() or "Ilgili sonuc",
                "snippet": snippet.strip() or raw_text,
                "url": raw_url,
                "relevance_score": max(40, 80 - index * 5),
            }
        )

    results: list[dict[str, Any]] = []
    consumed_chars = 0
    for candidate in candidates:
        if len(results) >= max_results:
            break
        remaining_chars = MAX_TOTAL_CHARS - consumed_chars
        if remaining_chars <= 0:
            break
        fitted = _build_result(remaining_chars=remaining_chars, **candidate)
        if not fitted:
            continue
        results.append(fitted)
        consumed_chars += (
            len(fitted["title"]) + len(fitted["snippet"]) + len(fitted["url"])
        )
    return results


def _format_sources(sources: list[dict[str, Any]]) -> str:
    if not sources:
        return "- Kaynak bulunamadi."
    lines = []
    for source in sources:
        title = str(source.get("title") or "Kaynak").strip()
        url = str(source.get("url") or "").strip()
        if url:
            lines.append(f"- {title}: {url}")
        else:
            lines.append(f"- {title}")
    return "\n".join(lines)


def _build_summary(query: str, sources: list[dict[str, Any]]) -> str:
    clean_query = str(query or "").strip()
    if not sources:
        return f"'{clean_query}' icin anlamli sonuc bulunamadi."

    lines = [f"Arastirma ozeti: {clean_query}", ""]
    for index, source in enumerate(sources, start=1):
        title = str(source.get("title") or "Kaynak").strip()
        snippet = str(source.get("snippet") or "").strip()
        if snippet:
            lines.append(f"{index}. {title}: {snippet}")
        else:
            lines.append(f"{index}. {title}")
    return "\n".join(lines)[:MAX_TOTAL_CHARS]


def _write_obsidian_note(
    query: str,
    summary: str,
    sources: list[dict[str, Any]],
) -> str | None:
    vault_dir = get_obsidian_vault_dir()
    if vault_dir is None:
        return None

    vault_root = Path(vault_dir).expanduser().resolve(strict=False)
    if not vault_root.exists() or not vault_root.is_dir():
        return None

    file_name = (
        f"{datetime.now(timezone.utc).strftime('%Y-%m-%d')}_{_slugify(query)}.md"
    )
    note_path = (vault_root / "personas" / "mert" / "research" / file_name).resolve(
        strict=False
    )
    try:
        note_path.relative_to(vault_root)
    except ValueError:
        return None

    lines = [
        f"# {query}",
        "",
        summary,
        "",
        "## Kaynaklar",
        _format_sources(sources),
        "",
    ]
    note_path.parent.mkdir(parents=True, exist_ok=True)
    note_path.write_text("\n".join(lines), encoding="utf-8")
    return note_path.relative_to(vault_root).as_posix()


def web_search_deep(query: str, max_results: int = 5) -> list[dict[str, Any]]:
    clean_query = str(query or "").strip()
    if not clean_query:
        return []

    _respect_rate_limit()
    try:
        payload = _fetch_duckduckgo_payload(clean_query)
        results = _extract_results(payload, max_results=max(1, min(int(max_results or 5), MAX_RESULTS)))
        _log_search(clean_query, status="ok", result_count=len(results))
        return results
    except Exception as exc:  # noqa: BLE001
        _log_search(clean_query, status="error", result_count=0, error=str(exc))
        return []


def search_and_summarize(query: str) -> dict[str, Any]:
    clean_query = str(query or "").strip()
    if not clean_query:
        return {
            "ok": False,
            "error": "query_required",
            "summary": "",
            "sources": [],
            "saved_to": None,
        }

    sources = web_search_deep(clean_query, max_results=MAX_RESULTS)
    summary = _build_summary(clean_query, sources)
    saved_to = _write_obsidian_note(clean_query, summary, sources)
    return {
        "ok": True,
        "summary": summary,
        "sources": sources,
        "saved_to": saved_to,
    }


def competitor_analysis(product_name: str) -> dict[str, Any]:
    clean_product = str(product_name or "").strip()
    if not clean_product:
        return {"ok": False, "error": "product_name_required", "report": "", "sources": []}

    queries = [
        f"{clean_product} reviews",
        f"{clean_product} alternatives",
        f"{clean_product} pricing",
    ]

    sections: list[str] = [f"Rakip analizi: {clean_product}", ""]
    all_sources: list[dict[str, Any]] = []
    for query in queries:
        sources = web_search_deep(query, max_results=3)
        all_sources.extend(sources)
        sections.append(f"## {query}")
        if sources:
            for source in sources:
                title = str(source.get("title") or "Kaynak").strip()
                snippet = str(source.get("snippet") or "").strip()
                if snippet:
                    sections.append(f"- {title}: {snippet}")
                else:
                    sections.append(f"- {title}")
        else:
            sections.append("- Anlamli sonuc bulunamadi.")
        sections.append("")

    report = "\n".join(sections)[:MAX_TOTAL_CHARS]
    return {
        "ok": True,
        "report": report,
        "queries": queries,
        "sources": all_sources[:MAX_RESULTS],
    }


__all__ = [
    "LOG_PATH",
    "RATE_LIMIT_SECONDS",
    "competitor_analysis",
    "search_and_summarize",
    "web_search_deep",
]
