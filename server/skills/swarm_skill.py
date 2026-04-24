"""
Jarvis Swarm Skill - UPGRADED v2.0
Multi-Account Codex Orchestration (5 parallel slots)
Fallback to OpenClaw (port 7090) if Codex unavailable
"""

import sys
import asyncio
import json
import logging
import os
import time
import uuid
import concurrent.futures
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, List

# Add parent to imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from multi_account_swarm import ParallelCodexDispatcher, QuotaTracker, VoiceTaskDispatcher
    from agents.codex_slot_agents import SlotRegistry, CodexSlot
    CODEX_SWARM_AVAILABLE = True
except ImportError:
    CODEX_SWARM_AVAILABLE = False

logger = logging.getLogger(__name__)

BYPASS_PORT = int(os.environ.get("BYPASS_PORT", 7090))
SWARM_URL = f"http://localhost:{BYPASS_PORT}/swarm"
PARALLEL_KEYWORDS = {
    "paralel", "aynı anda", "simultaneously", "5 görev", "5 tane", "5 task",
    "ekip", "team", "takım", "agent team",
}

# Persona → Codex slot mapping (matches config/agents.yaml)
PERSONA_SLOT = {
    "seda": "forge",
    "mert": "nexus",
    "buse": "spark",
    "eren": "spark",
    "sabri": "atlas",
    "luna": "shield",
    "sabrican": "nexus",
}

# Luna hard-reject guard
LUNA_HARD_REJECT = {"exploit", "hack target", "saldır", "canlı hedef", "ddos", "attack prod"}

# TTS queue path (bridge ↔ hey_jarvis köprüsü)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_TTS_QUEUE_PATH = _REPO_ROOT / "state" / "swarm_tts_queue.json"


def _tts_announce(text: str, event_type: str = "info") -> None:
    """Swarm lifecycle event'i hey_jarvis.py'nin polling göreceği dosyaya yaz."""
    try:
        _TTS_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {"queue": []}
        if _TTS_QUEUE_PATH.exists():
            try:
                data = json.loads(_TTS_QUEUE_PATH.read_text(encoding="utf-8"))
            except Exception:
                data = {"queue": []}
        queue = data.get("queue", [])
        queue.append({
            "event_id": uuid.uuid4().hex,
            "text": text[:200],
            "type": event_type,
            "ts": int(time.time()),
        })
        data["queue"] = queue[-10:]  # son 10 event
        _TTS_QUEUE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning(f"TTS announce failed: {e}")


def _luna_rejected(goal: str, personas: Optional[List[str]]) -> Optional[str]:
    if personas and "luna" in [p.lower() for p in personas]:
        low = (goal or "").lower()
        if any(kw in low for kw in LUNA_HARD_REJECT):
            return (
                "LUNA: Bu istek reddedildi. Yalnızca savunma amaçlı lab bağlamında çalışabilirim."
            )
    return None


def _format_swarm_results(results: dict) -> str:
    if not results:
        return "(swarm): sonuç yok — timeout veya slot kontası"
    lines = [f"SWARM TEAM — {len(results)} persona cevapladı"]
    for persona, out in results.items():
        lines.append(f"\n--- {persona.upper()} ---\n{str(out)[:1200]}")
    return "\n".join(lines)


def _run_parallel_personas(goal: str, personas: List[str], timeout: float = 120.0) -> str:
    """Paralel persona dispatch — ThreadPoolExecutor + aggregate timeout."""
    try:
        from multi_account_swarm import Task  # type: ignore
    except Exception:
        return "(swarm): multi_account_swarm import başarısız"

    async def _run_one(persona: str) -> str:
        try:
            slot_name = PERSONA_SLOT.get(persona.lower(), "forge")
            slot_enum = CodexSlot(slot_name)
            agent = SlotRegistry.get_agent(slot_enum)
            return await agent.execute_task(goal, persona=persona)
        except Exception as e:
            return f"(error {persona}: {e})"

    def _worker(persona: str) -> str:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(_run_one(persona))
        finally:
            loop.close()

    results: dict = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(_worker, p): p for p in personas}
        done, not_done = concurrent.futures.wait(futs, timeout=timeout)
        for f in done:
            try:
                results[futs[f]] = f.result()
            except Exception as e:
                results[futs[f]] = f"(error: {e})"
        for f in not_done:
            results[futs[f]] = "(timeout)"
            f.cancel()
    return _format_swarm_results(results)

# ==================== CODEX SWARM PATH ====================

