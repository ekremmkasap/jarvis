#!/usr/bin/env python3
"""
Jarvis Stripe webhook skill.
Odeme tamamlandiginda yeni musteri onboarding kayitlarini olusturur.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
CUSTOMERS_DIR = DATA_DIR / "customers"
CUSTOMERS_DB_PATH = DATA_DIR / "customers.db"
SOUL_TEMPLATE_PATH = BASE_DIR / "config" / "soul_template.md"

PRICE_TO_PLAN = {
    "price_starter": "Starter",
    "price_pro": "Pro",
    "price_agency": "Agency",
}

AMOUNT_TO_PLAN = {
    150000: "Starter",
    350000: "Pro",
    750000: "Agency",
}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _get_stripe_module():
    try:
        import stripe  # type: ignore
    except ImportError:
        return None, (
            "stripe Python paketi yuklu degil. "
            "Lutfen `pip install stripe` ile kurulumu tamamlayin."
        )
    return stripe, ""


def _parse_json_input(args: str, context: dict | None = None) -> tuple[dict, str]:
    if isinstance(context, dict) and isinstance(context.get("payload"), dict):
        return dict(context["payload"]), ""

    raw_text = str(args or "").strip()
    if not raw_text:
        return {}, (
            "Stripe webhook payload'i gerekli. "
            "Beklenen format: {'payload': raw_body, 'signature': '...'} veya {'session': {...}}"
        )

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        return {}, f"Stripe webhook payload'i JSON olmali: {exc}"

    if not isinstance(payload, dict):
        return {}, "Stripe webhook payload'i JSON object olmali."

    return payload, ""


def _verify_stripe_event(raw_payload: str, signature: str) -> tuple[dict | None, str]:
    stripe_module, error_message = _get_stripe_module()
    if error_message:
        return None, error_message

    webhook_secret = os.environ.get("STRIPE_WEBHOOK_SECRET", "").strip()
    if not webhook_secret:
        return None, "STRIPE_WEBHOOK_SECRET tanimli degil."

    if not signature:
        return None, "Stripe-Signature degeri gerekli."

    try:
        event = stripe_module.Webhook.construct_event(raw_payload, signature, webhook_secret)
    except Exception as exc:
        return None, f"Stripe imza dogrulamasi basarisiz: {exc}"

    if hasattr(event, "to_dict_recursive"):
        event = event.to_dict_recursive()
    elif not isinstance(event, dict):
        try:
            event = dict(event)
        except Exception:
            return None, "Stripe webhook event'i beklenen formatta degil."

    return event, ""


def _extract_session(payload: dict) -> tuple[dict | None, str]:
    raw_payload = payload.get("payload") or payload.get("raw_body")
    signature = (
        payload.get("signature")
        or payload.get("stripe_signature")
        or payload.get("sig_header")
    )

    if isinstance(raw_payload, str) and raw_payload.strip():
        event, error_message = _verify_stripe_event(raw_payload, str(signature or "").strip())
        if error_message:
            return None, error_message

        event_type = str(event.get("type", "")).strip()
        if event_type != "checkout.session.completed":
            return None, f"Desteklenmeyen Stripe event tipi: {event_type or 'bos'}"

        data = event.get("data")
        session = data.get("object") if isinstance(data, dict) else None
        if not isinstance(session, dict):
            return None, "Stripe event icinde checkout session bulunamadi."
        return session, ""

    session = payload.get("session")
    if isinstance(session, dict):
        return session, ""

    data = payload.get("data")
    if isinstance(data, dict) and isinstance(data.get("session"), dict):
        return dict(data["session"]), ""

    if str(payload.get("object", "")).strip() == "checkout.session":
        return payload, ""

    return None, "Checkout session payload'i bulunamadi."


def _sanitize_customer_dir_name(email: str) -> str:
    clean_email = str(email or "").strip().lower()
    clean_email = clean_email.replace("/", "_").replace("\\", "_")
    return clean_email


def _guess_customer_name(session: dict, email: str) -> str:
    customer_details = session.get("customer_details")
    if isinstance(customer_details, dict):
        name = str(customer_details.get("name", "")).strip()
        if name:
            return name

    metadata = session.get("metadata")
    if isinstance(metadata, dict):
        for key in ("customer_name", "name", "full_name"):
            value = str(metadata.get(key, "")).strip()
            if value:
                return value

    local_part = email.split("@", 1)[0]
    pieces = [piece for piece in re.split(r"[^a-zA-Z0-9]+", local_part) if piece]
    if not pieces:
        return "Jarvis Musterisi"
    return " ".join(piece.capitalize() for piece in pieces[:3])


def _extract_email(session: dict) -> str:
    customer_details = session.get("customer_details")
    if isinstance(customer_details, dict):
        email = str(customer_details.get("email", "")).strip().lower()
        if email:
            return email

    for key in ("customer_email", "email"):
        email = str(session.get(key, "")).strip().lower()
        if email:
            return email

    metadata = session.get("metadata")
    if isinstance(metadata, dict):
        email = str(metadata.get("email", "")).strip().lower()
        if email:
            return email

    return ""


def _extract_price_id(session: dict) -> str:
    metadata = session.get("metadata")
    if isinstance(metadata, dict):
        for key in ("price_id", "price", "plan_id", "stripe_price_id"):
            price_id = str(metadata.get(key, "")).strip()
            if price_id:
                return price_id

    for collection_key in ("line_items", "display_items"):
        collection = session.get(collection_key)
        if isinstance(collection, dict):
            items = collection.get("data")
        else:
            items = collection
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            price = item.get("price")
            if isinstance(price, dict):
                price_id = str(price.get("id", "")).strip()
                if price_id:
                    return price_id

    subscription_details = session.get("subscription_details")
    if isinstance(subscription_details, dict):
        items = subscription_details.get("items")
        data = items.get("data") if isinstance(items, dict) else None
        if isinstance(data, list):
            for item in data:
                if not isinstance(item, dict):
                    continue
                price = item.get("price")
                if isinstance(price, dict):
                    price_id = str(price.get("id", "")).strip()
                    if price_id:
                        return price_id

    return ""


def _extract_plan(session: dict) -> tuple[str, str]:
    metadata = session.get("metadata")
    if isinstance(metadata, dict):
        raw_plan = str(metadata.get("plan", "")).strip().lower()
        if raw_plan in {"starter", "pro", "agency"}:
            return raw_plan.capitalize(), "metadata.plan"

    price_id = _extract_price_id(session)
    if price_id and price_id in PRICE_TO_PLAN:
        return PRICE_TO_PLAN[price_id], f"price:{price_id}"

    client_reference_id = str(session.get("client_reference_id", "")).strip()
    if client_reference_id in PRICE_TO_PLAN:
        return PRICE_TO_PLAN[client_reference_id], f"client_reference_id:{client_reference_id}"

    amount_total = session.get("amount_total")
    try:
        amount_total_value = int(amount_total)
    except (TypeError, ValueError):
        amount_total_value = None
    if amount_total_value in AMOUNT_TO_PLAN:
        return AMOUNT_TO_PLAN[amount_total_value], f"amount_total:{amount_total_value}"

    return "", ""


def _extract_customer_id(session: dict) -> str:
    for key in ("customer", "client_reference_id"):
        value = str(session.get(key, "")).strip()
        if value:
            return value
    return ""


def _render_soul_template(customer_name: str, plan: str, created_at: str) -> tuple[str, str]:
    if not SOUL_TEMPLATE_PATH.exists():
        return "", f"Soul template bulunamadi: {SOUL_TEMPLATE_PATH}"

    template = SOUL_TEMPLATE_PATH.read_text(encoding="utf-8")
    rendered = (
        template.replace("{CUSTOMER_NAME}", customer_name)
        .replace("{PLAN}", plan)
        .replace("{CREATED_AT}", created_at)
    )
    return rendered, ""


def _write_customer_files(session: dict, email: str, plan: str, created_at: str, customer_id: str) -> tuple[Path | None, str]:
    customer_dir = CUSTOMERS_DIR / _sanitize_customer_dir_name(email)
    customer_dir.mkdir(parents=True, exist_ok=True)

    config_payload = {
        "plan": plan,
        "created_at": created_at,
        "status": "active",
        "email": email,
        "customer_id": customer_id,
    }
    (customer_dir / "config.json").write_text(
        json.dumps(config_payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    customer_name = _guess_customer_name(session, email)
    soul_contents, error_message = _render_soul_template(customer_name, plan, created_at)
    if error_message:
        return None, error_message

    (customer_dir / "soul.md").write_text(soul_contents, encoding="utf-8")
    return customer_dir, ""


def _ensure_customers_table() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(CUSTOMERS_DB_PATH)) as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS customers (
                email TEXT PRIMARY KEY,
                customer_id TEXT NOT NULL,
                plan TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                customer_dir TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )


def _save_customer_record(email: str, customer_id: str, plan: str, created_at: str, customer_dir: Path) -> None:
    _ensure_customers_table()
    updated_at = _utcnow_iso()

    with sqlite3.connect(str(CUSTOMERS_DB_PATH)) as db:
        db.execute(
            """
            INSERT INTO customers (email, customer_id, plan, status, created_at, customer_dir, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(email) DO UPDATE SET
                customer_id = excluded.customer_id,
                plan = excluded.plan,
                status = excluded.status,
                customer_dir = excluded.customer_dir,
                updated_at = excluded.updated_at
            """,
            (
                email,
                customer_id,
                plan,
                "active",
                created_at,
                str(customer_dir),
                updated_at,
            ),
        )


def _send_admin_notification(email: str, plan: str, customer_id: str, customer_dir: Path) -> tuple[bool, str]:
    telegram_token = os.environ.get("TELEGRAM_TOKEN", "").strip()
    admin_chat_id = os.environ.get("ADMIN_CHAT_ID", "").strip()

    if not telegram_token or not admin_chat_id:
        return False, "TELEGRAM_TOKEN veya ADMIN_CHAT_ID tanimli degil."

    text = (
        "Yeni Jarvis musterisi onboard edildi.\n"
        f"Email: {email}\n"
        f"Plan: {plan}\n"
        f"Customer ID: {customer_id or '-'}\n"
        f"Klasor: {customer_dir}"
    )

    payload = urlencode({"chat_id": admin_chat_id, "text": text}).encode("utf-8")
    request = Request(
        f"https://api.telegram.org/bot{telegram_token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urlopen(request, timeout=10) as response:
            body = json.loads(response.read() or b"{}")
    except (HTTPError, URLError) as exc:
        return False, f"Telegram bildirimi gonderilemedi: {exc}"
    except Exception as exc:
        return False, f"Telegram bildirimi islenemedi: {exc}"

    if not body.get("ok", False):
        return False, f"Telegram API hatasi: {body}"

    return True, ""


def handle_checkout_session_completed(session: dict) -> dict:
    email = _extract_email(session)
    if not email:
        return {"ok": False, "message": "Stripe session icinde musteri e-postasi bulunamadi."}

    plan, plan_source = _extract_plan(session)
    if not plan:
        return {
            "ok": False,
            "message": "Stripe session icinde plan bilgisi bulunamadi. "
            "metadata.plan, price_id veya amount_total alanlarini kontrol edin.",
        }

    created_at = _utcnow_iso()
    customer_id = _extract_customer_id(session)
    customer_dir, file_error = _write_customer_files(
        session=session,
        email=email,
        plan=plan,
        created_at=created_at,
        customer_id=customer_id,
    )
    if file_error or customer_dir is None:
        return {"ok": False, "message": file_error or "Musteri dosyalari yazilamadi."}

    _save_customer_record(
        email=email,
        customer_id=customer_id,
        plan=plan,
        created_at=created_at,
        customer_dir=customer_dir,
    )

    notification_ok, notification_error = _send_admin_notification(
        email=email,
        plan=plan,
        customer_id=customer_id,
        customer_dir=customer_dir,
    )

    result = {
        "ok": True,
        "email": email,
        "plan": plan,
        "customer_id": customer_id,
        "created_at": created_at,
        "customer_dir": str(customer_dir),
        "plan_source": plan_source,
        "telegram_ok": notification_ok,
        "telegram_error": notification_error,
    }
    return result


def run(args: str, context: dict | None = None) -> str:
    payload, error_message = _parse_json_input(args, context)
    if error_message:
        return error_message

    session, error_message = _extract_session(payload)
    if error_message:
        return error_message

    result = handle_checkout_session_completed(session)
    if not result.get("ok"):
        return str(result.get("message", "Stripe webhook islenemedi."))

    lines = [
        "Stripe webhook onboarding tamamlandi.",
        f"Email: {result['email']}",
        f"Plan: {result['plan']}",
        f"Customer ID: {result['customer_id'] or '-'}",
        f"Klasor: {result['customer_dir']}",
    ]
    if not result.get("telegram_ok"):
        lines.append(f"Telegram uyarisi: {result.get('telegram_error')}")
    return "\n".join(lines)
