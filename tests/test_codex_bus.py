from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from server.codex_bus import CodexBus


def test_post_is_idempotent_for_same_event(tmp_path) -> None:
    bus = CodexBus(path=tmp_path / "_bus.jsonl")

    first = bus.post("atlas", "job_started", {"summary": "ilk"}, job_id="job-1", event_id="evt-1")
    second = bus.post("atlas", "job_started", {"summary": "ilk"}, job_id="job-1", event_id="evt-1")

    assert first["event_id"] == second["event_id"]
    assert len(bus.read_since(limit=10)) == 1


def test_concurrent_post_writes_all_events(tmp_path) -> None:
    bus = CodexBus(path=tmp_path / "_bus.jsonl")

    def _post(index: int) -> None:
        bus.post("forge", "job_completed", {"summary": f"event-{index}"}, job_id=f"job-{index}", event_id=f"evt-{index}")

    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(_post, range(10)))

    events = bus.read_since(limit=20)
    assert len(events) == 10


def test_build_peer_context_block_formats_recent_events(tmp_path) -> None:
    bus = CodexBus(path=tmp_path / "_bus.jsonl")
    bus.post("forge", "job_completed", {"summary": "bridge tamam", "files_touched": ["server/bridge.py"]}, job_id="job-1", event_id="evt-1")
    bus.post("atlas", "peer_ask", {"question": "API kontratini kontrol eder misin?", "target_slot": "shield"}, job_id="job-2", event_id="evt-2")

    context = bus.build_peer_context_block("shield", limit=5)

    assert context.startswith("# Peer Context")
    assert "bridge tamam" in context
    assert "API kontratini kontrol eder misin?" in context


def test_lock_claim_and_release_prevent_parallel_edits(tmp_path) -> None:
    bus = CodexBus(path=tmp_path / "_bus.jsonl")
    target = "server/bridge.py"

    assert bus.claim_lock("atlas", target, job_id="job-1") is True
    assert bus.claim_lock("forge", target, job_id="job-2") is False
    assert bus.release_lock("atlas", target, job_id="job-1") is True
    assert bus.claim_lock("forge", target, job_id="job-2") is True
