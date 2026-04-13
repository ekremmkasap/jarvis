from __future__ import annotations

from pathlib import Path
from typing import Any

from .base import CanonicalAgent


class DeveloperAgent(CanonicalAgent):
    agent_id = "developer"
    name = "DeveloperAgent"
    role = "Bounded implementation agent"
    model_chain = "code"
    model_preference = "groq/moonshotai/kimi-k2-5"

    async def _execute(self, task: str, context: dict[str, Any]) -> dict[str, Any]:
        targets = self._normalize_targets(context)
        write_mode = str(context.get("write_mode") or "overwrite").strip().lower()
        change_description = str(context.get("change_description") or task).strip()
        proposed_content = context.get("proposed_content")

        files_changed: list[str] = []
        for target in targets:
            target_path = self._resolve_target(target)
            content = self._resolve_content_for_target(
                target=target,
                target_path=target_path,
                task=task,
                change_description=change_description,
                proposed_content=proposed_content,
            )
            target_path.parent.mkdir(parents=True, exist_ok=True)
            existing = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
            if write_mode == "append":
                target_path.write_text(existing + content, encoding="utf-8")
            else:
                target_path.write_text(content, encoding="utf-8")
            files_changed.append(str(target_path.relative_to(self.root_dir)).replace("\\", "/"))

        return {
            "files_changed": files_changed,
            "description": change_description,
            "status": "review_required",
        }

    def _normalize_targets(self, context: dict[str, Any]) -> list[str]:
        raw_targets = context.get("target_files")
        if raw_targets is None:
            raw_targets = context.get("target_file")
        if raw_targets is None:
            raise ValueError("DeveloperAgent requires context['target_file'] or context['target_files'].")
        if isinstance(raw_targets, str):
            targets = [raw_targets]
        elif isinstance(raw_targets, list):
            targets = [str(item) for item in raw_targets if str(item).strip()]
        else:
            raise TypeError("target_file(s) must be a string or list of strings.")
        if not targets:
            raise ValueError("DeveloperAgent received no writable target files.")
        return targets

    def _resolve_target(self, target: str) -> Path:
        target_path = Path(target)
        if not target_path.is_absolute():
            target_path = (self.root_dir / target_path).resolve()
        else:
            target_path = target_path.resolve()
        try:
            target_path.relative_to(self.root_dir)
        except ValueError as exc:
            raise ValueError(f"Refusing to write outside repo root: {target_path}") from exc
        return target_path

    def _resolve_content_for_target(
        self,
        *,
        target: str,
        target_path: Path,
        task: str,
        change_description: str,
        proposed_content: Any,
    ) -> str:
        if isinstance(proposed_content, dict):
            if target in proposed_content:
                return str(proposed_content[target])
            normalized = str(target_path.relative_to(self.root_dir)).replace("\\", "/")
            if normalized in proposed_content:
                return str(proposed_content[normalized])
        elif isinstance(proposed_content, str):
            return proposed_content

        current_content = target_path.read_text(encoding="utf-8") if target_path.exists() else ""
        prompt = (
            f"Task: {task}\n"
            f"Change description: {change_description}\n"
            f"Target file: {target}\n"
            "Return the full file content only.\n\n"
            f"Current content:\n{current_content}"
        )
        generated = self._call_llm(
            prompt,
            system="You are DeveloperAgent. Return only the full file content for the requested target.",
            max_tokens=1400,
        )
        if generated:
            return generated
        raise ValueError(f"No content available for target_file '{target}'.")

