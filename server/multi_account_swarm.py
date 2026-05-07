#!/usr/bin/env python3
"""
Multi-Account Swarm Orchestrator for Jarvis Mission Control
Enables 5 Codex accounts to work in parallel on decomposed tasks.

Usage:
    from multi_account_swarm import VoiceTaskDispatcher, ParallelCodexDispatcher, QuotaTracker
    
    dispatcher = ParallelCodexDispatcher(QuotaTracker())
    voice = VoiceTaskDispatcher(dispatcher)
    result = await voice.process_voice_command("Paralel olarak 5 görev çöz")
"""

import asyncio
import json
import time
import logging
import os
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path
import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

# ==================== CONFIGURATION ====================

class CodexSlot(Enum):
    """5 Codex account slots mapped to personas."""
    FORGE = "forge"      # Seda, Mert → code/debug
    NEXUS = "nexus"      # Sabrican → ops/automation
    SPARK = "spark"      # Eren, Buse → content/research
    ATLAS = "atlas"      # Sabri → strategy/planning
    SHIELD = "shield"    # Luna → security (lab-only)

PERSONA_TO_SLOT = {
    "seda": CodexSlot.FORGE,
    "mert": CodexSlot.FORGE,
    "sabrican": CodexSlot.NEXUS,
    "eren": CodexSlot.SPARK,
    "buse": CodexSlot.SPARK,
    "sabri": CodexSlot.ATLAS,
    "luna": CodexSlot.SHIELD,
    "jarvis": CodexSlot.FORGE,  # fallback
}

# ==================== MODELS ====================

@dataclass
class Task:
    """Single task for Codex execution."""
    id: str
    prompt: str
    persona: Optional[str] = None
    priority: int = 0  # 0=normal, higher=urgent
    timeout: int = 120  # seconds
    
    @property
    def slot(self) -> CodexSlot:
        if self.persona and self.persona in PERSONA_TO_SLOT:
            return PERSONA_TO_SLOT[self.persona]
        return CodexSlot.FORGE  # default

@dataclass
class TaskResult:
    """Result from Codex execution."""
    task_id: str
    slot: CodexSlot
    status: str  # "success", "rate_limit", "error", "timeout"
    output: Optional[str] = None
    error: Optional[str] = None
    duration: float = 0.0
    timestamp: str = ""

class RateLimitError(Exception):
    """Raised when Codex returns 429."""
    pass

# ==================== QUOTA TRACKING ====================

class QuotaTracker:
    """
    Track Codex quotas per slot.
    
    Stores state in: state/codex_quotas.json
    Format:
    {
      "forge": {
        "calls_today": 45,
        "limit": 100,
        "reset_at": "2026-04-16T00:00:00Z",
        "cooldown_until": null
      },
      ...
    }
    """
    
    STATE_FILE = Path("state/codex_quotas.json")
    
    def __init__(self, daily_limit: int = 100):
        self.daily_limit = daily_limit
        self.quotas = {}
        self._init_quotas()
    
    def _init_quotas(self):
        """Initialize quota tracking for all slots."""
        if self.STATE_FILE.exists():
            with open(self.STATE_FILE) as f:
                data = json.load(f)
                self.quotas = data
        else:
            # Fresh state
            reset_tomorrow = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
            self.quotas = {
                slot.value: {
                    "calls_today": 0,
                    "limit": self.daily_limit,
                    "reset_at": reset_tomorrow,
                    "cooldown_until": None,
                }
                for slot in CodexSlot
            }
            self._persist()
    
    def _persist(self):
        """Save quota state to disk."""
        self.STATE_FILE.parent.mkdir(exist_ok=True)
        with open(self.STATE_FILE, "w") as f:
            json.dump(self.quotas, f, indent=2)
    
    def get_available_slot(self) -> Optional[CodexSlot]:
        """Return first available slot, or None if all exhausted."""
        for slot in CodexSlot:
            if self.check_available(slot):
                return slot
        return None
    
    def check_available(self, slot: CodexSlot) -> bool:
        """Check if slot is available for use."""
        quota = self.quotas.get(slot.value, {})
        
        # Check daily limit
        if quota.get("calls_today", 0) >= quota.get("limit", self.daily_limit):
            return False
        
        # Check cooldown
        cooldown_until = quota.get("cooldown_until")
        if cooldown_until:
            if datetime.fromisoformat(cooldown_until.replace("Z", "+00:00")) > datetime.utcnow():
                return False
        
        return True
    
    def mark_used(self, slot: CodexSlot):
        """Increment call count for slot."""
        quota = self.quotas[slot.value]
        quota["calls_today"] = quota.get("calls_today", 0) + 1
        self._persist()
        logger.info(f"Slot {slot.value}: {quota['calls_today']}/{quota['limit']} calls")
    
    def on_rate_limit(self, slot: CodexSlot, wait_seconds: int = 60):
        """Mark slot as rate-limited until wait_seconds pass."""
        cooldown_until = (datetime.utcnow() + timedelta(seconds=wait_seconds)).isoformat() + "Z"
        self.quotas[slot.value]["cooldown_until"] = cooldown_until
        self._persist()
        logger.warning(f"Slot {slot.value} rate-limited until {cooldown_until}")
    
    def reset_cooldown_if_expired(self, slot: CodexSlot):
        """Clear cooldown if time has passed."""
        cooldown_until = self.quotas[slot.value].get("cooldown_until")
        if cooldown_until:
            if datetime.fromisoformat(cooldown_until.replace("Z", "+00:00")) <= datetime.utcnow():
                self.quotas[slot.value]["cooldown_until"] = None
                self._persist()

