from __future__ import annotations


def test_analyze_csv_invalid_file_returns_error(tmp_path, monkeypatch):
    from server.skills import eren_data_skill as skill

    monkeypatch.setattr(skill, "LOG_PATH", tmp_path / "eren_analysis.jsonl")
    result = skill.analyze_csv(str(tmp_path / "missing.csv"))

    assert result["ok"] is False
    assert result["error"] == "file_not_found"


def test_analyze_csv_valid_file_returns_stats(tmp_path, monkeypatch):
    from server.skills import eren_data_skill as skill

    csv_path = tmp_path / "sample.csv"
    csv_path.write_text(
        "gelir,musteri,kanal\n100,2,instagram\n200,3,linkedin\n,4,instagram\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(skill, "LOG_PATH", tmp_path / "eren_analysis.jsonl")

    result = skill.analyze_csv(str(csv_path))

    assert result["ok"] is True
    assert result["rows"] == 3
    assert result["columns"] == ["gelir", "musteri", "kanal"]
    assert result["stats"]["gelir"]["type"] == "numeric"
    assert result["stats"]["gelir"]["avg"] == 150.0
    assert result["stats"]["kanal"]["unique_count"] == 2


def test_kpi_summary_invalid_json_is_graceful(tmp_path, monkeypatch):
    from server.skills import eren_data_skill as skill

    monkeypatch.setattr(skill, "LOG_PATH", tmp_path / "eren_analysis.jsonl")
    result = skill.kpi_summary('{"gelir":15000')

    assert result["ok"] is False
    assert result["error"] == "invalid_json"


def test_kpi_summary_uses_thresholds(tmp_path, monkeypatch):
    from server.skills import eren_data_skill as skill

    monkeypatch.setattr(skill, "LOG_PATH", tmp_path / "eren_analysis.jsonl")
    result = skill.kpi_summary({"gelir": 15000, "musteri": 23, "churn": 0.05})

    assert result["ok"] is True
    assert "Gelir" in result["summary"]
    assert "hedefin ustunde" in result["summary"]


def test_quick_report_graceful_when_vault_missing(tmp_path, monkeypatch):
    from server.skills import eren_data_skill as skill

    csv_path = tmp_path / "sample.csv"
    csv_path.write_text("gelir,musteri\n100,2\n", encoding="utf-8")
    monkeypatch.setattr(skill, "LOG_PATH", tmp_path / "eren_analysis.jsonl")

    result = skill.quick_report(str(csv_path), vault_dir=tmp_path / "missing-vault")

    assert result["ok"] is False
    assert "Obsidian" in result["message"]
