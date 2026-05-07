from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


ROOT = Path(__file__).resolve().parents[1]
SERVER_DIR = ROOT / "server"
SKILLS_DIR = SERVER_DIR / "skills"

for candidate in (SERVER_DIR, SKILLS_DIR):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)


class EbayResearchTests(unittest.TestCase):
    def test_fetch_ebay_sold_prices_success(self) -> None:
        from ebay_research import fetch_ebay_sold_prices

        mock_html = b"""
        <html><body>
        <span class="s-item__price">$12.99</span>
        <span class="s-item__price">$15.00</span>
        <span class="s-item__price">$10.50</span>
        </body></html>
        """
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_html
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("ebay_research.urlopen", return_value=mock_resp):
            result = fetch_ebay_sold_prices("test product")

        self.assertNotIn("error", result)
        self.assertEqual(result["count"], 3)
        self.assertEqual(result["min_price"], 10.5)
        self.assertEqual(result["max_price"], 15.0)

    def test_fetch_ebay_sold_prices_network_error(self) -> None:
        from ebay_research import fetch_ebay_sold_prices

        with patch("ebay_research.urlopen", side_effect=Exception("timeout")):
            result = fetch_ebay_sold_prices("test")

        self.assertIn("error", result)

    def test_format_report_with_price_data(self) -> None:
        from ebay_research import format_report

        result = {
            "query": "led strip",
            "price_data": {
                "min_price": 5.0,
                "max_price": 20.0,
                "avg_price": 12.5,
                "count": 10,
                "prices": [],
            },
            "market_analysis": "Guclu pazar",
            "listing_titles": "1. LED Strip Lights",
            "suppliers": "AliExpress",
        }
        report = format_report(result)
        self.assertIn("led strip", report.lower())
        self.assertIn("$5.0", report)
        self.assertIn("Guclu pazar", report)


class OpportunitySkillTests(unittest.TestCase):
    def test_build_opportunity_report_empty(self) -> None:
        from ecommerce_opportunity_skill import build_opportunity_report

        report = build_opportunity_report([])
        self.assertTrue("veri cekemedim" in report.lower() or "bugun" in report.lower())

    def test_build_opportunity_report_with_data(self) -> None:
        from ecommerce_opportunity_skill import build_opportunity_report

        opportunities = [
            {
                "platform": "trendyol",
                "query": "kulaklık",
                "min_price_try": 100,
                "max_price_try": 500,
                "avg_price_try": 300,
                "count": 50,
                "best_product": "Sony WH",
            },
            {
                "platform": "ebay",
                "query": "headphones",
                "min_price_usd": 5,
                "max_price_usd": 30,
                "avg_price_usd": 15,
                "sold_count": 20,
            },
        ]
        report = build_opportunity_report(opportunities)
        self.assertIn("Trendyol", report)
        self.assertIn("eBay", report)
        self.assertIn("kulaklık", report)
        self.assertIn("headphones", report)

    def test_get_scheduler_status_not_started(self) -> None:
        import ecommerce_opportunity_skill

        ecommerce_opportunity_skill._scheduler = None
        status = ecommerce_opportunity_skill.get_scheduler_status()
        self.assertFalse(status["running"])
        self.assertEqual(status["jobs"], [])
        self.assertIsNone(status["next_run"])

    def test_save_and_load_last_scan(self) -> None:
        import tempfile
        import ecommerce_opportunity_skill

        with tempfile.TemporaryDirectory() as tmpdir:
            original_path = ecommerce_opportunity_skill.OPPORTUNITY_HISTORY_PATH
            ecommerce_opportunity_skill.OPPORTUNITY_HISTORY_PATH = (
                Path(tmpdir) / "opp.json"
            )
            try:
                opps = [{"platform": "trendyol", "query": "test"}]
                ecommerce_opportunity_skill.save_scan_result(opps)
                last = ecommerce_opportunity_skill.load_last_scan()
                self.assertIsNotNone(last)
                self.assertEqual(last["opportunities"], opps)
            finally:
                ecommerce_opportunity_skill.OPPORTUNITY_HISTORY_PATH = original_path

    def test_run_opportunity_scan_calls_send_fn(self) -> None:
        from ecommerce_opportunity_skill import run_opportunity_scan

        sent: list[str] = []
        with (
            patch("ecommerce_opportunity_skill.scan_opportunities", return_value=[]),
            patch("ecommerce_opportunity_skill.save_scan_result"),
        ):
            result = run_opportunity_scan(lambda msg: sent.append(msg))

        self.assertEqual(result["send_status"], "sent")
        self.assertEqual(len(sent), 1)

    def test_start_scheduler_returns_false_when_apscheduler_is_missing(self) -> None:
        import ecommerce_opportunity_skill

        ecommerce_opportunity_skill._scheduler = None
        with patch.dict(sys.modules, {"apscheduler": None}):
            result = ecommerce_opportunity_skill.start_opportunity_scheduler(
                lambda _: None
            )

        self.assertFalse(result)


if __name__ == "__main__":
    unittest.main()
