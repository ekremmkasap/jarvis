from __future__ import annotations

import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))

import skills.notion_skill as notion_skill


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        return self._payload


class NotionSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_env = os.environ.copy()

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.original_env)
        importlib.reload(notion_skill)

    def _reload_with_credentials(self):
        os.environ["NOTION_API_KEY"] = "secret_test"
        os.environ["NOTION_DATABASE_ID"] = "db_test"
        return importlib.reload(notion_skill)

    def test_no_credentials(self) -> None:
        os.environ.pop("NOTION_API_KEY", None)
        os.environ.pop("NOTION_DATABASE_ID", None)
        module = importlib.reload(notion_skill)

        result = module.handle_notion("liste")

        self.assertIn("Notion henuz bagli degil", result)
        self.assertIn("NOTION_API_KEY", result)

    def test_liste_command(self) -> None:
        module = self._reload_with_credentials()
        fake_requests = MagicMock()
        fake_requests.post.return_value = _FakeResponse(
            200,
            {
                "results": [
                    {
                        "properties": {
                            "Name": {
                                "type": "title",
                                "title": [{"plain_text": "Haftalik Not"}],
                            }
                        },
                        "url": "https://notion.so/weekly-note",
                    }
                ]
            },
        )

        with patch.object(module, "_requests", fake_requests):
            result = module.handle_notion("liste")

        self.assertIn("Haftalik Not", result)
        self.assertIn("https://notion.so/weekly-note", result)
        self.assertIn("/databases/db_test/query", fake_requests.post.call_args.args[0])

    def test_ara_command(self) -> None:
        module = self._reload_with_credentials()
        fake_requests = MagicMock()
        fake_requests.post.return_value = _FakeResponse(
            200,
            {
                "results": [
                    {
                        "properties": {
                            "Name": {
                                "type": "title",
                                "title": [{"plain_text": "Arama Sonucu"}],
                            }
                        },
                        "url": "https://notion.so/search-result",
                    }
                ]
            },
        )

        with patch.object(module, "_requests", fake_requests):
            result = module.handle_notion("ara roadmap")

        self.assertIn("Arama Sonuclari", result)
        self.assertIn("Arama Sonucu", result)
        self.assertIn("/search", fake_requests.post.call_args.args[0])

    def test_ekle_command(self) -> None:
        module = self._reload_with_credentials()
        fake_requests = MagicMock()
        fake_requests.post.return_value = _FakeResponse(
            200,
            {"url": "https://notion.so/new-page"},
        )

        with patch.object(module, "_requests", fake_requests):
            result = module.handle_notion("ekle Sprint Plani | Yapilacaklar")

        self.assertIn("Sayfa olusturuldu", result)
        self.assertIn("Sprint Plani", result)
        payload = fake_requests.post.call_args.kwargs["json"]
        self.assertEqual(payload["parent"]["database_id"], "db_test")
        self.assertEqual(
            payload["properties"]["title"]["title"][0]["text"]["content"],
            "Sprint Plani",
        )

    def test_invalid_command(self) -> None:
        module = self._reload_with_credentials()
        result = module.handle_notion("sil sayfa")
        self.assertIn("Komutlar", result)


if __name__ == "__main__":
    unittest.main()
