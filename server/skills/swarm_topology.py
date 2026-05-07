"""
Swarm Topology — Swarms + CrewAI pattern'lerinden ilham alınarak native Jarvis implementasyonu.

Desteklenen topologiler:
  - sequential : A → B → C zinciri (her agent bir öncekinin çıktısını alır)
  - parallel   : A, B, C aynı anda çalışır, hepsi aynı input alır
  - hierarchical: Orchestrator önce karar verir, sonra sub-agent'lara dağıtır

Referans:
  - kyegomez/swarms (Agent, SequentialWorkflow, ConcurrentWorkflow, HierarchicalSwarm)
  - crewAIInc/crewAI (Crew, Flow — event-driven)
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Optional


# ─── Agent Tanımı ────────────────────────────────────────────────────────────

class JarvisAgent:
    """
    Tek bir uzman agent.
    name      : agent adı (demir, selin, kaan, celik...)
    agent_id  : task_bus ID (backend, voice, video, security)
    handler   : Callable[[str, call_llm], str] — görevi çalıştıran fonksiyon
    """
    def __init__(self, name: str, agent_id: str, handler: Callable, description: str = ""):
        self.name = name
        self.agent_id = agent_id
        self.handler = handler
        self.description = description

    def run(self, task: str, call_llm: Optional[Callable] = None) -> str:
        try:
            return self.handler({"payload": task, "task_type": "swarm"}, call_llm)
        except Exception as e:
            return f"[{self.name}] hata: {e}"


# ─── Topologiler ──────────────────────────────────────────────────────────────

def run_sequential(agents: list[JarvisAgent], task: str, call_llm=None) -> dict:
    """
    Zincir: ilk agent görevi alır, çıktısı sonrakine input olur.
    Swarms SequentialWorkflow pattern.
    """
    results = []
    current_input = task
    for agent in agents:
        output = agent.run(current_input, call_llm)
        results.append({"agent": agent.name, "output": output})
        current_input = output  # bir sonrakine geç
    return {"topology": "sequential", "steps": results, "final": current_input}


def run_parallel(agents: list[JarvisAgent], task: str, call_llm=None, timeout: int = 30) -> dict:
    """
    Tüm agent'lar aynı anda çalışır, hepsi aynı görevi alır.
    Swarms ConcurrentWorkflow / crewAI parallel Crew pattern.
    """
    results = []
    with ThreadPoolExecutor(max_workers=len(agents)) as pool:
        futures = {pool.submit(a.run, task, call_llm): a.name for a in agents}
        for future in as_completed(futures, timeout=timeout):
            agent_name = futures[future]
            try:
                output = future.result()
            except Exception as e:
                output = f"hata: {e}"
            results.append({"agent": agent_name, "output": output})
    return {"topology": "parallel", "steps": results, "final": "\n\n".join(r["output"] for r in results)}


def run_hierarchical(
    orchestrator: JarvisAgent,
    workers: list[JarvisAgent],
    task: str,
    call_llm=None,
) -> dict:
    """
    Orchestrator önce görevi analiz eder ve hangi worker'a gideceğine karar verir.
    Swarms HierarchicalSwarm / crewAI Crew with manager pattern.
    """
    # Orchestrator görevi analiz eder
    worker_names = ", ".join(f"{w.name}({w.description})" for w in workers)
    routing_prompt = (
        f"Sen orchestrator'sun. Görev: {task}\n"
        f"Mevcut uzmanlar: {worker_names}\n"
        "Görevi kime ver? Sadece isim yaz."
    )
    routing_decision = orchestrator.run(routing_prompt, call_llm)
    # En yakın worker'ı bul
    chosen = None
    for w in workers:
        if w.name.lower() in routing_decision.lower():
            chosen = w
            break
    if not chosen:
        chosen = workers[0]  # fallback: ilk worker

    worker_result = chosen.run(task, call_llm)
    return {
        "topology": "hierarchical",
        "orchestrator": orchestrator.name,
        "routing_decision": routing_decision,
        "chosen_worker": chosen.name,
        "steps": [
            {"agent": orchestrator.name, "output": routing_decision},
            {"agent": chosen.name, "output": worker_result},
        ],
        "final": worker_result,
    }


def format_topology_result(result: dict) -> str:
    nl = chr(10)
    topo = result.get("topology", "?")
    steps = result.get("steps", [])
    final = result.get("final", "")

    lines = [f"🕸️ Swarm Topoloji: {topo.upper()}"]
    if topo == "hierarchical":
        lines.append(f"Orchestrator: {result.get('orchestrator')} → {result.get('chosen_worker')}")
    lines.append(nl + "📊 Adımlar:")
    for s in steps:
        out = str(s.get("output",""))[:200]
        lines.append(f"  [{s['agent']}] {out}")
    lines.append(nl + "✅ Sonuç:")
    lines.append(final[:600] if final else "(boş)")
    return nl.join(lines)