# ==================== PARALLEL DISPATCH ====================

class ParallelCodexDispatcher:
    """Dispatch multiple tasks to Codex slots in parallel."""
    
    def __init__(self, quota_tracker: QuotaTracker):
        self.quota = quota_tracker
        self.active_tasks: Dict[str, asyncio.Task] = {}
    
    async def dispatch_parallel(self, tasks: List[Task]) -> Dict[str, TaskResult]:
        """
        Execute multiple tasks in parallel across Codex slots.
        
        Args:
            tasks: List of Task objects
        
        Returns:
            {task_id: TaskResult, ...}
        """
        if len(tasks) > len(CodexSlot):
            raise ValueError(f"Too many tasks ({len(tasks)}), max {len(CodexSlot)}")
        
        logger.info(f"Dispatching {len(tasks)} tasks in parallel...")
        
        # Map tasks to slots
        slot_assignments = await self._assign_slots(tasks)
        
        # Run concurrently
        futures = {}
        for task in tasks:
            slot = slot_assignments[task.id]
            fut = asyncio.create_task(
                self._execute_with_retry(task, slot)
            )
            futures[task.id] = fut
            self.active_tasks[task.id] = fut
        
        # Gather results
        results = {}
        for task_id, fut in futures.items():
            try:
                results[task_id] = await asyncio.wait_for(
                    fut, 
                    timeout=tasks[0].timeout  # Use first task's timeout
                )
            except asyncio.TimeoutError:
                results[task_id] = TaskResult(
                    task_id=task_id,
                    slot=slot_assignments[task_id],
                    status="timeout",
                    error="Task exceeded timeout",
                    timestamp=datetime.utcnow().isoformat()
                )
            finally:
                self.active_tasks.pop(task_id, None)
        
        return results
    
    async def _assign_slots(self, tasks: List[Task]) -> Dict[str, CodexSlot]:
        """Assign each task to an available Codex slot."""
        assignment = {}
        used_slots = set()
        
        for task in sorted(tasks, key=lambda t: t.priority, reverse=True):
            # Try preferred slot first
            slot = task.slot
            if self.quota.check_available(slot) and slot not in used_slots:
                assignment[task.id] = slot
                used_slots.add(slot)
            else:
                # Find alternative
                for alt_slot in CodexSlot:
                    if self.quota.check_available(alt_slot) and alt_slot not in used_slots:
                        assignment[task.id] = alt_slot
                        used_slots.add(alt_slot)
                        break
                else:
                    # Fallback: use any slot (will retry if rate-limited)
                    for slot_enum in CodexSlot:
                        if slot_enum not in used_slots:
                            assignment[task.id] = slot_enum
                            used_slots.add(slot_enum)
                            break
        
        logger.info(f"Slot assignment: {assignment}")
        return assignment
    
    async def _execute_with_retry(self, task: Task, slot: CodexSlot, 
                                   max_retries: int = 3) -> TaskResult:
        """Execute task with exponential backoff on rate limit."""
        start = time.time()
        
        for attempt in range(max_retries):
            try:
                # Check cooldown
                self.quota.reset_cooldown_if_expired(slot)
                if not self.quota.check_available(slot):
                    raise RateLimitError(f"Slot {slot.value} currently rate-limited")
                
                # Mark usage
                self.quota.mark_used(slot)
                
                # Execute (placeholder)
                output = await self._call_codex_api(task.prompt, slot)
                
                return TaskResult(
                    task_id=task.id,
                    slot=slot,
                    status="success",
                    output=output,
                    duration=time.time() - start,
                    timestamp=datetime.utcnow().isoformat()
                )
            
            except RateLimitError as e:
                wait_time = 2 ** attempt
                self.quota.on_rate_limit(slot, wait_seconds=wait_time)
                
                if attempt < max_retries - 1:
                    logger.warning(f"Task {task.id}: Rate limited, retrying in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    return TaskResult(
                        task_id=task.id,
                        slot=slot,
                        status="rate_limit",
                        error=f"Rate limited after {max_retries} retries",
                        duration=time.time() - start,
                        timestamp=datetime.utcnow().isoformat()
                    )
            
            except Exception as e:
                return TaskResult(
                    task_id=task.id,
                    slot=slot,
                    status="error",
                    error=str(e),
                    duration=time.time() - start,
                    timestamp=datetime.utcnow().isoformat()
                )
        
        return TaskResult(
            task_id=task.id,
            slot=slot,
            status="error",
            error="Unknown error",
            duration=time.time() - start,
            timestamp=datetime.utcnow().isoformat()
        )
    
    async def _call_codex_api(self, prompt: str, slot: CodexSlot) -> str:
        """
        Placeholder for actual Codex API call.
        Replace with real http.post() to API endpoint.
        """
        # Simulate API call
        await asyncio.sleep(0.5)
        return f"✓ Processed by {slot.value}: {prompt[:50]}..."

