from __future__ import annotations

import importlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs
from unittest.mock import patch

SERVER_PATH = Path(__file__).parent.parent / "server"
if str(SERVER_PATH) not in sys.path:
    sys.path.append(str(SERVER_PATH))

import skills.stripe_webhook_skill as stripe_webhook_skill


class _DummyUrlopenResponse:
    def __enter__(self) -> "_DummyUrlopenResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def read(self) -> bytes:
        return b'{"ok": true}'


class _FakeStripeWebhook:
    def __init__(self, side_effect=None, payload=None):
        self.side_effect = side_effect
        self.payload = payload or {
            "type": "checkout.session.completed",
            "data": {"object": {"id": "cs_test"}},
        }

    def construct_event(self, raw_payload, signature, webhook_secret):
        if self.side_effect is not None:
            raise self.side_effect
        return self.payload


class _FakeStripeModule:
    def __init__(self, webhook):
        self.Webhook = webhook


class StripeWebhookSkillTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.original_env = os.environ.copy()
        self.module = importlib.reload(stripe_webhook_skill)

        self.module.DATA_DIR = self.temp_dir / "data"
        self.module.CUSTOMERS_DIR = self.module.DATA_DIR / "customers"
        self.module.CUSTOMERS_DB_PATH = self.module.DATA_DIR / "customers.db"
        self.module.CUSTOMERS_REGISTRY_PATH = self.module.DATA_DIR / "customers.json"
        self.module.TENANTS_DIR = self.temp_dir / "tenants"
        self.module.TENANT_TEMPLATE_PATH = self.module.TENANTS_DIR / "_template" / "config.json"
        self.module.SOUL_TEMPLATE_PATH = self.temp_dir / "soul_template.md"
        self.module.TENANT_TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        self.module.TENANT_TEMPLATE_PATH.write_text(
            json.dumps(
                {
                    "tenant_id": "TENANT_ID",
                    "name": "Template",
                    "plan": "starter",
                    "features": [],
                }
            ),
            encoding="utf-8",
        )
        self.module.SOUL_TEMPLATE_PATH.write_text(
            "Customer: {CUSTOMER_NAME}\nPlan: {PLAN}\nCreated: {CREATED_AT}\n",
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        os.environ.clear()
        os.environ.update(self.original_env)
        importlib.reload(stripe_webhook_skill)
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_handle_checkout_session_completed_uses_env_price_id_map(self) -> None:
        os.environ["STRIPE_PRO_PRICE_ID"] = "price_real_pro"

        session = {
            "id": "cs_test_pro",
            "customer": "cus_123",
            "customer_details": {
                "email": "test@example.com",
                "name": "Test User",
            },
            "line_items": [
                {
                    "price": {
                        "id": "price_real_pro",
                    }
                }
            ],
        }

        with patch.object(self.module, "_send_admin_notification", return_value=(True, "")):
            result = self.module.handle_checkout_session_completed(session)

        self.assertTrue(result["ok"])
        self.assertEqual(result["plan"], "Pro")
        self.assertEqual(result["plan_source"], "price:price_real_pro")
        self.assertEqual(result["tenant_id"], "test")

        customer_dir = Path(result["customer_dir"])
        self.assertTrue((customer_dir / "config.json").exists())
        self.assertTrue((customer_dir / "soul.md").exists())
        tenant_dir = Path(result["tenant_dir"])
        self.assertTrue((tenant_dir / "config.json").exists())
        self.assertTrue((tenant_dir / "soul.md").exists())

        config_payload = json.loads((customer_dir / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(config_payload["email"], "test@example.com")
        self.assertEqual(config_payload["plan"], "Pro")
        self.assertEqual(config_payload["tenant_id"], "test")

        tenant_payload = json.loads((tenant_dir / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(tenant_payload["tenant_id"], "test")
        self.assertEqual(tenant_payload["plan"], "pro")
        self.assertEqual(tenant_payload["customer_email"], "test@example.com")

        with sqlite3.connect(str(self.module.CUSTOMERS_DB_PATH)) as db:
            row = db.execute(
                "SELECT email, customer_id, plan, status, tenant_id FROM customers WHERE email = ?",
                ("test@example.com",),
            ).fetchone()
            processed = db.execute(
                "SELECT session_id FROM processed_sessions WHERE email = ?",
                ("test@example.com",),
            ).fetchone()

        self.assertEqual(row, ("test@example.com", "cus_123", "Pro", "active", "test"))
        self.assertEqual(processed, ("cs_test_pro",))

        registry = json.loads(self.module.CUSTOMERS_REGISTRY_PATH.read_text(encoding="utf-8"))
        self.assertEqual(registry[0]["tenant_id"], "test")
        self.assertEqual(registry[0]["email"], "test@example.com")

    def test_run_accepts_session_payload_and_uses_amount_override(self) -> None:
        os.environ["STRIPE_STARTER_AMOUNT"] = "99000"

        payload = {
            "session": {
                "customer_details": {
                    "email": "starter@example.com",
                    "name": "Starter User",
                },
                "amount_total": 99000,
                "customer": "cus_starter",
            }
        }

        with patch.object(self.module, "_send_admin_notification", return_value=(False, "disabled")):
            result = self.module.run(json.dumps(payload))

        self.assertIn("Stripe webhook onboarding tamamlandi.", result)
        self.assertIn("Email: starter@example.com", result)
        self.assertIn("Plan: Starter", result)
        self.assertIn("Tenant ID: starter", result)
        self.assertIn("Telegram uyarisi: disabled", result)

    def test_admin_notification_uses_repo_telegram_env_names(self) -> None:
        os.environ["TELEGRAM_BOT_TOKEN"] = "bot-token"
        os.environ["TELEGRAM_CHAT_ID"] = "987654"

        with patch.object(self.module, "urlopen", return_value=_DummyUrlopenResponse()) as mocked_urlopen:
            ok, error = self.module._send_admin_notification(
                email="notify@example.com",
                plan="Agency",
                customer_id="cus_notify",
                customer_dir=self.temp_dir,
            )

        self.assertTrue(ok)
        self.assertEqual(error, "")
        self.assertEqual(mocked_urlopen.call_count, 1)
        request = mocked_urlopen.call_args.args[0]
        self.assertIn("bot-token", request.full_url)
        payload = parse_qs(request.data.decode("utf-8"))
        self.assertEqual(payload["chat_id"], ["987654"])
        self.assertIn("notify@example.com", payload["text"][0])
        self.assertIn("Agency", payload["text"][0])

    def test_duplicate_session_is_skipped(self) -> None:
        session = {
            "id": "cs_test_duplicate",
            "payment_status": "paid",
            "customer": "cus_dup",
            "customer_details": {
                "email": "dup@example.com",
                "name": "Dup User",
            },
            "metadata": {"plan": "pro"},
        }

        with patch.object(self.module, "_send_admin_notification", return_value=(True, "")):
            first = self.module.handle_checkout_session_completed(session)
            second = self.module.handle_checkout_session_completed(session)

        self.assertTrue(first["ok"])
        self.assertTrue(second["ok"])
        self.assertTrue(second["duplicate"])
        self.assertEqual(second["session_id"], "cs_test_duplicate")

    def test_unpaid_session_is_reported_as_skipped(self) -> None:
        session = {
            "id": "cs_test_unpaid",
            "payment_status": "unpaid",
            "customer_details": {
                "email": "pending@example.com",
            },
            "metadata": {"plan": "starter"},
        }

        result = self.module.handle_checkout_session_completed(session)

        self.assertTrue(result["ok"])
        self.assertTrue(result["skipped"])
        self.assertIn("odemesi henuz tamamlanmamis", result["message"])

    def test_unknown_plan_returns_error(self) -> None:
        session = {
            "id": "cs_test_unknown_plan",
            "payment_status": "paid",
            "customer": "cus_unknown",
            "customer_details": {
                "email": "unknown@example.com",
            },
        }

        result = self.module.handle_checkout_session_completed(session)

        self.assertFalse(result["ok"])
        self.assertIn("plan bilgisi bulunamadi", result["message"])

    def test_missing_env_returns_webhook_secret_error(self) -> None:
        os.environ.pop("STRIPE_WEBHOOK_SECRET", None)
        fake_stripe = _FakeStripeModule(_FakeStripeWebhook())

        with patch.object(self.module, "_get_stripe_module", return_value=(fake_stripe, "")):
            event, error = self.module._verify_stripe_event("{}", "sig_test")

        self.assertIsNone(event)
        self.assertEqual(error, "STRIPE_WEBHOOK_SECRET tanimli degil.")

    def test_invalid_signature_is_reported(self) -> None:
        os.environ["STRIPE_WEBHOOK_SECRET"] = "whsec_test"
        fake_stripe = _FakeStripeModule(_FakeStripeWebhook(side_effect=ValueError("bad signature")))

        with patch.object(self.module, "_get_stripe_module", return_value=(fake_stripe, "")):
            event, error = self.module._extract_session(
                {"payload": "{}", "signature": "sig_invalid"}
            )

        self.assertIsNone(event)
        self.assertIn("Stripe imza dogrulamasi basarisiz", error)


if __name__ == "__main__":
    unittest.main()
