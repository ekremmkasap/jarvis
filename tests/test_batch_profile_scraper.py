from __future__ import annotations

import asyncio
import json
import os
import sys
import types
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).parent.parent
SERVER_PATH = REPO_ROOT / "server"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(SERVER_PATH) not in sys.path:
    sys.path.insert(0, str(SERVER_PATH))

os.environ.setdefault("JARVIS_ENABLE_TELEGRAM", "0")
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "")
os.environ.setdefault("TELEGRAM_CHAT_ID", "0")

if "telegram" not in sys.modules:
    telegram_package = types.ModuleType("telegram")
    telegram_intelligence_module = types.ModuleType("telegram.telegram_intelligence")

    class _DummyTelegramIntelligence:
        def __init__(self, *args, **kwargs) -> None:
            pass

    telegram_intelligence_module.TelegramIntelligence = _DummyTelegramIntelligence
    telegram_package.telegram_intelligence = telegram_intelligence_module
    sys.modules["telegram"] = telegram_package
    sys.modules["telegram.telegram_intelligence"] = telegram_intelligence_module

import bridge as bridge_module
from server.skills import batch_profile_scraper as compat_batch_module
from server.skills import batch_profile_scraper_codex as batch_module
from server.skills import bridge_wiki_wrapper as wiki_bridge_module


def _install_batch_scrape_stub(monkeypatch, handler) -> None:
    module = types.ModuleType("batch_profile_scraper_codex")
    module.batch_scrape_handler = handler

    import server.skills as server_skills_package

    monkeypatch.setitem(sys.modules, "server.skills.batch_profile_scraper_codex", module)
    monkeypatch.setattr(
        server_skills_package,
        "batch_profile_scraper_codex",
        module,
        raising=False,
    )

    try:
        import skills as skills_package  # type: ignore
    except Exception:
        skills_package = None

    if skills_package is not None:
        monkeypatch.setitem(sys.modules, "skills.batch_profile_scraper_codex", module)
        monkeypatch.setattr(
            skills_package,
            "batch_profile_scraper_codex",
            module,
            raising=False,
        )

    monkeypatch.setitem(sys.modules, "batch_profile_scraper_codex", module)


def _install_batch_wiki_stub(monkeypatch, handler) -> None:
    module = types.ModuleType("bridge_wiki_wrapper")
    module.batch_scrape_to_wiki_result = handler

    import server.skills as server_skills_package

    monkeypatch.setitem(sys.modules, "server.skills.bridge_wiki_wrapper", module)
    monkeypatch.setattr(
        server_skills_package,
        "bridge_wiki_wrapper",
        module,
        raising=False,
    )

    try:
        import skills as skills_package  # type: ignore
    except Exception:
        skills_package = None

    if skills_package is not None:
        monkeypatch.setitem(sys.modules, "skills.bridge_wiki_wrapper", module)
        monkeypatch.setattr(
            skills_package,
            "bridge_wiki_wrapper",
            module,
            raising=False,
        )

    monkeypatch.setitem(sys.modules, "bridge_wiki_wrapper", module)