# ==================== VOICE INTEGRATION ====================

class VoiceTaskDispatcher:
    """Bridge between voice input and parallel Codex execution."""
    
    PARALLEL_KEYWORDS = {"paralel", "aynı anda", "simultaneously", "concurrent"}
    DECOMPOSE_PROMPT = """Sen görev decomposer'sın. Kullanıcının 1 hedefini 5 tane independent subtask'e böl.
Her subtask'ı farklı bir persona'ya atayacağız.

Personas:
- seda: Kod, debug, PR review
- mert: Kod, araştırma
- eren: Veri, analiz, dashboard
- buse: Marketing, landing, content
- sabri: Strateji, planning, creative
- luna: Güvenlik, audit

Format (MUTLAKA JSON):
{{
  "tasks": [
    {{"id": "t1", "prompt": "Konkret görev 1", "persona": "seda", "priority": 0}},
    ...
  ]
}}

Hedef: {goal}

JSON çıktısını direkt ver, ek text yok."""
    
    def __init__(self, codex_dispatcher: ParallelCodexDispatcher):
        self.dispatcher = codex_dispatcher
        self.groq_api_key = os.environ.get("GROQ_API_KEY", "")
        self.groq_model = "qwen-qwq-32b"
    
    async def process_voice_command(self, text: str) -> str:
        """
        Process voice input → decompose → parallel execute → synthesize response.
        
        Args:
            text: Voice-to-text input (Turkish or English)
        
        Returns:
            TTS-ready response string
        """
        logger.info(f"Voice input: {text}")
        
        # Detect parallel intent
        is_parallel = any(kw in text.lower() for kw in self.PARALLEL_KEYWORDS)
        
        # Decompose into tasks
        tasks = await self._decompose_tasks(text)
        
        if not is_parallel or len(tasks) <= 1:
            # Single execution
            logger.info("Single task execution mode")
            result = await self.dispatcher._call_codex_api(
                tasks[0].prompt, 
                tasks[0].slot
            )
            return f"Sonuç: {result}"
        
        # Parallel execution
        logger.info(f"Parallel execution mode: {len(tasks)} tasks")
        results = await self.dispatcher.dispatch_parallel(tasks)
        
        # Synthesize response
        narrative = self._synthesize_response(results)
        
        return narrative
    
    async def _decompose_tasks(self, text: str) -> List[Task]:
        """
        Decompose voice input into multiple tasks using LLM.
        Falls back to simple heuristics if LLM unavailable.
        """
        # Try LLM first
        if self.groq_api_key:
            try:
                tasks = await self._decompose_with_groq(text)
                if tasks:
                    logger.info(f"LLM decomposed into {len(tasks)} tasks")
                    return tasks
            except Exception as e:
                logger.warning(f"Groq decomposition failed, using heuristics: {e}")
        
        # Fallback: Simple heuristics
        logger.info("Using heuristic task decomposition")
        return self._decompose_heuristic(text)
    
    async def _decompose_with_groq(self, text: str) -> Optional[List[Task]]:
        """Call Groq API to decompose task."""
        import json as json_lib
        
        prompt = self.DECOMPOSE_PROMPT.format(goal=text)
        
        payload = {
            "model": self.groq_model,
            "messages": [
                {"role": "system", "content": "Sen görev decomposer'sın."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000,
        }
        
        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json_lib.dumps(payload).encode(),
                headers=headers
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                response = json_lib.loads(r.read())
                content = response["choices"][0]["message"]["content"]
                
                # Parse JSON from response
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    data = json_lib.loads(json_match.group())
                    tasks = []
                    for i, t in enumerate(data.get("tasks", [])[:5]):
                        tasks.append(Task(
                            id=t.get("id", f"t{i}"),
                            prompt=t.get("prompt", text),
                            persona=t.get("persona", "seda"),
                            priority=t.get("priority", 0),
                            timeout=120
                        ))
                    return tasks if tasks else None
        except Exception as e:
            logger.error(f"Groq API error: {e}")
            return None
    
    def _decompose_heuristic(self, text: str) -> List[Task]:
        """Fallback heuristic decomposition."""
        tasks = []
        
        # If text mentions "5" or "paralel" → create 5 tasks
        num_tasks = 5 if ("5" in text or "paralel" in text.lower()) else 3
        
        # Distribute personas
        personas = ["seda", "eren", "buse", "sabri", "luna"][:num_tasks]
        
        for i, persona in enumerate(personas):
            tasks.append(Task(
                id=f"t{i+1}",
                prompt=f"{text} (Kısım {i+1}: {persona} perspektifi)",
                persona=persona,
                priority=0,
                timeout=120
            ))
        
        return tasks
    
    def _synthesize_response(self, results: Dict[str, TaskResult]) -> str:
        """
        Combine multiple TaskResult's into TTS-ready narrative.
        
        Filters by status, extracts outputs, builds coherent narration.
        """
        narrative_parts = []
        successful = [r for r in results.values() if r.status == "success"]
        failed = [r for r in results.values() if r.status != "success"]
        
        # Start
        if len(successful) > 0 and len(failed) == 0:
            narrative_parts.append(f"✓ Tüm {len(successful)} görev tamamlandı.")
        elif len(successful) > 0:
            narrative_parts.append(f"✓ {len(successful)} görev başarılı, {len(failed)} hata.")
        else:
            narrative_parts.append(f"Hata: {len(failed)} görev başarısız.")
        
        # Results
        for i, result in enumerate(sorted(successful, key=lambda r: r.task_id), 1):
            output_preview = (result.output[:100] + "...") if result.output and len(result.output) > 100 else result.output
            narrative_parts.append(f"Görev {i} ({result.slot.value}): {output_preview}")
        
        # Duration
        total_duration = sum(r.duration for r in results.values())
        narrative_parts.append(f"Toplam süre: {total_duration:.1f} saniye.")
        
        return "\n".join(narrative_parts)

# ==================== USAGE EXAMPLE ====================

async def main():
    """Demo usage."""
    logging.basicConfig(level=logging.INFO)
    
    # Initialize
    quota = QuotaTracker(daily_limit=100)
    dispatcher = ParallelCodexDispatcher(quota)
    voice_handler = VoiceTaskDispatcher(dispatcher)
    
    # Test 1: Single voice command
    print("\n--- Test 1: Single Command ---")
    result = await voice_handler.process_voice_command("Merhaba, nasılsın?")
    print(result)
    
    # Test 2: Parallel voice command
    print("\n--- Test 2: Parallel Execution ---")
    result = await voice_handler.process_voice_command(
        "Paralel olarak 5 yapay zeka görevini çöz"
    )
    print(result)
    
    # Test 3: Check quota
    print("\n--- Quota Status ---")
    with open(quota.STATE_FILE) as f:
        print(json.dumps(json.load(f), indent=2))

if __name__ == "__main__":
    asyncio.run(main())
