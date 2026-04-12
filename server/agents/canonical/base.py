from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ...model_router import ModelRouter, build_model_router


SENSITIVE_TOKENS = ("key", "token", "secret", "password", "authorization", "cookie")


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()


def extract_json_payload(text: str) -> Any | None:
    raw_text = str(text or "").strip()
    if not raw_text:
        return None

    candidates = [raw_text]
    for pattern in (r"```json\s*(.*?)```", r"```\s*(.*?)```"):
        for match in re.findall(pattern, raw_text, flags=re.IGNORECASE | re.DOTALL):
            cleaned = str(match).strip()
            if cleaned:
                candidates.append(cleaned)

    for candidate in candidates:
        for opener, closer in (("{", "}"), ("[", "]")):
            start = candidate.find(opener)
            end = candidate.rfind(closer)
            if start == -1 or end == -1 or end <= start:
                continue
            snippet = candidate[start : end + 1]
            try:
                return json.loads(snippet)
            except json.JSONDecodeError:
                continue
    return None


class CanonicalAgent:
    agent_id = "canonical"
    name = "CanonicalAgent"
    role = "canonical"
    model_chain = "default"
    model_preference = "groq/llama-3.3-70b-versatile"

    def __init__(
        self,
        *,
        router: ModelRouter | None = None,
        root_dir: Path | None = None,
        log_path: Path | None = None,
    ) -> None:
        self.root_dir = Path(root_dir) if root_dir else Path(__file__).resolve().parents[3]
        self._router = router
        self.log_path = Path(log_path) if log_path else self.root_dir / "server" / "logs" / "canonical_agents.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._memory_path = self.root_dir / "state" / "agent_memory" / f"{self.agent_id}.json"
        self._last_llm_trace: dict[str, Any] = {}
        self._last_run_context: dict[str, Any] = {}

    async def run(self, task: str, context: dict | None = None) -> dict[str, Any]:
        clean_task = str(task or "").strip()
        context_data = dict(context or {})
        self._last_run_context = context_data
        timestamp = utc_timestamp()

        if not clean_task:
            result = self._result(
                status="error",
                timestamp=timestamp,
                output={},
                error="Task cannot be empty.",
            )
            self._log_result(result)
            return result

        self.remember("last_task", clean_task[:200])
        self.remember("last_run", timestamp)

        try:
            payload = await self._execute(clean_task, context_data)
            if not isinstance(payload, dict):
                raise TypeError("Agent payload must be a dictionary.")
            flat_payload = {
                key: value
                for key, value in payload.items()
                if key not in {"agent_id", "status", "timestamp", "output", "error"}
            }
            result = self._result(status="ok", timestamp=timestamp, output=payload, **flat_payload)
        except Exception as exc:  # noqa: BLE001
            result = self._result(
                status="error",
                timestamp=timestamp,
                output={},
                error=str(exc),
            )

        self._log_result(result)
        return result

    async def _execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def _get_router(self) -> ModelRouter:
        if self._router is None:
            self._router = build_model_router(
                root_dir=self.root_dir,
                default_ollama_url=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"),
                request_timeout=int(os.environ.get("JARVIS_REQUEST_TIMEOUT", "120")),
            )
        return self._router

    def _call_llm(self, prompt: str, system: str | None = None, max_tokens: int = 800) -> str:
        router = self._get_router()
        if hasattr(router, "settings") and hasattr(router.settings, "chains"):
            original_chains = router.settings.chains
            router.settings.chains = {}
            try:
                response, trace = router.chat(
                    route_name=None,
                    primary_model=self.model_preference,
                    fallback_model=None,
                    messages=[{"role": "user", "content": str(prompt)}],
                    system=system,
                    max_tokens=max_tokens,
                    num_ctx=4096,
                )
            finally:
                router.settings.chains = original_chains
        else:
            response, trace = router.chat(
                route_name=None,
                primary_model=self.model_preference,
                fallback_model=None,
                messages=[{"role": "user", "content": str(prompt)}],
                system=system,
                max_tokens=max_tokens,
                num_ctx=4096,
            )
        self._last_llm_trace = trace if isinstance(trace, dict) else {}
        if self._last_llm_trace.get("ok"):
            return str(response).strip()
        return ""

    def _result(self, *, status: str, timestamp: str, output: dict[str, Any], **payload: Any) -> dict[str, Any]:
        result = {
            "agent_id": self.agent_id,
            "status": status,
            "timestamp": timestamp,
            "output": output,
        }
        if self._last_llm_trace:
            result["llm_trace"] = self._trim_for_log(self._last_llm_trace)
        result.update(payload)
        return result

    def _log_result(self, result: dict[str, Any]) -> None:
        log_entry = {
            "timestamp": result.get("timestamp", utc_timestamp()),
            "agent_id": self.agent_id,
            "status": result.get("status", "error"),
            "context": self._sanitize_context(self._last_run_context),
            "result": self._trim_for_log(result),
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(log_entry, ensure_ascii=False) + "\n")

    def remember(self, key: str, value: object) -> None:
        self._memory_path.parent.mkdir(parents=True, exist_ok=True)
        data = self._load_memory()
        data[str(key)] = value
        self._memory_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def recall(self, key: str, default: Any = None) -> Any:
        return self._load_memory().get(key, default)

    def memory_summary(self) -> dict[str, Any]:
        return self._load_memory()

    def _load_memory(self) -> dict[str, Any]:
        if not self._memory_path.exists():
            return {}
        try:
            loaded = json.loads(self._memory_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
        return loaded if isinstance(loaded, dict) else {}

    def _sanitize_context(self, value: Any) -> Any:
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, nested in value.items():
                key_text = str(key)
                if any(token in key_text.lower() for token in SENSITIVE_TOKENS):
                    sanitized[key_text] = "[REDACTED]"
                else:
                    sanitized[key_text] = self._sanitize_context(nested)
            return sanitized
        if isinstance(value, list):
            return [self._sanitize_context(item) for item in value[:20]]
        if isinstance(value, tuple):
            return [self._sanitize_context(item) for item in value[:20]]
        if isinstance(value, str):
            return value if len(value) <= 500 else value[:497] + "..."
        return value

    def _trim_for_log(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._trim_for_log(nested) for key, nested in value.items()}
        if isinstance(value, list):
            return [self._trim_for_log(item) for item in value[:20]]
        if isinstance(value, tuple):
            return [self._trim_for_log(item) for item in value[:20]]
        if isinstance(value, str):
            return value if len(value) <= 500 else value[:497] + "..."
        return value
