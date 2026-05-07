from __future__ import annotations

import importlib
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - testlerde monkeypatch edilebilir
    OpenAI = None  # type: ignore[assignment]


DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_FILE_READER_CHARS = 2000
MAX_CODE_CHARS = 6000
MAX_SUMMARIZER_CHARS = 12000
SUPPORTED_AGENT_TYPES = (
    "web_search",
    "code_analyzer",
    "file_reader",
    "obsidian_writer",
    "summarizer",
)
_PATH_SUFFIXES = (
    ".py",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
)
_QUOTED_PATH_RE = re.compile(r"""["'](?P<path>[^"']+)["']""")
_MULTI_STEP_PATTERNS = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\badim adim\b",
        r"\bonce\b.*\bsonra\b",
        r"\banaliz et ve\b",
        r"\boku\b.*\blistele\b",
        r"\barastir ve\b",
        r"\bdosyalari\b.*\bhata\b",
    )
)


class SubAgentRunnerError(RuntimeError):
    pass


def _normalize_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = normalized.replace("ı", "i").replace("İ", "i")
    return " ".join(normalized.lower().split())


def is_multi_step(message: str) -> bool:
    normalized = _normalize_text(message)
    if not normalized:
        return False
    return any(pattern.search(normalized) for pattern in _MULTI_STEP_PATTERNS)


def _ensure_mapping(payload: dict | None) -> dict[str, Any]:
    return dict(payload) if isinstance(payload, dict) else {}


def _extract_path_from_task(task: str) -> str:
    raw_task = str(task or "").strip()
    if not raw_task:
        return ""

    for match in _QUOTED_PATH_RE.finditer(raw_task):
        candidate = str(match.group("path") or "").strip()
        if candidate:
            return candidate

    for token in re.split(r"\s+", raw_task):
        candidate = token.strip(" ,;:()[]{}<>")
        if not candidate:
            continue
        normalized = candidate.replace("\\", "/")
        if "/" in normalized or normalized.lower().endswith(_PATH_SUFFIXES):
            return candidate
    return ""


def _derive_note_title(task: str) -> str:
    cleaned = re.sub(r"\s+", " ", str(task or "").strip())
    if not cleaned:
        return "Swarm Notu"
    words = cleaned.split(" ")
    return " ".join(words[:8])[:80].strip() or "Swarm Notu"


def _read_file_payload(
    payload: dict[str, Any],
    *,
    max_chars: int | None = None,
) -> tuple[Path, str]:
    path_text = str(payload.get("path") or "").strip()
    if not path_text:
        raise SubAgentRunnerError("path gerekli")

    target = Path(path_text).expanduser()
    if not target.exists() or not target.is_file():
        raise SubAgentRunnerError(f"dosya bulunamadi: {path_text}")

    content = target.read_text(encoding="utf-8", errors="ignore")
    if max_chars is not None:
        content = content[:max_chars]
    return target, content


def _extract_completion_text(response: Any) -> str:
    choices = getattr(response, "choices", None)
    if choices is None and isinstance(response, dict):
        choices = response.get("choices")
    if not choices:
        raise SubAgentRunnerError("Groq yaniti bos dondu")

    first_choice = choices[0]
    message = getattr(first_choice, "message", None)
    if message is None and isinstance(first_choice, dict):
        message = first_choice.get("message")

    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            text_value = getattr(item, "text", None)
            if text_value is None and isinstance(item, dict):
                text_value = item.get("text")
            if text_value:
                parts.append(str(text_value))
        content = "".join(parts)

    text = str(content or "").strip()
    if not text:
        raise SubAgentRunnerError("Groq yaniti bos dondu")
    return text


def _call_groq_chat(
    prompt: str,
    *,
    system_prompt: str,
    model: str = DEFAULT_GROQ_MODEL,
    temperature: float = 0.2,
    max_tokens: int = 700,
) -> str:
    clean_prompt = str(prompt or "").strip()
    if not clean_prompt:
        raise SubAgentRunnerError("prompt gerekli")
    if OpenAI is None:
        raise SubAgentRunnerError("openai SDK yuklu degil")

    api_key = str(os.environ.get("GROQ_API_KEY") or "").strip()
    if not api_key:
        raise SubAgentRunnerError("GROQ_API_KEY ayarli degil")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
        timeout=30,
    )
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": str(system_prompt or "").strip()},
            {"role": "user", "content": clean_prompt},
        ],
    )
    return _extract_completion_text(response)


