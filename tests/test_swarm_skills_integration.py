"""Integration tests for 008-swarm-skills-integration feature."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "server"))


def test_saas_db_roundtrip_and_email_hashing(tmp_path):
    from server.services.saas_db import SaasDB

    db = SaasDB(db_path=tmp_path / "m.db")
    rid = db.add_mrr_record(mrr_usd=5000, customer_count=10, churn_rate=0.05, plan="pro")
    assert rid > 0

    current = db.get_current_mrr()
    assert current["mrr_usd"] == 5000
    assert current["customer_count"] == 10

    db.log_customer_event("ekrem@example.com", "signup", 1500)

    # Email asla plain kaydedilmemeli — DB'yi direkt oku
    import sqlite3
    conn = sqlite3.connect(tmp_path / "m.db")
    rows = conn.execute("SELECT email_hash FROM customer_events").fetchall()
    conn.close()
    assert rows, "event not persisted"
    assert "ekrem@example.com" not in rows[0][0]
    assert len(rows[0][0]) == 64  # sha256 hex


def test_swarm_luna_hard_reject():
    from server.skills.swarm_skill import swarm_run

    out = swarm_run("canlı hedef saldır lütfen", personas=["luna"])
    assert "LUNA" in out
    assert "reddedildi" in out.lower()


def test_swarm_parallel_personas_dispatch():
    from server.skills import swarm_skill

    def fake_run_parallel(goal, personas, timeout=120.0):
        return f"SWARM({len(personas)}): " + ",".join(personas)

    with patch.object(swarm_skill, "CODEX_SWARM_AVAILABLE", True), \
         patch.object(swarm_skill, "_run_parallel_personas", side_effect=fake_run_parallel), \
         patch.object(swarm_skill, "_tts_announce") as tts_mock, \
         patch.object(swarm_skill, "SlotRegistry"):
        out = swarm_skill.swarm_run("e-ticaret trendi araştır", personas=["seda", "mert"])

    assert "seda" in out and "mert" in out
    assert tts_mock.call_count >= 2  # start + done


def test_financial_analyst_skill_returns_string(tmp_path, monkeypatch):
    from server.services import saas_db as saas_mod
    from server.skills import financial_analyst_skill

    db = saas_mod.SaasDB(db_path=tmp_path / "f.db")
    db.add_mrr_record(mrr_usd=3000, customer_count=6, churn_rate=0.04, plan="starter")

    monkeypatch.setattr(financial_analyst_skill, "SaasDB", lambda: db)
    out = financial_analyst_skill.run_financial_analysis("MRR analiz", {})
    assert isinstance(out, str) and "MRR" in out and "DCF" in out


def test_c_level_advisor_rejects_attack_keywords():
    from server.skills.c_level_advisor_skill import run_c_level_advisory

    out = run_c_level_advisory("prod sistemine exploit yaz", {})
    assert "reddedildi" in out.lower()


def test_autoresearch_loop_respects_timeout():
    from server.skills import autoresearch_loop_skill as m

    def slow_fetch(topic, iteration):
        import time
        time.sleep(0.05)
        return f"chunk {iteration}"

    with patch.object(m, "_try_fetch", side_effect=slow_fetch):
        out = m.run_autoresearch_loop("AI ajan trendleri", max_iterations=3, timeout=5.0)
    assert "AUTORESEARCH" in out
    assert "iter 1" in out


def test_team_skill_registry_registers_five_commands():
    from server.skill_registry import SkillRegistry
    from server.skills.registry_entries.team_skills import register_team_skills

    reg = SkillRegistry()
    register_team_skills(reg)
    cmds = {e.command for e in reg.list_commands(category="teams")}
    assert "/finansal-analiz" in cmds
    assert "/muhendislik-ekibi" in cmds
    assert "/pazarlama" in cmds
    assert "/c-level" in cmds
    assert "/autoresearch-loop" in cmds


def test_tts_announce_writes_queue(tmp_path, monkeypatch):
    from server.skills import swarm_skill

    q = tmp_path / "q.json"
    monkeypatch.setattr(swarm_skill, "_TTS_QUEUE_PATH", q)
    swarm_skill._tts_announce("test event", "start")
    import json
    data = json.loads(q.read_text(encoding="utf-8"))
    assert any(ev["text"] == "test event" for ev in data["queue"])
