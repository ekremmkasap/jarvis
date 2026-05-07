"""
Jarvis Agent Runner
Her agent bu script ile çalışır. task_bus'ı poll eder,
görevi alır, çalıştırır, sonucu geri yazar.

Kullanım:
  python server/agents/agent_runner.py demir
  python server/agents/agent_runner.py selin
  python server/agents/agent_runner.py kaan
  python server/agents/agent_runner.py celik
"""
import sys
import time
import json
import importlib
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "server"))
sys.path.insert(0, str(ROOT / "server" / "agents"))
sys.path.insert(0, str(ROOT / "server" / "skills"))
sys.path.insert(0, str(ROOT / "server" / "services"))

import task_bus
from agent_os_visual import sync_tool_job_result

POLL_INTERVAL = 5  # saniye
AGENT_OS_EVENTS_PATH = ROOT / "server" / "logs" / "agent_os_events.jsonl"

# Agent ID → task_bus ID eşlemesi
AGENT_NAME_MAP = {
    "demir":  "backend",
    "selin":  "voice",
    "kaan":   "video",
    "celik":  "security",
    "jarvis": "swarm",
}

# Agent ID → çalıştırılacak skill/fonksiyon
AGENT_HANDLERS = {
    "backend": "_handle_backend",
    "voice":   "_handle_voice",
    "video":   "_handle_video",
    "security": "_handle_security",
}


def _load_llm():
    """Ollama LLM çağrı fonksiyonu."""
    try:
        import requests
        def call_llm(prompt: str, max_tokens: int = 400) -> str:
            r = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama3.2:latest", "prompt": prompt, "stream": False},
                timeout=30,
            )
            return r.json().get("response", "").strip()
        return call_llm
    except Exception:
        return None


def _extract_task_text(task: dict) -> str:
    payload = task.get("payload")
    if isinstance(payload, dict):
        text = str(payload.get("task") or payload.get("hedef") or payload.get("summary") or "").strip()
        if text:
            return text
        try:
            return json.dumps(payload, ensure_ascii=False)[:500]
        except Exception:
            return str(payload)[:500]
    return str(payload or task.get("task") or "").strip()


def _extract_tool_execution(task: dict) -> dict:
    payload = task.get("payload")
    if isinstance(payload, dict) and isinstance(payload.get("tool_execution"), dict):
        return dict(payload.get("tool_execution") or {})
    return {}


def _build_tool_hint(task: dict) -> str:
    tool_execution = _extract_tool_execution(task)
    tool = str(tool_execution.get("tool") or "").strip()
    if not tool:
        return ""
    mode = str(tool_execution.get("mode") or "-").strip() or "-"
    fallback = "yes" if bool(tool_execution.get("fallback_used")) else "no"
    status = "ok" if bool(tool_execution.get("ok")) else "error"
    return f"Tool routing: {tool} | status={status} | fallback={fallback} | mode={mode}"


def _record_agent_os_event(event_type: str, message: str, data: dict | None = None) -> None:
    event = {
        "time": datetime.now().isoformat(),
        "type": str(event_type or "agent_runner").strip() or "agent_runner",
        "message": str(message or "").strip()[:240],
        "data": data or {},
    }
    try:
        AGENT_OS_EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with AGENT_OS_EVENTS_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _handle_backend(task: dict, call_llm) -> str:
    payload = _extract_task_text(task)
    task_type = task.get("task_type", "")
    tool_hint = _build_tool_hint(task)

    # github agent
    if any(w in str(payload).lower() for w in ["git", "commit", "branch", "repo", "pr"]):
        try:
            import github_agent
            result = github_agent.analyze(str(payload), call_llm=call_llm)
            return result.get("report", "GitHub analizi tamamlandı.")
        except Exception as e:
            return f"GitHub agent hatası: {e}"

    # LLM fallback
    if call_llm:
        prompt = (
            f"Sen Jarvis'in Backend Core agentisin (Demir)." + chr(10) +
            f"Görev: {payload}" + chr(10) +
            (tool_hint + chr(10) if tool_hint else "") +
            "Kısa, teknik, Türkçe yanıt ver."
        )
        return call_llm(prompt)
    return f"Backend görev alındı: {payload}"


def _handle_voice(task: dict, call_llm) -> str:
    payload = _extract_task_text(task)
    tool_hint = _build_tool_hint(task)
    if call_llm:
        prompt = (
            f"Sen Jarvis'in Voice+Hologram agentisin (Selin)." + chr(10) +
            f"Görev: {payload}" + chr(10) +
            (tool_hint + chr(10) if tool_hint else "") +
            "Sıcak, akıcı, Türkçe yanıt ver."
        )
        return call_llm(prompt)
    return f"Voice görev alındı: {payload}"


def _handle_video(task: dict, call_llm) -> str:
    payload = _extract_task_text(task)
    tool_hint = _build_tool_hint(task)

    # youtube agent
    if any(w in str(payload).lower() for w in ["youtube", "youtu.be", "video", "instagram"]):
        try:
            import youtube_agent
            result = youtube_agent.analyze(str(payload), call_llm=call_llm)
            return result.get("report", "Video analizi tamamlandı.")
        except Exception as e:
            return f"YouTube agent hatası: {e}"

    if call_llm:
        prompt = (
            f"Sen Jarvis'in Video+Workspace agentisin (Kaan)." + chr(10) +
            f"Görev: {payload}" + chr(10) +
            (tool_hint + chr(10) if tool_hint else "") +
            "Analitik, heyecanlı, Türkçe yanıt ver."
        )
        return call_llm(prompt)
    return f"Video görev alındı: {payload}"