def _load_web_search() -> Callable[..., Any]:
    module_candidates = (
        "server.skills.mert_skill",
        "server.skills.mert_research_skill",
        "mert_skill",
        "mert_research_skill",
    )
    for module_name in module_candidates:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue
        search_fn = getattr(module, "web_search_deep", None)
        if callable(search_fn):
            return search_fn
    raise SubAgentRunnerError("web_search_deep bulunamadi")


def _execute_web_search(payload: dict[str, Any]) -> str:
    query = str(payload.get("query") or payload.get("task") or "").strip()
    if not query:
        raise SubAgentRunnerError("query gerekli")

    max_results = max(1, min(int(payload.get("max_results") or 5), 5))
    search_fn = _load_web_search()
    results = search_fn(query, max_results=max_results)
    if not isinstance(results, list) or not results:
        return f"Web aramasinda sonuc bulunamadi: {query}"

    lines = [f"Web arama: {query}"]
    for index, item in enumerate(results[:max_results], start=1):
        title = str((item or {}).get("title") or "Kaynak").strip()
        snippet = str((item or {}).get("snippet") or "").strip()
        url = str((item or {}).get("url") or "").strip()
        parts = [f"{index}. {title}"]
        if snippet:
            parts.append(snippet)
        if url:
            parts.append(url)
        lines.append(" - ".join(parts))
    return "\n".join(lines)[:MAX_SUMMARIZER_CHARS]


def _execute_code_analyzer(payload: dict[str, Any]) -> str:
    target, content = _read_file_payload(payload, max_chars=MAX_CODE_CHARS)
    task_text = str(payload.get("task") or "").strip()
    prompt = (
        "Kod analizi yap:\n"
        f"Dosya: {target}\n"
        f"Gorev: {task_text or 'Genel kalite, risk ve refactor alanlarini incele.'}\n\n"
        f"{content}"
    )
    return _call_groq_chat(
        prompt,
        system_prompt=(
            "Sen teknik bir kod inceleme ajanisin. "
            "Bulgulari kisa, net ve uygulanabilir sekilde yaz."
        ),
        max_tokens=800,
    )


def _execute_file_reader(payload: dict[str, Any]) -> str:
    _, content = _read_file_payload(payload, max_chars=MAX_FILE_READER_CHARS)
    return content or "[bos dosya]"


def _execute_obsidian_writer(payload: dict[str, Any]) -> str:
    try:
        from server.skills.persona_obsidian_skill import write_persona_note
    except Exception:
        from persona_obsidian_skill import write_persona_note

    persona_id = str(payload.get("persona_id") or "").strip()
    if not persona_id:
        raise SubAgentRunnerError("persona_id gerekli")

    title = str(payload.get("title") or "").strip() or "Swarm Notu"
    content = str(payload.get("content") or payload.get("text") or "").strip()
    if not content:
        raise SubAgentRunnerError("icerik gerekli")

    note = write_persona_note(persona_id=persona_id, title=title, content=content)
    if not note:
        raise SubAgentRunnerError("OBSIDIAN_VAULT_PATH ayarli degil")

    note_path = str(note.get("path") or note.get("title") or title).strip()
    return f"Obsidian kaydi tamamlandi: {note_path}"


def _execute_summarizer(payload: dict[str, Any]) -> str:
    text = str(payload.get("text") or payload.get("content") or "").strip()
    if not text:
        raise SubAgentRunnerError("text gerekli")

    prompt = "Ozetle:\n\n" + text[:MAX_SUMMARIZER_CHARS]
    return _call_groq_chat(
        prompt,
        system_prompt="Sen kisa ve net ozetler ureten bir asistansin.",
        model=DEFAULT_GROQ_MODEL,
        max_tokens=500,
    )


