from __future__ import annotations

from pathlib import Path


def _patch_log(monkeypatch, tmp_path):
    from server.skills import zeynep_security_skill as skill
    monkeypatch.setattr(skill, "LOG_PATH", tmp_path / "zeynep.jsonl")
    return skill


def test_kvkk_audit_rejects_invalid_path(tmp_path, monkeypatch):
    skill = _patch_log(monkeypatch, tmp_path)
    result = skill.zeynep_kvkk_audit(str(tmp_path / "does_not_exist"))
    assert result["ok"] is False
    assert result["error"] == "invalid_path"


def test_kvkk_audit_detects_email_and_phone(tmp_path, monkeypatch):
    skill = _patch_log(monkeypatch, tmp_path)
    sample = tmp_path / "notes.txt"
    sample.write_text(
        "Musteri iletisim: ahmet@example.com, telefon 0555 123 45 67\n"
        "Normal satir.\n",
        encoding="utf-8",
    )

    result = skill.zeynep_kvkk_audit(str(tmp_path))
    assert result["ok"] is True
    assert result["total_findings"] >= 2
    types = {f["type"] for f in result["findings"]}
    assert "email" in types
    assert "telefon" in types


def test_kvkk_audit_redacts_tc_kimlik(tmp_path, monkeypatch):
    skill = _patch_log(monkeypatch, tmp_path)
    sample = tmp_path / "data.txt"
    sample.write_text("TC: 12345678901\n", encoding="utf-8")

    result = skill.zeynep_kvkk_audit(str(tmp_path))
    tc_findings = [f for f in result["findings"] if f["type"] == "tc_kimlik"]
    assert tc_findings, "TC kimlik pattern yakalanmadi"
    assert "12345678901" not in tc_findings[0]["sample"]
    assert "REDACTED" in tc_findings[0]["sample"]


def test_secret_scan_detects_and_redacts_aws_key(tmp_path, monkeypatch):
    skill = _patch_log(monkeypatch, tmp_path)
    sample = tmp_path / "config.env"
    sample.write_text("AWS_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE\n", encoding="utf-8")

    result = skill.zeynep_secret_scan(str(tmp_path))
    assert result["ok"] is True
    aws_findings = [f for f in result["findings"] if f["type"] == "aws_access_key"]
    assert aws_findings
    assert "AKIAIOSFODNN7EXAMPLE" not in aws_findings[0]["sample"]


def test_secret_scan_detects_stripe_and_openai_and_telegram(tmp_path, monkeypatch):
    skill = _patch_log(monkeypatch, tmp_path)
    sample = tmp_path / "secrets.py"
    stripe_token = "sk_" + "live_" + "abcdefghijklmnopqrstuvwxyzABCD"
    openai_token = "sk-" + "abcdefghijklmnopqrstuvwx"
    telegram_token = "123456789:" + "AAE-example-long-token-payload-string"
    sample.write_text(
        f"STRIPE = '{stripe_token}'\n"
        f"OPENAI = '{openai_token}'\n"
        f"TELEGRAM = '{telegram_token}'\n",
        encoding="utf-8",
    )

    result = skill.zeynep_secret_scan(str(tmp_path))
    types = {f["type"] for f in result["findings"]}
    assert "stripe_live" in types
    assert "openai_key" in types
    assert "telegram_bot" in types


def test_log_review_counts_anomalies(tmp_path, monkeypatch):
    skill = _patch_log(monkeypatch, tmp_path)
    log_file = tmp_path / "server.log"
    log_file.write_text(
        "2026-04-20 10:00 auth failed for user foo\n"
        "2026-04-20 10:01 permission denied on /admin\n"
        "2026-04-20 10:02 Traceback (most recent call last):\n"
        "2026-04-20 10:03 all good\n",
        encoding="utf-8",
    )

    result = skill.zeynep_log_review(str(tmp_path), since_hours=24 * 365)
    assert result["ok"] is True
    counts = result["anomaly_counts"]
    assert counts["auth_fail"] >= 1
    assert counts["permission_denied"] >= 1
    assert counts["exception"] >= 1


def test_hardening_check_scores(tmp_path, monkeypatch):
    skill = _patch_log(monkeypatch, tmp_path)
    (tmp_path / ".env").write_text("SECRET=abc", encoding="utf-8")
    (tmp_path / ".gitignore").write_text(".env\n", encoding="utf-8")
    (tmp_path / ".env.example").write_text("SECRET=", encoding="utf-8")
    (tmp_path / "README.md").write_text("# Proje", encoding="utf-8")

    result = skill.zeynep_hardening_check(str(tmp_path))
    assert result["ok"] is True
    check_ids = {c["id"]: c["ok"] for c in result["checks"]}
    assert check_ids["env_in_gitignore"] is True
    assert check_ids["env_example_present"] is True
    assert check_ids["readme_present"] is True
    assert result["score_pct"] >= 60.0
