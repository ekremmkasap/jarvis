from __future__ import annotations

from typing import Any

from .base import CanonicalAgent, extract_json_payload


class DocsAgent(CanonicalAgent):
    agent_id = "docs"
    name = "DocsAgent"
    role = "Documentation draft generation"
    model_chain = "default"
    model_preference = "groq/llama-3.3-70b-versatile"

    async def _execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        doc_type = self._infer_doc_type(task, context)
        response = self._call_llm(
            self._build_prompt(task, doc_type, context),
            system=(
                "You are DocsAgent. Return strict JSON only. "
                "Schema: {"
                '"doc_type":str,'
                '"content":str,'
                '"target_file_suggestion":str}'
            ),
            max_tokens=1200,
        )
        parsed = extract_json_payload(response)
        if isinstance(parsed, dict):
            return self._normalize_payload(parsed, task, doc_type, context)
        return self._fallback_payload(task, doc_type, context)

    def _build_prompt(self, task: str, doc_type: str, context: dict[str, Any]) -> str:
        return (
            f"Task: {task}\n"
            f"Doc type: {doc_type}\n"
            f"Context: {context}\n"
            "Return documentation draft JSON."
        )

    def _normalize_payload(
        self,
        payload: dict[str, Any],
        task: str,
        doc_type: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        content = str(payload.get("content") or "").strip()
        if not content:
            return self._fallback_payload(task, doc_type, context)
        normalized_type = str(payload.get("doc_type") or doc_type).strip().lower() or doc_type
        target_file = str(payload.get("target_file_suggestion") or self._suggest_target_file(normalized_type)).strip()
        return {
            "doc_type": normalized_type,
            "content": content,
            "target_file_suggestion": target_file,
        }

    def _fallback_payload(self, task: str, doc_type: str, context: dict[str, Any]) -> dict[str, Any]:
        description = str(context.get("description") or task).strip() or task
        command = str(context.get("command") or "").strip()
        code = str(context.get("code") or "").strip()
        content_lines = [f"# {doc_type.upper()} Draft", "", "## Overview", description]
        if command:
            content_lines.extend(["", "## Command", f"`{command}`"])
        if code:
            content_lines.extend(["", "## Notes", "```text", code[:1200], "```"])
        content_lines.extend(["", "## Next Steps", "- Review the draft with the owning engineer.", "- Add examples or edge cases if needed."])
        return {
            "doc_type": doc_type,
            "content": "\n".join(content_lines).strip(),
            "target_file_suggestion": self._suggest_target_file(doc_type),
        }

    def _infer_doc_type(self, task: str, context: dict[str, Any]) -> str:
        raw = str(context.get("doc_type") or "").strip().lower()
        if raw:
            return raw
        lower = task.lower()
        if "readme" in lower:
            return "readme"
        if "runbook" in lower:
            return "runbook"
        if "agent" in lower:
            return "agents"
        if "api" in lower:
            return "api"
        return "docs"

    def _suggest_target_file(self, doc_type: str) -> str:
        mapping = {
            "readme": "README.md",
            "runbook": "RUNBOOK.md",
            "agents": "AGENTS.md",
            "api": "docs/API.md",
            "docs": "docs/README.md",
        }
        return mapping.get(doc_type, f"docs/{doc_type}.md")
