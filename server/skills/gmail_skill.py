#!/usr/bin/env python3
"""
Jarvis Gmail skill.
Komutlar:
- /mail liste
- /mail gonder alici@example.com | Konu | Icerik
"""

from __future__ import annotations

import base64
import json
import os
import re
from email.message import EmailMessage
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CREDENTIALS_PATH = BASE_DIR / "config" / "google_credentials.json"
DEFAULT_TOKEN_PATH = BASE_DIR / "data" / "google_token.json"
GMAIL_READ_SCOPE = "https://www.googleapis.com/auth/gmail.readonly"
GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"
CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
ALL_SUPPORTED_SCOPES = [
    GMAIL_READ_SCOPE,
    GMAIL_SEND_SCOPE,
    CALENDAR_SCOPE,
]


def _escape_markdown(text: str) -> str:
    value = re.sub(r"\s+", " ", str(text or "").strip())
    if not value:
        return "-"
    for char in ("\\", "_", "*", "`", "[", "]", "(", ")"):
        value = value.replace(char, f"\\{char}")
    return value


def _credentials_path() -> Path:
    raw_path = (
        os.environ.get("GMAIL_CREDENTIALS_PATH", "").strip()
        or os.environ.get("GOOGLE_CREDENTIALS_PATH", "").strip()
    )
    return Path(raw_path) if raw_path else DEFAULT_CREDENTIALS_PATH


def _token_path() -> Path:
    raw_path = (
        os.environ.get("GMAIL_TOKEN_PATH", "").strip()
        or os.environ.get("GOOGLE_TOKEN_PATH", "").strip()
    )
    return Path(raw_path) if raw_path else DEFAULT_TOKEN_PATH


def _missing_credentials_message(credentials_path: Path) -> str:
    return (
        "Google Gmail entegrasyonu icin kurulum gerekli.\n"
        "1. Google Cloud Console uzerinde Gmail API'yi etkinlestirin.\n"
        "2. OAuth istemci kimligini `Desktop app` olarak olusturun.\n"
        "3. JSON credentials dosyasini su konuma koyun:\n"
        f"`{credentials_path}`\n"
        "4. Gerekirse `GMAIL_CREDENTIALS_PATH` veya `GOOGLE_CREDENTIALS_PATH` env degerini ayarlayin.\n"
        "5. Ardindan `/mail liste` veya `/mail gonder ...` komutunu tekrar calistirin."
    )


def _missing_libraries_message() -> str:
    return (
        "Google kutuphaneleri yuklu degil.\n"
        "Lutfen `google-api-python-client`, `google-auth-oauthlib` ve "
        "`google-auth-httplib2` paketlerini kurup tekrar deneyin."
    )


def _read_existing_scopes(token_path: Path) -> list[str]:
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


def _resolve_requested_scopes(required_scopes: list[str], token_path: Path) -> list[str]:
    scopes = set(_read_existing_scopes(token_path))
    scopes.update(required_scopes)
    return [scope for scope in ALL_SUPPORTED_SCOPES if scope in scopes]


def _get_gmail_service(required_scopes: list[str]):
    credentials_path = _credentials_path()
    token_path = _token_path()

    if not credentials_path.exists():
        return None, _missing_credentials_message(credentials_path)

    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
    except ImportError:
        return None, _missing_libraries_message()

    requested_scopes = _resolve_requested_scopes(required_scopes, token_path)
    creds = None

    if token_path.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(token_path), requested_scopes)
        except Exception:
            creds = None

    try:
        has_required_scopes = bool(creds and creds.has_scopes(required_scopes))
        if creds and creds.expired and creds.refresh_token and has_required_scopes:
            creds.refresh(Request())
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json(), encoding="utf-8")

        if not creds or not creds.valid or not has_required_scopes:
            flow = InstalledAppFlow.from_client_secrets_file(str(credentials_path), requested_scopes)
            creds = flow.run_local_server(
                host="127.0.0.1",
                port=0,
                open_browser=True,
                authorization_prompt_message="Jarvis icin Gmail yetkilendirme penceresi aciliyor.",
                success_message="Jarvis Gmail yetkilendirmesi tamamlandi. Bu pencereyi kapatabilirsiniz.",
            )
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(creds.to_json(), encoding="utf-8")
    except Exception as exc:
        return None, f"Google Gmail yetkilendirmesi basarisiz oldu: {exc}"

    try:
        service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return service, ""
    except Exception as exc:
        return None, f"Gmail servisi baslatilamadi: {exc}"


