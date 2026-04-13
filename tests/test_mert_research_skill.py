from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent.parent))

from server.skills import mert_research_skill


def _mock_payload() -> dict:
    return {
        "Heading": "OpenAI",
        "AbstractText": "OpenAI yapay zeka sistemleri gelistirir.",
        "AbstractURL": "https://openai.com/",
        "Answer": "OpenAI 2015 yilinda kuruldu.",
        "AnswerType": "kurulus",
        "RelatedTopics": [
            {
                "Text": "Anthropic - Rakip model saglayicisi ve guvenlik odakli arastirma sirketi.",
                "FirstURL": "https://www.anthropic.com/",
            },
            {
                "Name": "Nested",
                "Topics": [
                    {
                        "Text": "Perplexity - Arama destekli cevap motoru.",
                        "FirstURL": "https://www.perplexity.ai/",
                    }
                ],
            },
        ],
    }


def test_search_and_summarize_empty_query_returns_error(tmp_path, monkeypatch):
    monkeypatch.setattr(mert_research_skill, "LOG_PATH", tmp_path / "mert_research.jsonl")

    result = mert_research_skill.search_and_summarize("   ")

    assert result["ok"] is False
    assert result["error"] == "query_required"
    assert result["saved_to"] is None


def test_web_search_deep_scores_results_without_network(tmp_path, monkeypatch):
    monkeypatch.setattr(mert_research_skill, "LOG_PATH", tmp_path / "mert_research.jsonl")
    monkeypatch.setattr(mert_research_skill, "_fetch_duckduckgo_payload", lambda query: _mock_payload())
    monkeypatch.setattr(mert_research_skill, "_sleep", lambda seconds: None)
    monkeypatch.setattr(mert_research_skill, "_LAST_SEARCH_AT", 0.0)

    results = mert_research_skill.web_search_deep("openai", max_results=5)

    assert len(results) == 4
    assert results[0]["title"] == "OpenAI"
    assert results[0]["relevance_score"] > results[-1]["relevance_score"]
    assert (tmp_path / "mert_research.jsonl").exists()


def test_search_and_summarize_gracefully_handles_missing_obsidian_vault(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(mert_research_skill, "LOG_PATH", tmp_path / "mert_research.jsonl")
    monkeypatch.setattr(mert_research_skill, "_fetch_duckduckgo_payload", lambda query: _mock_payload())
    monkeypatch.setattr(mert_research_skill, "_sleep", lambda seconds: None)
    monkeypatch.setattr(mert_research_skill, "_LAST_SEARCH_AT", 0.0)
    monkeypatch.setattr(mert_research_skill, "get_obsidian_vault_dir", lambda: None)

    result = mert_research_skill.search_and_summarize("OpenAI agents")

    assert result["ok"] is True
    assert result["saved_to"] is None
    assert "Arastirma ozeti" in result["summary"]
    assert len(result["sources"]) >= 1


def test_competitor_analysis_runs_three_searches(monkeypatch):
    seen_queries: list[str] = []

    def _fake_search(query: str, max_results: int = 5):
        seen_queries.append(query)
        return [
            {
                "title": query,
                "snippet": "Ornek ozet",
                "url": f"https://example.com/{mert_research_skill._slugify(query)}",
                "relevance_score": 50,
            }
        ]

    monkeypatch.setattr(mert_research_skill, "web_search_deep", _fake_search)

    result = mert_research_skill.competitor_analysis("Notion")

    assert result["ok"] is True
    assert seen_queries == [
        "Notion reviews",
        "Notion alternatives",
        "Notion pricing",
    ]
    assert "Rakip analizi: Notion" in result["report"]


def test_bridge_contains_mert_commands():
    bridge_path = Path(__file__).parent.parent / "server" / "bridge.py"
    content = bridge_path.read_text(encoding="utf-8")

    assert 'elif command == "/mert-ara":' in content
    assert 'elif command == "/mert-rakip":' in content
