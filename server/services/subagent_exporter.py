from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = ROOT_DIR / "config" / "generated_subagents"
CODEX_OUTPUT_DIR = ROOT_DIR / ".codex" / "agents"


def _load_manifests() -> dict[str, dict[str, Any]]:
    from policy_engine import load_agent_manifests

    return load_agent_manifests()


def _slug(value: str) -> str:
    text = "".join(ch.lower() if ch.isalnum() else "-" for ch in str(value or "").strip())
    while "--" in text:
        text = text.replace("--", "-")
    return text.strip("-") or "agent"


def _recommended_subagents(manifest: dict[str, Any]) -> list[str]:
    items = manifest.get("recommended_subagents") or []
    return [str(item).strip() for item in items if str(item).strip()][:3]


def _agent_export_filename(agent_id: str) -> str:
    return f"jarvis-{_slug(agent_id)}-subagent-pack.toml"


def _build_subagent_toml(agent_id: str, manifest: dict[str, Any]) -> str:
    label = str(manifest.get("label") or agent_id).strip() or agent_id
    role = str(manifest.get("role") or "unknown").strip() or "unknown"
    risk_level = str(manifest.get("risk_level") or "unknown").strip() or "unknown"
    approval_mode = str(manifest.get("approval_mode") or "auto").strip() or "auto"
    task_types = [str(item).strip() for item in (manifest.get("allowed_task_types") or []) if str(item).strip()]
    handoffs = [str(item).strip() for item in (manifest.get("handoff_targets") or []) if str(item).strip()]
    subagents = _recommended_subagents(manifest)
    character = str(manifest.get("character") or "").strip()
    memory_scope = str(manifest.get("memory_scope") or "none").strip() or "none"

    instructions = [
        f"You are the Jarvis {label} pack.",
        f"Primary role: {role}.",
        f"Risk level: {risk_level}. Approval mode: {approval_mode}.",
        f"Memory scope: {memory_scope}.",
    ]
    if character:
        instructions.append(f"Working style: {character}")
    if task_types:
        instructions.append("Allowed task types: " + ", ".join(task_types) + ".")
    if handoffs:
        instructions.append("Allowed handoff targets: " + ", ".join(handoffs) + ".")
    if subagents:
        instructions.append("Recommended reference subagents: " + ", ".join(subagents) + ".")
    instructions.append("Stay aligned with Jarvis runtime governance, policy enforcement, and minimal safe changes.")

    description = f"Jarvis role pack for {label} using {', '.join(subagents) if subagents else 'no external shortlist'}"
    escaped_instructions = "\n".join(instructions).replace('"""', '\"\"\"')
    return (
        f'name = "jarvis-{_slug(agent_id)}-pack"\n'
        f'description = "{description}"\n'
        'model = "gpt-5.3-codex-spark"\n'
        'model_reasoning_effort = "medium"\n'
        'sandbox_mode = "workspace-write"\n\n'
        '[instructions]\n'
        f'text = """{escaped_instructions}"""\n'
    )


def build_subagent_exports() -> list[dict[str, str]]:
    manifests = _load_manifests()
    exports: list[dict[str, str]] = []
    for agent_id, manifest in sorted(manifests.items(), key=lambda item: item[0]):
        subagents = _recommended_subagents(manifest)
        if not subagents:
            continue
        exports.append(
            {
                "agent_id": agent_id,
                "filename": _agent_export_filename(agent_id),
                "content": _build_subagent_toml(agent_id, manifest),
            }
        )
    return exports


def export_subagent_files(output_dir: str | Path | None = None) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    exports = build_subagent_exports()
    written: list[str] = []
    for item in exports:
        path = target_dir / item["filename"]
        path.write_text(item["content"], encoding="utf-8")
        written.append(str(path))
    return {
        "output_dir": str(target_dir),
        "count": len(written),
        "files": written,
    }


def export_to_codex_agents() -> dict[str, Any]:
    return export_subagent_files(CODEX_OUTPUT_DIR)


def clean_exported_files(output_dir: str | Path | None = None) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    removed: list[str] = []
    if not target_dir.exists():
        return {"output_dir": str(target_dir), "count": 0, "files": removed}
    for path in target_dir.glob("jarvis-*-subagent-pack.toml"):
        try:
            path.unlink()
            removed.append(str(path))
        except Exception:
            continue
    return {"output_dir": str(target_dir), "count": len(removed), "files": removed}


def build_export_report() -> str:
    exports = build_subagent_exports()
    if not exports:
        return "SUBAGENT EXPORT\n\nExport edilecek recommended_subagents kaydi yok."
    lines = ["SUBAGENT EXPORT", f"Toplam paket: {len(exports)}", ""]
    for item in exports:
        lines.append(f"- {item['agent_id']} -> {item['filename']}")
    return "\n".join(lines)


def _resolve_cli_output_dir(argv: list[str]) -> Path | None:
    args = list(argv[1:])
    if not args:
        return None
    if args[0] in {"--codex", "--codex-clean"}:
        return CODEX_OUTPUT_DIR
    if args[0] == "--output" and len(args) > 1:
        return Path(args[1])
    if args[0] == "--clean" and len(args) > 1:
        return Path(args[1])
    return None


def _run_cli(argv: list[str]) -> dict[str, Any] | str:
    args = list(argv[1:])
    if not args:
        return export_subagent_files()
    if args[0] == "--report":
        return build_export_report()
    if args[0] == "--codex":
        return export_subagent_files(CODEX_OUTPUT_DIR)
    if args[0] == "--codex-clean":
        return clean_exported_files(CODEX_OUTPUT_DIR)
    if args[0] == "--clean":
        target = Path(args[1]) if len(args) > 1 else DEFAULT_OUTPUT_DIR
        return clean_exported_files(target)
    if args[0] == "--output" and len(args) > 1:
        return export_subagent_files(Path(args[1]))
    return export_subagent_files(_resolve_cli_output_dir(argv))


if __name__ == "__main__":
    result = _run_cli(sys.argv)
    if isinstance(result, str):
        print(result)
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