def test_bridge_batch_scrape_accepts_csv_path(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    async def _fake_handler(csv_path=None, handles=None):
        captured["csv_path"] = csv_path
        captured["handles"] = handles
        return {
            "status": "completed",
            "toplam": 4,
            "basarili": 3,
            "basarisiz": 1,
            "output_path": "outputs/batch_scrapes",
            "report_path": "outputs/batch_scrapes/ozet_rapor.json",
        }

    _install_batch_scrape_stub(monkeypatch, _fake_handler)

    csv_path = tmp_path / "handles.csv"
    csv_path.write_text("hesap\n@leadgenman\n", encoding="utf-8")

    result = bridge_module.handle_command(201, f'/batch-scrape "{csv_path}"')

    assert captured == {"csv_path": str(csv_path), "handles": None}
    assert "Toplu profil cekimi tamamlandi!" in result
    assert f"Girdi: CSV ({csv_path})" in result
    assert "Toplam: 4" in result
    assert "Basarili: 3" in result
    assert "Basarisiz: 1" in result
    assert "Ozet rapor: outputs/batch_scrapes/ozet_rapor.json" in result


def test_bridge_batch_scrape_wiki_output_accepts_flag_before_csv(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _fake_wiki_handler(csv_path=None):
        captured["csv_path"] = csv_path
        return {
            "status": "completed",
            "ok": True,
            "lead_count": 5,
            "output_path": "leads-wiki/wiki",
            "summary_path": "leads-wiki/wiki/hot.md",
        }

    _install_batch_wiki_stub(monkeypatch, _fake_wiki_handler)

    csv_path = tmp_path / "handles.csv"
    csv_path.write_text("username\nleadgenman\n", encoding="utf-8")

    result = bridge_module.handle_command(205, f'/batch-scrape --output wiki "{csv_path}"')

    assert captured == {"csv_path": str(csv_path)}
    assert "Leads wiki guncellendi!" in result
    assert f"Girdi: CSV ({csv_path})" in result
    assert "Lead sayisi: 5" in result
    assert "Haftalik ozet: leads-wiki/wiki/hot.md" in result
    assert "Kayit klasoru: leads-wiki/wiki" in result


def test_bridge_batch_scrape_wiki_output_accepts_flag_after_csv(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}

    def _fake_wiki_handler(csv_path=None):
        captured["csv_path"] = csv_path
        return (True, "OK Wiki updated: 2 leads in leads-wiki/wiki")

    _install_batch_wiki_stub(monkeypatch, _fake_wiki_handler)

    csv_path = tmp_path / "handles.csv"
    csv_path.write_text("username\nleadgenman\nalexlindai\n", encoding="utf-8")

    result = bridge_module.handle_command(206, f'/batch-scrape "{csv_path}" --output=wiki')

    assert captured == {"csv_path": str(csv_path)}
    assert "Leads wiki guncellendi!" in result
    assert f"Girdi: CSV ({csv_path})" in result
    assert "Detay: OK Wiki updated: 2 leads in leads-wiki/wiki" in result


def test_bridge_batch_scrape_wiki_output_requires_csv(monkeypatch) -> None:
    def _fake_wiki_handler(csv_path=None):
        raise AssertionError("wiki handler should not be loaded for inline accounts")

    _install_batch_wiki_stub(monkeypatch, _fake_wiki_handler)

    result = bridge_module.handle_command(207, "/batch-scrape --output wiki @leadgenman,@alexlindai")

    assert "Wiki output icin CSV path gerekli." in result
    assert "Kullanim: /batch-scrape" in result


def test_bridge_batch_scrape_accepts_comma_and_newline_list(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def _fake_handler(csv_path=None, handles=None):
        captured["csv_path"] = csv_path
        captured["handles"] = handles
        return {
            "status": "completed",
            "summary": {
                "total": 3,
                "successful": 3,
                "failed": 0,
            },
            "saved_files": ["a.json", "b.json", "c.json"],
            "output_dir": "outputs/batch_scrapes",
        }

    _install_batch_scrape_stub(monkeypatch, _fake_handler)

    result = bridge_module.handle_command(
        202,
        "/batch-scrape @leadgenman,\n@alexlindai, @ohmo.ai",
    )

    assert captured == {
        "csv_path": None,
        "handles": ["@leadgenman", "@alexlindai", "@ohmo.ai"],
    }
    assert "Girdi: 3 hesap" in result
    assert "Toplam: 3" in result
    assert "Basarili: 3" in result
    assert "Basarisiz: 0" in result
    assert "Kaydedilen dosya sayisi: 3" in result
    assert "Kayit klasoru: outputs/batch_scrapes" in result


def test_bridge_batch_scrape_wrapper_preserves_other_commands(monkeypatch) -> None:
    monkeypatch.setattr(
        bridge_module,
        "_ORIGINAL_BATCH_PROFILE_SCRAPE_HANDLE_COMMAND",
        lambda chat_id, cmd: f"fallback:{chat_id}:{cmd}",
    )

    result = bridge_module.handle_command(203, "/status_check Telegram bridge connection")

    assert result == "fallback:203:/status_check Telegram bridge connection"


class _FakeBatchScraper:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses

    async def scrape(self, target: str, platform: str | None = None):
        value = self.responses[target]
        if isinstance(value, Exception):
            raise value
        payload = dict(value)
        payload.setdefault("platform", platform or "instagram")
        return payload


def test_batch_profile_scraper_writes_reports(tmp_path: Path) -> None:
    fake_scraper = _FakeBatchScraper(
        {
            "@leadgenman": {
                "handle": "leadgenman",
                "followers_count": 22000,
                "avg_engagement_rate": 2.4,
                "has_affiliate_links": True,
            },
            "https://youtube.com/c/testchannel": {
                "channel_name": "Test Channel",
                "subscribers_count": 55000,
                "avg_engagement_rate": 3.8,
                "is_partner_program_eligible": True,
            },
        }
    )

    result = asyncio.run(
        batch_module.batch_scrape_handler(
            accounts=["@leadgenman", "https://youtube.com/c/testchannel"],
            scraper=fake_scraper,
            output_root=tmp_path,
            request_spacing_seconds=0,
        )
    )

    assert result["status"] == "completed"
    assert result["basarili"] == 2
    assert result["basarisiz"] == 0
    assert len(result["saved_files"]) == 2
    assert Path(result["report_path"]).exists()
    assert Path(result["analysis_path"]).exists()
    report = json.loads(Path(result["report_path"]).read_text(encoding="utf-8"))
    assert report["toplam_profil"] == 2
    assert report["platform_dagilimi"]["instagram"] == 1
    assert report["platform_dagilimi"]["youtube"] == 1


def test_batch_profile_scraper_collects_errors_after_retries(tmp_path: Path) -> None:
    fake_scraper = _FakeBatchScraper(
        {
            "@good": {
                "handle": "good",
                "followers_count": 1200,
                "avg_engagement_rate": 1.5,
            },
            "@bad": RuntimeError("network_down"),
        }
    )

    result = asyncio.run(
        batch_module.batch_scrape_handler(
            accounts=["@good", "@bad"],
            scraper=fake_scraper,
            output_root=tmp_path,
            max_retries=1,
            request_spacing_seconds=0,
        )
    )

    assert result["toplam"] == 2
    assert result["basarili"] == 1
    assert result["basarisiz"] == 1
    assert result["errors"][0]["target"] == "@bad"
    assert result["errors"][0]["attempts"] == 2


def test_batch_wiki_wrapper_runs_batch_scrape_for_handle_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "handles.csv"
    csv_path.write_text(
        "hesap,platform\n@leadgenman,instagram\nhttps://youtube.com/c/test,youtube\n",
        encoding="utf-8",
    )

    async def _fake_batch_runner(csv_path=None):
        assert csv_path is not None
        return {
            "status": "completed",
            "ok": True,
            "profiles": [
                {
                    "handle": "leadgenman",
                    "profile_url": "https://instagram.com/leadgenman",
                    "full_name": "Lead Gen Man",
                    "bio": "Growth systems and outbound playbooks",
                    "followers_count": 22000,
                    "platform": "instagram",
                },
                {
                    "channel_id": "UC123",
                    "channel_name": "AI Growth TV",
                    "channel_url": "https://youtube.com/c/test",
                    "description": "YouTube growth case studies",
                    "subscribers_count": 55000,
                    "platform": "youtube",
                },
            ],
            "output_path": str(tmp_path / "outputs" / "batch"),
            "report_path": str(tmp_path / "outputs" / "batch" / "ozet_rapor.json"),
        }

    wiki_root = tmp_path / "leads-wiki"
    result = wiki_bridge_module.batch_scrape_to_wiki_result(
        csv_path=csv_path,
        wiki_output_dir=wiki_root,
        batch_scrape_runner=_fake_batch_runner,
    )

    assert result["ok"] is True
    assert result["source_mode"] == "handles_csv"
    assert result["lead_count"] == 2
    assert Path(result["normalized_csv_path"]).exists()
    assert Path(result["summary_path"]).exists()
    assert (wiki_root / "wiki" / "lead_000001_leadgenman.md").exists()
    assert (wiki_root / "wiki" / "lead_000002_ai_growth_tv.md").exists()


def test_batch_wiki_wrapper_accepts_pre_enriched_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "lead_rows.csv"
    csv_path.write_text(
        (
            "number,username,full_name,biography,followers_count,external_url\n"
            "000001,leadgenman,Lead Gen Man,Outbound systems,22000,https://leadgen.example\n"
        ),
        encoding="utf-8",
    )

    wiki_root = tmp_path / "leads-wiki"
    result = wiki_bridge_module.batch_scrape_to_wiki_result(
        csv_path=csv_path,
        wiki_output_dir=wiki_root,
    )

    assert result["ok"] is True
    assert result["source_mode"] == "lead_csv"
    assert Path(result["summary_path"]).exists()
    assert (wiki_root / "wiki" / "lead_000001_leadgenman.md").exists()


def test_batch_profile_scraper_loads_csv_targets(tmp_path: Path) -> None:
    csv_path = tmp_path / "handles.csv"
    csv_path.write_text(
        "hesap,platform\n@leadgenman,instagram\nhttps://youtube.com/c/test,youtube\n",
        encoding="utf-8",
    )

    targets = batch_module.load_batch_targets_from_csv(csv_path)

    assert targets == [
        {"target": "@leadgenman", "platform": "instagram"},
        {"target": "https://youtube.com/c/test", "platform": "youtube"},
    ]


def test_bridge_batch_scrape_uses_real_skill_module(monkeypatch, tmp_path: Path) -> None:
    class _FakeRealBatchScraper:
        def __init__(self, max_concurrent=5, **kwargs) -> None:
            self.max_concurrent = max_concurrent

        async def batch_scrape_from_csv(self, csv_path):
            return {
                "status": "completed",
                "toplam": 2,
                "basarili": 2,
                "basarisiz": 0,
                "output_path": str(tmp_path / "outputs"),
                "report_path": str(tmp_path / "outputs" / "ozet_rapor.json"),
            }

    csv_path = tmp_path / "handles.csv"
    csv_path.write_text("hesap\n@leadgenman\n@alexlindai\n", encoding="utf-8")

    monkeypatch.setattr(batch_module, "BatchProfileScraper", _FakeRealBatchScraper)

    result = bridge_module.handle_command(204, f"/batch-scrape {csv_path}")

    assert "Toplu profil cekimi tamamlandi!" in result
    assert f"Girdi: CSV ({csv_path})" in result
    assert "Toplam: 2" in result
    assert "Basarili: 2" in result
    assert "Basarisiz: 0" in result


def test_run_batch_scrape_sync_rejects_active_event_loop() -> None:
    async def _run() -> None:
        with pytest.raises(RuntimeError, match="aktif event loop"):
            batch_module.run_batch_scrape_sync(accounts=["@leadgenman"])

    asyncio.run(_run())


def test_legacy_batch_profile_scraper_module_reexports_canonical_api() -> None:
    assert compat_batch_module.BatchProfileScraper is batch_module.BatchProfileScraper
    assert compat_batch_module.batch_scrape_handler is batch_module.batch_scrape_handler
    assert (
        compat_batch_module.load_batch_targets_from_csv
        is batch_module.load_batch_targets_from_csv
    )