def _handle_security(task: dict, call_llm) -> str:
    payload = _extract_task_text(task)
    tool_hint = _build_tool_hint(task)
    if call_llm:
        prompt = (
            f"Sen Jarvis'in Security/Review agentisin (Çelik)." + chr(10) +
            f"Görev: {payload}" + chr(10) +
            (tool_hint + chr(10) if tool_hint else "") +
            "Kısa, sert, güvenlik odaklı Türkçe rapor ver."
        )
        return call_llm(prompt)
    return f"Security görev alındı: {payload}"


def _run_task(agent_id: str, task: dict, call_llm) -> str:
    handlers = {
        "backend":  _handle_backend,
        "voice":    _handle_voice,
        "video":    _handle_video,
        "security": _handle_security,
    }
    handler = handlers.get(agent_id)
    if handler:
        try:
            return handler(task, call_llm)
        except Exception as e:
            return f"Görev işlenirken hata: {e}"
    return f"Handler bulunamadı: {agent_id}"


def run(agent_name: str):
    agent_id = AGENT_NAME_MAP.get(agent_name.lower())
    if not agent_id:
        print(f"Geçersiz agent: {agent_name}. Geçerliler: {list(AGENT_NAME_MAP.keys())}")
        sys.exit(1)

    call_llm = _load_llm()
    print(f"[{agent_name.upper()}] Başlatıldı. Agent ID: {agent_id}. Poll: {POLL_INTERVAL}s")

    while True:
        try:
            tasks = task_bus.get_tasks(agent_id)
            for task in tasks:
                task_id = task["id"]
                task_text = _extract_task_text(task)
                tool_execution = _extract_tool_execution(task)
                tool_hint = _build_tool_hint(task)
                tool_name = str(tool_execution.get("tool") or "-").strip() or "-"
                tool_status = "ok" if bool(tool_execution.get("ok")) else ("error" if tool_name != "-" else "-")
                fallback_used = "yes" if bool(tool_execution.get("fallback_used")) else ("no" if tool_name != "-" else "-")
                print(f"[{agent_name.upper()}] Görev alındı: {task_id} — {task_text[:60]}")
                if tool_hint:
                    print(f"[{agent_name.upper()}] {tool_hint}")
                _record_agent_os_event(
                    "tool_task_started",
                    f"{agent_name} started {task_id} | tool={tool_name} | fallback={fallback_used}",
                    {
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "task_id": task_id,
                        "task_type": str(task.get("task_type") or "-"),
                        "task_excerpt": task_text[:160],
                        "tool": tool_name,
                        "tool_status": tool_status,
                        "fallback_used": fallback_used,
                        "mode": str(tool_execution.get("mode") or "-"),
                    },
                )

                # çalıştır
                result = _run_task(agent_id, task, call_llm)

                # tamamla + Jarvis'e bildir
                completed = task_bus.complete_task(
                    task_id,
                    {
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "task_excerpt": task_text[:160],
                        "summary": str(result)[:300],
                        "tool_execution": tool_execution,
                    },
                )
                if not completed:
                    raise RuntimeError(f"task_complete_failed:{task_id}")
                _record_agent_os_event(
                    "tool_task_completed",
                    f"{agent_name} completed {task_id} | tool={tool_name} | fallback={fallback_used}",
                    {
                        "agent_id": agent_id,
                        "agent_name": agent_name,
                        "task_id": task_id,
                        "task_excerpt": task_text[:160],
                        "summary": str(result)[:240],
                        "tool": tool_name,
                        "tool_status": tool_status,
                        "fallback_used": fallback_used,
                        "mode": str(tool_execution.get("mode") or "-"),
                    },
                )
                sync_tool_job_result(
                    task_id=task_id,
                    task_type=str(task.get("task_type") or "-"),
                    agent_id=agent_id,
                    agent_name=agent_name,
                    task_text=task_text,
                    tool_execution=tool_execution,
                    summary=str(result)[:240],
                    success=True,
                )
                summary_ok, summary_ref = task_bus.post_task(
                    from_agent=agent_id,
                    to_agent="swarm",
                    task_type="summary",
                    payload={
                        "original_task_id": task_id,
                        "from_agent": agent_name,
                        "task_excerpt": task_text[:160],
                        "result": result[:300],
                        "tool_execution": tool_execution,
                    },
                    policy_check=False,
                )
                if not summary_ok:
                    _record_agent_os_event(
                        "tool_task_summary_error",
                        f"{agent_name} summary post failed for {task_id}",
                        {
                            "agent_id": agent_id,
                            "agent_name": agent_name,
                            "task_id": task_id,
                            "error": str(summary_ref)[:240],
                        },
                    )
                print(f"[{agent_name.upper()}] Tamamlandı: {task_id}")

        except Exception as e:
            _record_agent_os_event(
                "tool_task_error",
                f"{agent_name} poll error | {str(e)[:120]}",
                {"agent_name": agent_name, "agent_id": agent_id, "error": str(e)[:240]},
            )
            print(f"[{agent_name.upper()}] Poll hatası: {e}")

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Kullanım: python agent_runner.py [demir|selin|kaan|celik]")
        sys.exit(1)
    run(sys.argv[1])
