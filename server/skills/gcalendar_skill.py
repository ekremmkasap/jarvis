#!/usr/bin/env python3
"""
Jarvis Google Calendar skill.
Komutlar:
- /takvim liste
- /takvim ekle baslik:Toplanti tarih:2026-04-06 saat:14:30 yer:Ofis
"""

from __future__ import annotations

import json
import os
import re
from datetime import datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CREDENTIALS_PATH = BASE_DIR / "config" / "google_credentials.json"
DEFAULT_TOKEN_PATH = BASE_DIR / "data" / "google_token.json"
CALENDAR_TIMEZONE = "Europe/Istanbul"
SCOPES = ["https://www.googleapis.com/auth/calendar"]
ALL_SUPPORTED_SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
]

FIELD_KEYWORDS = {
    "title": ["baslik", "baslik", "title", "etkinlik", "konu"],
    "date": ["tarih", "date", "gun", "gun"],
    "time": ["saat", "time"],
    "location": ["yer", "konum", "location"],
}


def _escape_markdown(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "").strip())
    if not value:
        return "-"
    for char in ("\\", "_", "*", "`", "[", "]", "(", ")"):
        value = value.replace(char, f"\\{char}")
    return value


def _credentials_path() -> Path:
    raw_path = os.environ.get("GOOGLE_CREDENTIALS_PATH", "").strip()
    return Path(raw_path) if raw_path else DEFAULT_CREDENTIALS_PATH


def _token_path() -> Path:
    raw_path = os.environ.get("GOOGLE_TOKEN_PATH", "").strip()
    return Path(raw_path) if raw_path else DEFAULT_TOKEN_PATH


def _missing_credentials_message() -> str:
    credentials_path = _credentials_path()
    return (
        "Google Takvim entegrasyonu icin kurulum gerekli.\n"
        "1. Google Cloud Console uzerinde Google Calendar API'yi etkinlestirin.\n"
        "2. OAuth istemci kimligini `Desktop app` olarak olusturun.\n"
        "3. Indirdiginiz JSON dosyasini su konuma koyun:\n"
        f"`{credentials_path}`\n"
        "4. Gerekirse `GOOGLE_CREDENTIALS_PATH` env degerini ayarlayin.\n"
        "5. Ardindan `/takvim liste` veya `/takvim ekle ...` komutunu tekrar calistirin."
    )


def _missing_libraries_message() -> str:
    return (
        "Google kutuphaneleri yuklu degil.\n"
        "Lutfen `google-api-python-client`, `google-auth-oauthlib` ve "
        "`google-auth-httplib2` paketlerini kurup tekrar deneyin."
    )


def _read_existing_scopes() -> list[str]:
    token_path = _token_path()
    if not token_path.exists():
        return []
    try:
        token_data = json.loads(token_path.read_text(encoding="utf-8"))
    except Exception:
        return []
    raw_scopes = token_data.get("scopes") or token_data.get("scope") or []
    if isinstance(raw_scopes, str):
        raw_scopes = [scope for scope in raw_scopes.split() if scope]
    if not isinstance(raw_scopes, list):
        return []
    return [scope for scope in raw_scopes if isinstance(scope, str) and scope in ALL_SUPPORTED_SCOPES]


def _resolve_requested_scopes() -> list[str]:
    scopes = set(_read_existing_scopes())
    scopes.update(SCOPES)
    return [scope for scope in ALL_SUPPORTED_SCOPES if scope in scopes]


def _get_calendar_service():
    credentials_path = _credentials_path()
    token_path = _token_path()

    if not credentials_path.exists():
        return None, _missing_credentials_message()

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        return None, _missing_libraries_message()

    requested_scopes = _resolve_requested_scopes()
    creds = None

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), requested_scopes)
        except Exception:
            creds = None

    try:
        if creds and creds.expired and creds.refresh_token and creds.has_scopes(SCOPES):
            creds.refresh(Request())
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json(), encoding="utf-8")

        if not creds or not creds.valid or not creds.has_scopes(SCOPES):
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), requested_scopes)
            creds = flow.run_local_server(
                host="127.0.0.1",
                port=0,
                open_browser=True,
                authorization_prompt_message="Jarvis icin Google Takvim yetkilendirme penceresi aciliyor.",
                success_message="Jarvis Takvim yetkilendirmesi tamamlandi. Bu pencereyi kapatabilirsiniz.",
            )
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json(), encoding="utf-8")
    except Exception as exc:
        return None, f"Google Takvim yetkilendirmesi basarisiz oldu: {exc}"

    try:
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        return service, ""
    except Exception as exc:
        return None, f"Google Takvim servisi baslatilamadi: {exc}"


def _field_alias_pattern(field_name: str) -> str:
    return "|".join(re.escape(alias) for alias in FIELD_KEYWORDS[field_name])


def _all_alias_pattern() -> str:
    aliases = []
    for values in FIELD_KEYWORDS.values():
        aliases.extend(values)
    return "|".join(re.escape(alias) for alias in aliases)


def _extract_field(text: str, field_name: str) -> str:
    pattern = (
        rf"(?:^|\s)(?:{_field_alias_pattern(field_name)})\s*[:=]\s*(.+?)"
        rf"(?=(?:\s+(?:{_all_alias_pattern()})\s*[:=])|$)"
    )
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1).strip(" ,") if match else ""


def _looks_like_create_request(text: str) -> bool:
    lowered = text.lower()
    has_title_keyword = any(f"{keyword}:" in lowered or f"{keyword}=" in lowered for keyword in FIELD_KEYWORDS["title"])
    has_date_or_time_keyword = any(
        f"{keyword}:" in lowered or f"{keyword}=" in lowered
        for keyword in FIELD_KEYWORDS["date"] + FIELD_KEYWORDS["time"]
    )
    return has_title_keyword and has_date_or_time_keyword


