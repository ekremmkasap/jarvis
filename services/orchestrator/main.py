from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from services.orchestrator.task_queue import TaskQueue, Task, TaskStatus, TaskPriority
from services.orchestrator.safety import SafetyPolicy
from services.orchestrator.ws_broadcaster import WSBroadcaster
from services.orchestrator.agent_runner import AgentRunner

log = logging.getLogger("orchestrator.main")

app = FastAPI(title="Jarvis Mission Control Orchestrator", version="2.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

broadcaster = WSBroadcaster()
queue = TaskQueue(broadcaster=broadcaster)
safety = SafetyPolicy()
runner = AgentRunner(queue=queue, broadcaster=broadcaster, safety=safety)


class TaskRequest(BaseModel):
    goal: str
    agent: str = "planner"
    priority: str = "normal"
    context: dict[str, Any] = {}
    dry_run: bool = False


class VoiceCommand(BaseModel):
    text: str
    session_id: str = ""


@app.on_event("startup")
async def startup():
    asyncio.create_task(runner.run_loop())
    log.info("Orchestrator started on port %s", os.getenv("ORCHESTRATOR_PORT", "8091"))


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await broadcaster.connect(ws)
    try:
        while True:
            data = await ws.receive_text()
            if data == "ping":
                await ws.send_text("pong")
    except WebSocketDisconnect:
        broadcaster.disconnect(ws)


@app.post("/task")
async def create_task(req: TaskRequest):
    check = safety.check(goal=req.goal, agent=req.agent, context=req.context)
    if check.blocked:
        raise HTTPException(status_code=403, detail=f"Safety violation: {check.reason}")

    task = Task(
        id=str(uuid.uuid4())[:8],
        goal=req.goal,
        agent=req.agent,
        priority=TaskPriority(req.priority),
        context=req.context,
        dry_run=req.dry_run,
        created_at=datetime.now(timezone.utc).isoformat(),
        requires_confirmation=check.requires_confirmation,
    )
    await queue.enqueue(task)
    await broadcaster.broadcast({"event": "task_created", "task": task.to_dict()})
    return {
        "task_id": task.id,
        "status": task.status.value,
        "requires_confirmation": check.requires_confirmation,
        "risk_score": check.risk_score,
    }


@app.get("/tasks")
async def list_tasks(limit: int = 50):
    return {"tasks": [t.to_dict() for t in queue.get_all(limit=limit)]}


@app.get("/tasks/{task_id}")
async def get_task(task_id: str):
    task = queue.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()


@app.post("/tasks/{task_id}/confirm")
async def confirm_task(task_id: str):
    task = queue.get(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    task.requires_confirmation = False
    task.status = TaskStatus.QUEUED
    await queue._queue.put(task)
    await broadcaster.broadcast({"event": "task_confirmed", "task": task.to_dict()})
    return {"ok": True}


@app.get("/agents")
async def list_agents():
    return {"agents": runner.list_agents()}


@app.post("/voice")
async def voice_command(cmd: VoiceCommand):
    text = cmd.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Empty command")

    # Intent routing based on keywords
    agent = "planner"
    text_lower = text.lower()
    if any(k in text_lower for k in ["analiz", "analyze", "repository", "repo", "health"]):
        agent = "repo_analyst"
    elif any(k in text_lower for k in ["review", "pr", "pull request"]):
        agent = "reviewer"
    elif any(k in text_lower for k in ["debug", "hata", "error", "fix", "ci failure"]):
        agent = "debug"
    elif any(k in text_lower for k in ["release", "changelog", "versiyon"]):
        agent = "release"
    elif any(k in text_lower for k in ["doc", "readme", "documentation"]):
        agent = "docs"
    elif any(k in text_lower for k in ["status", "durum", "health check"]):
        agent = "mission_control"

    req = TaskRequest(
        goal=text,
        agent=agent,
        context={"source": "voice", "session_id": cmd.session_id},
    )
    return await create_task(req)


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "queue_size": queue.size(),
        "ws_connections": broadcaster.connection_count(),
        "agents": len(runner.list_agents()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    port = int(os.getenv("ORCHESTRATOR_PORT", "8091"))
    uvicorn.run(
        "services.orchestrator.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info",
    )