class CodexSwarmOrchestrator:
    """Multi-account parallel Codex executor."""
    
    def __init__(self):
        SlotRegistry.init()
        self.quota = QuotaTracker(daily_limit=100)
        self.dispatcher = ParallelCodexDispatcher(self.quota)
        self.voice = VoiceTaskDispatcher(self.dispatcher)
    
    def execute_sync(self, goal: str) -> str:
        """Synchronous wrapper (bridge.py compatible)."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self._execute_async(goal))
            loop.close()
            return result
        except Exception as e:
            logger.exception(f"CodexSwarmOrchestrator error: {e}")
            return f"❌ Hata: {str(e)}"
    
    async def _execute_async(self, goal: str) -> str:
        """Core async logic."""
        is_parallel = any(kw in goal.lower() for kw in PARALLEL_KEYWORDS)
        
        if is_parallel:
            logger.info(f"Parallel mode: {goal}")
            return await self.voice.process_voice_command(goal)
        else:
            logger.info(f"Single mode: {goal}")
            return await self._single_execute(goal)
    
    async def _single_execute(self, goal: str) -> str:
        """Single task execution (non-parallel)."""
        from multi_account_swarm import Task
        
        task = Task(id="single", prompt=goal, persona="seda")
        slot = task.slot
        
        if not self.quota.check_available(slot):
            return f"❌ {slot.value} slotu kontasında. Lütfen daha sonra deneyin."
        
        self.quota.mark_used(slot)
        
        try:
            agent = SlotRegistry.get_agent(slot)
            result = await agent.execute_task(goal, persona="seda")
            return f"✅ {result}"
        except Exception as e:
            return f"❌ {slot.value}: {str(e)}"

# ==================== OPENCLAW FALLBACK ====================

def _post_openclaw(body):
    """Post to OpenClaw fallback."""
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        SWARM_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    except urllib.error.URLError as e:
        return {"ok": False, "error": str(e)}

def _execute_openclaw(goal, llm_url=None, cwd=None):
    """Fallback to OpenClaw agent swarm."""
    if not goal:
        return "❌ Hedef boş. Örnek: `/swarm npm bağımlılıkları kur`"

    body = {"goal": goal}
    if llm_url:
        body["llmUrl"] = llm_url
    if cwd:
        body["cwd"] = cwd

    r = _post_openclaw(body)

    if not r.get("ok"):
        return f"❌ Swarm hatası: {r.get('error', 'bilinmiyor')}"

    verdict = r.get("verdict", "?")
    emoji = {"pass": "✅", "fail": "❌", "pending": "⏸"}.get(verdict, "❓")
    lines = [
        f"{emoji} **Swarm Tamamlandı** — `{verdict.upper()}`",
        f"🎯 Hedef: {goal}",
        f"🔄 Loop: {r.get('loops', '?')}",
        f"📝 Özet: {r.get('summary', '')}",
        ""
    ]

    result_lines = r.get("resultLines", [])
    if result_lines:
        lines.append("**Adımlar:**")
        lines.extend(result_lines[:15])

    warnings = r.get("securityWarnings", [])
    if warnings:
        lines.append(f"\n⚠️ **Güvenlik uyarısı:** {len(warnings)} adımda hassas veri olabilir")

    return "\n".join(lines)

# ==================== MAIN ENTRY POINT ====================

_codex_executor: Optional[CodexSwarmOrchestrator] = None

def swarm_run(
    goal: str,
    llm_url: Optional[str] = None,
    cwd: Optional[str] = None,
    personas: Optional[List[str]] = None,
) -> str:
    """
    Main entry point for bridge.py

    Called from: server/bridge.py:2461 _handle_swarm_command()

    Routing:
    0. Luna hard-reject guard (if luna in personas + attack keyword)
    1. If `personas` verildi AND Codex available → paralel persona dispatch
    2. If "paralel"/"aynı anda" detected AND Codex available → CodexSwarmOrchestrator
    3. Otherwise → OpenClaw fallback (port 7090)
    """

    # 0. Luna defense-in-depth
    rejection = _luna_rejected(goal, personas)
    if rejection:
        return rejection

    # 1. Sabrican → OpenClaw integrator (always routed, Codex bağımsız)
    if personas and "sabrican" in [p.lower() for p in personas]:
        logger.info(f"[SWARM] Sabrican → OpenClaw integrator: {goal[:80]}")
        _tts_announce(f"Sabrican görevi OpenClaw'a yönlendiriliyor: {goal[:60]}", "start")
        try:
            from openclaw_bridge import run_openclaw_integrator  # type: ignore
        except ImportError:
            try:
                from server.openclaw_bridge import run_openclaw_integrator
            except ImportError:
                return _execute_openclaw(goal, llm_url=llm_url, cwd=cwd)
        result = run_openclaw_integrator(goal, deliver=False)
        _tts_announce("Sabrican görevi tamamlandı.", "done")
        return f"Sabrican/OpenClaw: {result.get('status', '?')}\n{str(result)[:800]}"

    # 2. Multi-persona parallel dispatch (Codex available)
    if personas and CODEX_SWARM_AVAILABLE:
        logger.info(f"[SWARM] Parallel personas={personas}: {goal[:80]}")
        _tts_announce(f"Swarm başlıyor: {goal[:60]}", "start")
        try:
            SlotRegistry.init()
        except Exception:
            pass
        result = _run_parallel_personas(goal, personas, timeout=120.0)
        _tts_announce(f"Tamamlandı. {len(personas)} görev.", "done")
        return result

    # 3. Detect parallel intent (legacy keyword path)
    is_parallel = any(kw in goal.lower() for kw in PARALLEL_KEYWORDS)

    if is_parallel and CODEX_SWARM_AVAILABLE:
        logger.info(f"[SWARM] Routing to CodexSwarmOrchestrator: {goal}")
        global _codex_executor
        if _codex_executor is None:
            _codex_executor = CodexSwarmOrchestrator()
        return _codex_executor.execute_sync(goal)

    # 4. Fallback to OpenClaw
    logger.info(f"[SWARM] Routing to OpenClaw: {goal}")
    return _execute_openclaw(goal, llm_url=llm_url, cwd=cwd)