def _parse_event_date(raw_value: str, tz: ZoneInfo) -> datetime.date:
    now = datetime.now(tz)
    value = (raw_value or "").strip().lower()
    if not value or value in {"bugun", "today"}:
        return now.date()
    if value in {"yarin", "tomorrow"}:
        return (now + timedelta(days=1)).date()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(raw_value.strip(), fmt).date()
        except ValueError:
            continue
    raise ValueError("Tarih anlasilmadi. Ornek: tarih:2026-04-06 veya tarih:06.04.2026")


def _parse_event_time(raw_value: str) -> time | None:
    value = (raw_value or "").strip()
    if not value:
        return None
    for fmt in ("%H:%M", "%H.%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    raise ValueError("Saat anlasilmadi. Ornek: saat:14:30")


def _build_create_payload(args: str) -> tuple[dict | None, str]:
    if not _looks_like_create_request(args):
        return None, ""

    title = _extract_field(args, "title")
    date_value = _extract_field(args, "date")
    time_value = _extract_field(args, "time")
    location = _extract_field(args, "location")

    if not title:
        return None, (
            "Etkinlik olusturmak icin su formati kullanin:\n"
            "`/takvim ekle baslik:Urun toplantisi tarih:2026-04-06 saat:14:30 yer:Ofis`"
        )

    tz = ZoneInfo(CALENDAR_TIMEZONE)

    try:
        event_date = _parse_event_date(date_value, tz)
        event_time = _parse_event_time(time_value)
    except ValueError as exc:
        return None, str(exc)

    body = {"summary": title}
    if location:
        body["location"] = location

    if event_time is None:
        body["start"] = {"date": event_date.isoformat()}
        body["end"] = {"date": (event_date + timedelta(days=1)).isoformat()}
    else:
        start_dt = datetime.combine(event_date, event_time, tzinfo=tz)
        end_dt = start_dt + timedelta(hours=1)
        body["start"] = {"dateTime": start_dt.isoformat(), "timeZone": CALENDAR_TIMEZONE}
        body["end"] = {"dateTime": end_dt.isoformat(), "timeZone": CALENDAR_TIMEZONE}

    return body, ""


def _format_event_time(event: dict) -> str:
    start = event.get("start", {})
    if start.get("dateTime"):
        date_time_value = str(start["dateTime"]).replace("Z", "+00:00")
        dt = datetime.fromisoformat(date_time_value)
        if dt.tzinfo is not None:
            dt = dt.astimezone(ZoneInfo(CALENDAR_TIMEZONE))
        return dt.strftime("%H:%M")
    return "Tum gun"


def _list_today_events(service) -> str:
    tz = ZoneInfo(CALENDAR_TIMEZONE)
    now = datetime.now(tz)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    try:
        response = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=day_start.isoformat(),
                timeMax=day_end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except Exception as exc:
        return f"Takvim etkinlikleri okunamadi: {exc}"

    events = response.get("items", [])
    if not events:
        return "*Google Takvim*\n\nBugun icin etkinlik bulunamadi."

    lines = ["*Google Takvim - Bugunun Etkinlikleri*", ""]
    for index, event in enumerate(events, start=1):
        title = event.get("summary") or "Basliksiz etkinlik"
        location = event.get("location")
        lines.append(f"{index}. {_escape_markdown(title)}")
        lines.append(f"   Saat: {_escape_markdown(_format_event_time(event))}")
        if location:
            lines.append(f"   Konum: {_escape_markdown(location)}")
        lines.append("")

    return "\n".join(lines).strip()


def _create_event(service, body: dict) -> str:
    try:
        created = service.events().insert(calendarId="primary", body=body).execute()
    except Exception as exc:
        return f"Takvim etkinligi olusturulamadi: {exc}"

    summary = created.get("summary") or body.get("summary") or "Basliksiz etkinlik"
    location = created.get("location") or body.get("location")

    if created.get("start", {}).get("dateTime"):
        start_text = _format_event_time(created)
        date_text = datetime.fromisoformat(
            str(created["start"]["dateTime"]).replace("Z", "+00:00")
        ).astimezone(ZoneInfo(CALENDAR_TIMEZONE)).strftime("%d.%m.%Y")
        when_text = f"{date_text} {start_text}"
    else:
        when_text = datetime.fromisoformat(created["start"]["date"]).strftime("%d.%m.%Y") + " Tum gun"

    lines = [
        "*Google Takvim*",
        "",
        "Yeni etkinlik olusturuldu.",
        f"Baslik: {_escape_markdown(summary)}",
        f"Zaman: {_escape_markdown(when_text)}",
    ]
    if location:
        lines.append(f"Konum: {_escape_markdown(location)}")
    return "\n".join(lines)


def handle_gcalendar(args: str = "", user_id: str = "") -> str:
    service, error_message = _get_calendar_service()
    if error_message:
        return error_message

    args = (args or "").strip()
    lowered = args.lower()

    if lowered in {"", "liste", "bugun", "today"}:
        return _list_today_events(service)

    if lowered.startswith("ekle "):
        body, parse_error = _build_create_payload(args.split(" ", 1)[1].strip())
        if parse_error:
            return parse_error
        if body is not None:
            return _create_event(service, body)
        return "Kullanim: `/takvim ekle baslik:Toplanti tarih:2026-04-06 saat:14:30 yer:Ofis`"

    if args:
        body, parse_error = _build_create_payload(args)
        if parse_error:
            return parse_error
        if body is not None:
            return _create_event(service, body)

    return (
        "Takvim komutlari:\n"
        "- `/takvim liste`\n"
        "- `/takvim ekle baslik:Toplanti tarih:2026-04-06 saat:14:30 yer:Ofis`"
    )
