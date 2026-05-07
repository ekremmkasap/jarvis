from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from server import codex_orchestrator
from server import multi_account_swarm


class _FakeQuotaTracker:
    def record_dispatch(self, slot: str) -> None:
        self.last_dispatch = slot

    def record_completion(self, slot: str, status: str) -> None:
        self.last_completion = (slot, status)


class _FakeJobManager:
    def __init__(self) -> None:
        self.agent_updates: list[tuple[str, str, dict[str, object]]] = []

    def update_agent_state(self, job_id: str, slot: str, **fields: object) -> None:
        self.agent_updates.append((job_id, slot, fields))


class _FakeProc:
    def __init__(
        self,
        *,
        stdout: str = "ok",
        stderr: str = "",
        returncode: int = 0,
        timeout_once: bool = False,
        wait_timeout: bool = False,
    ) -> None:
        self._stdout = stdout
        self._stderr = stderr
        self.returncode = returncode
        self.timeout_once = timeout_once
        self.wait_timeout = wait_timeout
        self.communicate_calls = 0
        self.terminated = False
        self.killed = False

    def communicate(self, timeout: int | None = None) -> tuple[str, str]:
        self.communicate_calls += 1
        if self.timeout_once and self.communicate_calls == 1:
            raise subprocess.TimeoutExpired(cmd=["codex"], timeout=timeout or 0)
        return (self._stdout, self._stderr)

    def terminate(self) -> None:
        self.terminated = True

    def wait(self, timeout: int | None = None) -> int:
        if self.wait_timeout:
            raise subprocess.TimeoutExpired(cmd=["codex"], timeout=timeout or 0)
        return self.returncode

    def kill(self) -> None:
        self.killed = True

    def poll(self) -> int | None:
        return None


def test_run_codex_task_sets_codex_home_env(monkeypatch) -> None:
    fake_job_manager = _FakeJobManager()
    fake_quota = _FakeQuotaTracker()
    captured: dict[str, object] = {}

    def _fake_popen(*args, **kwargs):
        captured["env"] = kwargs["env"]
        captured["cwd"] = kwargs["cwd"]
        return _FakeProc(stdout="tamam")

    monkeypatch.setattr(codex_orchestrator, "_resolve_codex_command", lambda: ["codex"])
    monkeypatch.setattr(codex_orchestrator, "_load_profile", lambda agent: "profil")
    monkeypatch.setattr(
        codex_orchestrator,
        "_resolve_execution_context",
        lambda slot: {
            "codex_home": str(Path("C:/tmp/state/codex-accounts") / slot),
            "cwd": "C:/tmp/repo",
            "worktree": "",
        },
    )
    monkeypatch.setattr(codex_orchestrator, "get_quota_tracker", lambda: fake_quota)
    monkeypatch.setattr(codex_orchestrator, "get_job_manager", lambda: fake_job_manager)
    monkeypatch.setattr(codex_orchestrator, "_emit_codex_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(codex_orchestrator, "_failover_job", lambda *args, **kwargs: None)
    monkeypatch.setattr(codex_orchestrator.subprocess, "Popen", _fake_popen)

    codex_orchestrator._run_codex_task("job-1", "forge", "bridge endpointini duzelt")

    env = captured["env"]
    assert isinstance(env, dict)
    assert env["CODEX_HOME"].endswith("codex-accounts\\forge")
    assert captured["cwd"] == "C:/tmp/repo"
    assert fake_job_manager.agent_updates[-1][2]["status"] == "done"


def test_run_codex_task_terminates_then_kills_when_timeout_persists(monkeypatch) -> None:
    fake_job_manager = _FakeJobManager()
    fake_quota = _FakeQuotaTracker()
    fake_proc = _FakeProc(timeout_once=True, wait_timeout=True)

    monkeypatch.setattr(codex_orchestrator, "_resolve_codex_command", lambda: ["codex"])
    monkeypatch.setattr(codex_orchestrator, "_load_profile", lambda agent: "profil")
    monkeypatch.setattr(
        codex_orchestrator,
        "_resolve_execution_context",
        lambda slot: {
            "codex_home": str(Path("C:/tmp/state/codex-accounts") / slot),
            "cwd": "C:/tmp/repo",
            "worktree": "",
        },
    )
    monkeypatch.setattr(codex_orchestrator, "get_quota_tracker", lambda: fake_quota)
    monkeypatch.setattr(codex_orchestrator, "get_job_manager", lambda: fake_job_manager)
    monkeypatch.setattr(codex_orchestrator, "_emit_codex_event", lambda *args, **kwargs: None)
    monkeypatch.setattr(codex_orchestrator, "_failover_job", lambda *args, **kwargs: None)
    monkeypatch.setattr(codex_orchestrator.subprocess, "Popen", lambda *args, **kwargs: fake_proc)

    codex_orchestrator._run_codex_task("job-2", "forge", "uzun is")

    assert fake_proc.terminated is True
    assert fake_proc.killed is True
    assert "Zaman asimi (600s)" in str(fake_job_manager.agent_updates[-1][2]["output"])


@pytest.mark.asyncio
async def test_multi_account_swarm_uses_unique_codex_home_per_slot(monkeypatch) -> None:
    dispatcher = multi_account_swarm.ParallelCodexDispatcher(multi_account_swarm.QuotaTracker())
    captured_homes: list[str] = []

    class _AsyncProc:
        def __init__(self) -> None:
            self.returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return (b"tamam", b"")

        def terminate(self) -> None:
            pass

        def kill(self) -> None:
            pass

    async def _fake_create_subprocess_exec(*args, **kwargs):
        captured_homes.append(kwargs["env"]["CODEX_HOME"])
        return _AsyncProc()

    monkeypatch.setattr(multi_account_swarm, "_resolve_codex_command", lambda: ["codex"])
    monkeypatch.setattr(multi_account_swarm.asyncio, "create_subprocess_exec", _fake_create_subprocess_exec)

    for slot in multi_account_swarm.CodexSlot:
        result = await dispatcher._call_codex_api("test gorevi", slot)
        assert "tamam" in result

    assert len(captured_homes) == 5
    assert len(set(captured_homes)) == 5