def _extract_header(message: dict, header_name: str) -> str:
    headers = message.get("payload", {}).get("headers", [])
    for header in headers:
        if str(header.get("name", "")).lower() == header_name.lower():
            return str(header.get("value", "")).strip()
    return ""


def _parse_send_command(raw_args: str) -> tuple[str, str, str, str]:
    body = raw_args.split(" ", 1)[1].strip() if " " in raw_args else ""
    if not body:
        return "", "", "", "Kullanim: `/mail gonder alici@example.com | Konu | Icerik`"

    parts = [part.strip() for part in body.split("|", 2)]
    if len(parts) != 3 or not all(parts):
        return "", "", "", "Kullanim: `/mail gonder alici@example.com | Konu | Icerik`"
    return parts[0], parts[1], parts[2], ""


def _list_recent_messages(service) -> str:
    try:
        response = (
            service.users()
            .messages()
            .list(userId="me", labelIds=["INBOX"], maxResults=5)
            .execute()
        )
        messages = response.get("messages", [])
    except Exception as exc:
        return f"Gmail kutusu okunamadi: {exc}"

    if not messages:
        return "*Gmail*\n\nGelen kutusunda gosterilecek e-posta bulunamadi."

    lines = ["*Gmail - Son 5 E-posta*", ""]
    for index, message in enumerate(messages, start=1):
        try:
            detail = (
                service.users()
                .messages()
                .get(
                    userId="me",
                    id=message["id"],
                    format="metadata",
                    metadataHeaders=["From", "Subject"],
                )
                .execute()
            )
        except Exception as exc:
            lines.append(f"{index}. E-posta okunamadi: {_escape_markdown(exc)}")
            lines.append("")
            continue

        sender = _extract_header(detail, "From") or "Bilinmeyen gonderen"
        subject = _extract_header(detail, "Subject") or "Konu yok"
        snippet = detail.get("snippet", "") or "Ozet bulunamadi"

        lines.append(f"{index}. Gonderen: {_escape_markdown(sender)}")
        lines.append(f"   Konu: {_escape_markdown(subject)}")
        lines.append(f"   Ozet: {_escape_markdown(snippet)}")
        lines.append("")

    return "\n".join(lines).strip()


def _send_message(service, to_email: str, subject: str, content: str) -> str:
    message = EmailMessage()
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(content)

    encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    try:
        service.users().messages().send(userId="me", body={"raw": encoded_message}).execute()
    except Exception as exc:
        return f"E-posta gonderilemedi: {exc}"

    return (
        "*Gmail*\n\n"
        "E-posta gonderildi.\n"
        f"Alici: {_escape_markdown(to_email)}\n"
        f"Konu: {_escape_markdown(subject)}"
    )


def handle_gmail(args: str = "", user_id: str = "") -> str:
    raw_args = (args or "").strip()
    lowered = raw_args.lower()

    if lowered.startswith("gonder "):
        to_email, subject, content, error_message = _parse_send_command(raw_args)
        if error_message:
            return error_message
        service, error_message = _get_gmail_service([GMAIL_READ_SCOPE, GMAIL_SEND_SCOPE])
        if error_message:
            return error_message
        return _send_message(service, to_email, subject, content)

    if lowered in {"", "liste", "son", "son 5", "list"}:
        service, error_message = _get_gmail_service([GMAIL_READ_SCOPE])
        if error_message:
            return error_message
        return _list_recent_messages(service)

    return (
        "Gmail komutlari:\n"
        "- `/mail liste`\n"
        "- `/mail gonder alici@example.com | Konu | Icerik`"
    )
