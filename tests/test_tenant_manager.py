from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from server.skills.tenant_manager import TenantManager


class TenantManagerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = Path(tempfile.mkdtemp())
        self.customers_dir = self.temp_dir / "customers"
        self.soul_template = self.temp_dir / "soul_template.md"
        self.soul_template.write_text(
            "Email: {CUSTOMER_EMAIL}\nPlan: {PLAN}\nCreated: {CREATED_AT}\n",
            encoding="utf-8",
        )
        self.manager = TenantManager(
            base_dir=self.customers_dir,
            soul_template=self.soul_template,
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_create_tenant_creates_config_soul_and_memory_db(self) -> None:
        result = self.manager.create_tenant("demo@example.com", "pro")

        self.assertTrue(result["ok"])
        tenant_dir = Path(result["tenant_dir"])
        self.assertTrue((tenant_dir / "config.json").exists())
        self.assertTrue((tenant_dir / "soul.md").exists())
        self.assertTrue((tenant_dir / "memory.db").exists())

        config = json.loads((tenant_dir / "config.json").read_text(encoding="utf-8"))
        self.assertEqual(config["email"], "demo@example.com")
        self.assertEqual(config["plan"], "pro")

        soul_text = (tenant_dir / "soul.md").read_text(encoding="utf-8")
        self.assertIn("demo@example.com", soul_text)
        self.assertIn("pro", soul_text)

    def test_get_and_deactivate_tenant(self) -> None:
        self.manager.create_tenant("owner@example.com", "starter")

        tenant = self.manager.get_tenant("owner@example.com")
        self.assertIsNotNone(tenant)
        assert tenant is not None
        self.assertEqual(tenant["status"], "active")

        self.assertTrue(self.manager.deactivate_tenant("owner@example.com"))
        updated = self.manager.get_tenant("owner@example.com")
        assert updated is not None
        self.assertEqual(updated["status"], "inactive")

    def test_list_tenants_returns_only_active_records(self) -> None:
        self.manager.create_tenant("one@example.com", "starter")
        self.manager.create_tenant("two@example.com", "agency")
        self.manager.deactivate_tenant("two@example.com")

        tenants = self.manager.list_tenants()

        self.assertEqual(len(tenants), 1)
        self.assertEqual(tenants[0]["email"], "one@example.com")

    def test_get_tenant_stats(self) -> None:
        self.manager.create_tenant("one@example.com", "starter")
        self.manager.create_tenant("two@example.com", "agency")
        self.manager.deactivate_tenant("two@example.com")

        stats = self.manager.get_tenant_stats()

        self.assertEqual(stats["total_customers"], 2)
        self.assertEqual(stats["active_customers"], 1)
        self.assertEqual(stats["plan_distribution"]["starter"], 1)
        self.assertEqual(stats["plan_distribution"]["agency"], 1)
        self.assertGreaterEqual(stats["new_this_month"], 2)


if __name__ == "__main__":
    unittest.main()