def _safe_run(
    runner: Callable[[dict[str, Any]], str],
    payload: dict | None,
    *,
    error_prefix: str,
) -> str:
    try:
        return runner(_ensure_mapping(payload))
    except Exception as exc:  # noqa: BLE001
        return f"{error_prefix}: {exc}"


def _build_agent_payload(
    persona_id: str,
    task: str,
    agent_type: str,
    previous_outputs: list[str],
) -> dict[str, Any]:
    path = _extract_path_from_task(task)
    previous_text = "\n\n".join(previous_outputs).strip()
    if agent_type == "web_search":
        return {"query": task}
    if agent_type == "code_analyzer":
        return {"path": path, "task": task}
    if agent_type == "file_reader":
        return {"path": path}
    if agent_type == "obsidian_writer":
        return {
            "persona_id": persona_id,
            "title": _derive_note_title(task),
            "content": previous_text or task,
        }
    if agent_type == "summarizer":
        return {"text": previous_text or task}
    return {"task": task}


def _coerce_agent_types(agent_types: list[str] | None) -> list[str]:
    raw_items = agent_types if isinstance(agent_types, list) else list(SUPPORTED_AGENT_TYPES)
    normalized: list[str] = []
    for item in raw_items:
        agent_type = str(item or "").strip()
        if agent_type and agent_type not in normalized:
            normalized.append(agent_type)
    return normalized


_RUNNER_IMPLS: dict[str, Callable[[dict[str, Any]], str]] = {
    "web_search": _execute_web_search,
    "code_analyzer": _execute_code_analyzer,
    "file_reader": _execute_file_reader,
    "obsidian_writer": _execute_obsidian_writer,
    "summarizer": _execute_summarizer,
}


def run_sub_agents(
    persona_id: str, task: str, agent_types: list[str] | None = None
) -> str:
    clean_persona_id = str(persona_id or "").strip() or "jarvis"
    clean_task = str(task or "").strip()
    if not clean_task:
        return ""

    outputs: list[str] = []
    previous_outputs: list[str] = []
    for agent_type in _coerce_agent_types(agent_types):
        runner = _RUNNER_IMPLS.get(agent_type)
        if runner is None:
            outputs.append(f"[{agent_type}] adimda sorun cikti: unsupported_agent_type")
            continue

        payload = _build_agent_payload(
            clean_persona_id,
            clean_task,
            agent_type,
            previous_outputs,
        )
        try:
            result = runner(payload)
        except Exception as exc:  # noqa: BLE001
            outputs.append(f"[{agent_type}] adimda sorun cikti: {exc}")
            continue

        clean_result = str(result or "").strip()
        if not clean_result:
            outputs.append(f"[{agent_type}] adimda sorun cikti: bos_sonuc")
            continue

        outputs.append(f"[{agent_type}] {clean_result}")
        previous_outputs.append(f"[{agent_type}] {clean_result}")

    return "\n\n".join(outputs).strip()


def _run_web_search(payload: dict | None = None) -> str:
    return _safe_run(_execute_web_search, payload, error_prefix="Web arama hatasi")


def _run_code_analyzer(payload: dict | None = None) -> str:
    return _safe_run(_execute_code_analyzer, payload, error_prefix="Kod analizi hatasi")


def _run_file_reader(payload: dict | None = None) -> str:
    return _safe_run(_execute_file_reader, payload, error_prefix="Dosya okunamadi")


def _run_obsidian_writer(payload: dict | None = None) -> str:
    return _safe_run(
        _execute_obsidian_writer,
        payload,
        error_prefix="Obsidian yazimi hatasi",
    )


def _run_summarizer(payload: dict | None = None) -> str:
    return _safe_run(_execute_summarizer, payload, error_prefix="Ozetleme hatasi")


__all__ = [
    "is_multi_step",
    "run_sub_agents",
    "_run_web_search",
    "_run_code_analyzer",
    "_run_file_reader",
    "_run_obsidian_writer",
    "_run_summarizer",
]
