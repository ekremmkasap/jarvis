from __future__ import annotations

import base64
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))

import skills.gcalendar_skill as gcalendar_skill
import skills.gmail_skill as gmail_skill


class _FakeRequest:
    def __init__(self, payload):
        self.payload = payload

    def execute(self):
        return self.payload


class _FakeGmailMessages:
    def __init__(self, details):
        self.details = details
        self.index = 0
        self.sent_bodies = []

    def list(self, **kwargs):
        return _FakeRequest({"messages": [{"id": "1"}, {"id": "2"}]})

    def get(self, **kwargs):
        payload = self.details[self.index]
        self.index += 1
        return _FakeRequest(payload)

    def send(self, **kwargs):
        self.sent_bodies.append(kwargs.get("body", {}))
        return _FakeRequest({"id": "sent_1"})


class _FakeGmailUsers:
    def __init__(self, details):
        self._messages = _FakeGmailMessages(details)

    def messages(self):
        return self._messages


class _FakeGmailService:
    def __init__(self, details):
        self._users = _FakeGmailUsers(details)

    def users(self):
        return self._users


class _FakeCalendarEvents:
    def __init__(self, list_payload=None, insert_payload=None):
        self.list_payload = list_payload or {"items": []}
        self.insert_payload = insert_payload or {}

    def list(self, **kwargs):
        return _FakeRequest(self.list_payload)

    def insert(self, **kwargs):
        return _FakeRequest(self.insert_payload)


class _FakeCalendarService:
    def __init__(self, list_payload=None, insert_payload=None):
        self._events = _FakeCalendarEvents(list_payload=list_payload, insert_payload=insert_payload)

    def events(self):
        return self._events


class GmailSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_missing_credentials_message_is_returned(self) -> None:
        with patch.object(
            gmail_skill,
            "_credentials_path",
            return_value=self.temp_dir / "missing-google-credentials.json",
        ):
            result = gmail_skill.handle_gmail("liste")
        self.assertIn("Google Gmail entegrasyonu icin kurulum gerekli", result)

    def test_recent_mail_is_formatted(self) -> None:
        service = _FakeGmailService(
            [
                {
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "Alice <alice@example.com>"},
                            {"name": "Subject", "value": "Roadmap"},
                        ]
                    },
                    "snippet": "Sprint plani hazir",
                },
                {
                    "payload": {
                        "headers": [
                            {"name": "From", "value": "Bob <bob@example.com>"},
                            {"name": "Subject", "value": "Launch"},
                        ]
                    },
                    "snippet": "Yayin hazirligi tamam",
                },
            ]
        )

        with patch.object(gmail_skill, "_get_gmail_service", return_value=(service, "")):
            result = gmail_skill.handle_gmail("liste")

        self.assertIn("*Gmail - Son 5 E-posta*", result)
        self.assertIn("Alice <alice@example.com>", result)
        self.assertIn("Roadmap", result)
        self.assertIn("Launch", result)

    def test_send_mail_uses_pipe_format(self) -> None:
        service = _FakeGmailService([])

        with patch.object(gmail_skill, "_get_gmail_service", return_value=(service, "")):
            result = gmail_skill.handle_gmail(
                "gonder demo@example.com | Sprint Ozeti | Merhaba ekip"
            )

        self.assertIn("E-posta gonderildi", result)
        raw_payload = service.users().messages().sent_bodies[0]["raw"]
        decoded = base64.urlsafe_b64decode(raw_payload.encode("utf-8")).decode("utf-8")
        self.assertIn("To: demo@example.com", decoded)
        self.assertIn("Subject: Sprint Ozeti", decoded)
        self.assertIn("Merhaba ekip", decoded)


class CalendarSkillTests(unittest.TestCase):
    def test_build_create_payload_supports_relative_date(self) -> None:
        body, error = gcalendar_skill._build_create_payload(
            "baslik:Urun Toplantisi tarih:yarin saat:14:30 yer:Ofis"
        )

        self.assertEqual(error, "")
        self.assertIsNotNone(body)
        assert body is not None
        self.assertEqual(body["summary"], "Urun Toplantisi")
        self.assertEqual(body["location"], "Ofis")
        self.assertIn("dateTime", body["start"])

    def test_calendar_lists_events(self) -> None:
        service = _FakeCalendarService(
            list_payload={
                "items": [
                    {
                        "summary": "Standup",
                        "location": "Zoom",
                        "start": {"dateTime": "2026-04-06T09:30:00+03:00"},
                    }
                ]
            }
        )

        with patch.object(gcalendar_skill, "_get_calendar_service", return_value=(service, "")):
            result = gcalendar_skill.handle_gcalendar("liste")

        self.assertIn("*Google Takvim - Bugunun Etkinlikleri*", result)
        self.assertIn("Standup", result)
        self.assertIn("Zoom", result)

    def test_calendar_creates_events(self) -> None:
        service = _FakeCalendarService(
            insert_payload={
                "summary": "Demo",
                "location": "Ofis",
                "start": {"dateTime": "2026-04-06T14:30:00+03:00"},
            }
        )

        with patch.object(gcalendar_skill, "_get_calendar_service", return_value=(service, "")):
            result = gcalendar_skill.handle_gcalendar(
                "ekle baslik:Demo tarih:2026-04-06 saat:14:30 yer:Ofis"
            )

        self.assertIn("Yeni etkinlik olusturuldu.", result)
        self.assertIn("Demo", result)
        self.assertIn("Ofis", result)


if __name__ == "__main__":
    unittest.main()
