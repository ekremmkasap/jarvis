from __future__ import annotations

from typing import Any

from .base import CanonicalAgent, extract_json_payload


class DebugAgent(CanonicalAgent):
    agent_id = "debug"
    name = "DebugAgent"
    role = "Root cause analysis and fix recommendation"
    model_chain = "reasoning"
    model_preference = "groq/llama-3.3-70b-versatile"

    async def _execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        error_text = self._select_error_text(task, context)
        response = self._call_llm(
            self._build_prompt(task, error_text, context),
            system=(
                "You are DebugAgent. Return strict JSON only. "
                "Schema: {"
                '"error_type":str,'
                '"likely_cause":str,'
                '"affected_files":[str],'
                '"suggested_fix":str,'
                '"confidence":"low|medium|high"}'
            ),
            max_tokens=900,
        )
        parsed = extract_json_payload(response)
        if isinstance(parsed, dict):
            return self._normalize_payload(parsed, error_text)
        return self._fallback_payload(error_text)

    def _select_error_text(self, task: str, context: dict[str, Any]) -> str:
        for key in ("stack_trace", "error_message"):
            value = str(context.get(key) or "").strip()
            if value:
                return value
        return task

    def _build_prompt(self, task: str, error_text: str, context: dict[str, Any]) -> str:
        relevant_context = {
            key: value
            for key, value in context.items()
            if key not in {"token", "api_key", "password", "secret", "authorization", "cookie"}
        }
        return (
            f"Task: {task}\n"
            f"Error details:\n{error_text[:10000]}\n"
            f"Context: {relevant_context}\n"
            "Analyze the root cause and return JSON."
        )

    def _normalize_payload(self, payload: dict[str, Any], error_text: str) -> dict[str, Any]:
        confidence = str(payload.get("confidence") or "").strip().lower()
        if confidence not in {"low", "medium", "high"}:
            confidence = self._estimate_confidence(error_text)
        affected_files = payload.get("affected_files")
        if isinstance(affected_files, list):
            normalized_files = [str(item).strip() for item in affected_files if str(item).strip()]
        else:
            normalized_files = []
        return {
            "error_type": str(payload.get("error_type") or self._classify_error(error_text)).strip() or "UnknownError",
            "likely_cause": str(payload.get("likely_cause") or self._heuristic_cause(error_text)).strip() or self._heuristic_cause(error_text),
            "affected_files": normalized_files,
            "suggested_fix": str(payload.get("suggested_fix") or self._heuristic_fix(error_text)).strip() or self._heuristic_fix(error_text),
            "confidence": confidence,
        }

    def _fallback_payload(self, error_text: str) -> dict[str, Any]:
        return {
            "error_type": self._classify_error(error_text),
            "likely_cause": self._heuristic_cause(error_text),
            "affected_files": self._extract_files(error_text),
            "suggested_fix": self._heuristic_fix(error_text),
            "confidence": self._estimate_confidence(error_text),
        }

    def _classify_error(self, error_text: str) -> str:
        lower = error_text.lower()
        if "modulenotfounderror" in lower or "cannot import" in lower:
            return "ImportError"
        if "keyerror" in lower:
            return "KeyError"
        if "typeerror" in lower:
            return "TypeError"
        if "attributeerror" in lower:
            return "AttributeError"
        if "syntaxerror" in lower:
            return "SyntaxError"
        if "timeout" in lower:
            return "TimeoutError"
        if "connection" in lower or "refused" in lower:
            return "ConnectionError"
        return "RuntimeError"

    def _heuristic_cause(self, error_text: str) -> str:
        lower = error_text.lower()
        if "modulenotfounderror" in lower:
            return "A missing module or local import path is causing the runtime import failure."
        if "keyerror" in lower:
            return "Code accessed a dictionary key that was not present in the runtime payload."
        if "attributeerror" in lower:
            return "Code assumed an object shape or optional value that is not guaranteed."
        if "typeerror" in lower:
            return "A function or operator received an unexpected value type or null-like input."
        if "timeout" in lower:
            return "The operation exceeded its time budget or waited on an unavailable dependency."
        if "connection" in lower or "refused" in lower:
            return "A network dependency or local service was unavailable."
        return "The failure likely comes from an unhandled runtime edge case in the current code path."

    def _heuristic_fix(self, error_text: str) -> str:
        lower = error_text.lower()
        if "modulenotfounderror" in lower:
            return "Verify the dependency or package path, then update imports or environment setup to include the missing module."
        if "keyerror" in lower:
            return "Guard the missing key with validation or defaults before accessing the payload."
        if "attributeerror" in lower or "typeerror" in lower:
            return "Add input validation and null/type guards around the failing object before the access or call."
        if "timeout" in lower:
            return "Increase timeout only if needed, but first profile the blocking dependency and add retry or fallback handling."
        if "connection" in lower or "refused" in lower:
            return "Check service availability, configuration, and startup order, then add clearer retry or failure handling."
        return "Reproduce the failure locally, isolate the failing branch, and add a targeted guard plus regression test."

    def _extract_files(self, error_text: str) -> list[str]:
        files: list[str] = []
        for line in error_text.splitlines():
            marker = 'File "'
            if marker in line:
                start = line.find(marker)
                end = line.find('"', start + len(marker))
                if start != -1 and end != -1:
                    file_name = line[start + len(marker) : end].strip()
                    if file_name and file_name not in files:
                        files.append(file_name)
        return files

    def _estimate_confidence(self, error_text: str) -> str:
        if self._extract_files(error_text):
            return "high"
        if any(token in error_text.lower() for token in ("traceback", "exception", "error")):
            return "medium"
        return "low"
