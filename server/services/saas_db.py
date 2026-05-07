"""
SaaS Metrics Database Service
Stores and retrieves MRR, customer metrics, and financial data for Jarvis.
Email addresses are hashed with SHA256 — never stored in plain text.
"""

import sqlite3
import json
import hashlib
import os
from datetime import datetime, timedelta
from pathlib import Path
from threading import Lock

# Database file location
STATE_DIR = Path(__file__).parent.parent.parent / "state"
STATE_DIR.mkdir(exist_ok=True, parents=True)
DB_PATH = STATE_DIR / "saas_metrics.db"

# Thread-safe database access
DB_LOCK = Lock()

class SaasDB:
    """SQLite service for SaaS metrics, emails hashed for security."""

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_schema()

    def _init_schema(self):
        """Create tables if they don't exist."""
        with DB_LOCK:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()

            # MRR records (monthly recurring revenue)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS mrr_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date TEXT NOT NULL,
                    mrr_usd REAL NOT NULL,
                    customer_count INTEGER NOT NULL,
                    churn_rate REAL,
                    plan TEXT,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Customer events (SHA256-hashed emails, never plain text)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS customer_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    email_hash TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    amount REAL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()
            conn.close()

    @staticmethod
    def _hash_email(email: str) -> str:
        """SHA256 hash an email address."""
        return hashlib.sha256(email.lower().encode()).hexdigest()

    def add_mrr_record(self, mrr_usd: float, customer_count: int,
                       churn_rate: float = None, plan: str = None,
                       notes: str = None, date: str = None) -> int:
        """Add a new MRR record."""
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")

        with DB_LOCK:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO mrr_records (date, mrr_usd, customer_count, churn_rate, plan, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (date, mrr_usd, customer_count, churn_rate, plan, notes))
            record_id = cur.lastrowid
            conn.commit()
            conn.close()
        return record_id

    def log_customer_event(self, email: str, event_type: str, amount: float = None):
        """Log a customer event (signup, payment, churn, etc.) with hashed email."""
        email_hash = self._hash_email(email)
        with DB_LOCK:
            conn = sqlite3.connect(self.db_path)
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO customer_events (email_hash, event_type, amount)
                VALUES (?, ?, ?)
            """, (email_hash, event_type, amount))
            conn.commit()
            conn.close()

    def get_current_mrr(self) -> dict:
        """Get the latest MRR record."""
        with DB_LOCK:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM mrr_records ORDER BY created_at DESC LIMIT 1")
            row = cur.fetchone()
            conn.close()

        if row is None:
            return {}
        return dict(row)

    def get_mrr_trend(self, days: int = 30) -> list:
        """Get MRR trend for the last N days."""
        with DB_LOCK:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cutoff_date = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
            cur.execute("""
                SELECT date, mrr_usd, customer_count, churn_rate
                FROM mrr_records
                WHERE date >= ?
                ORDER BY date ASC
            """, (cutoff_date,))
            rows = cur.fetchall()
            conn.close()

        return [dict(row) for row in rows]

    def get_customer_count(self) -> int:
        """Get current customer count from latest MRR record."""
        current = self.get_current_mrr()
        return current.get("customer_count", 0)

    def calculate_metrics(self) -> dict:
        """Calculate SaaS metrics: MRR, churn, LTV."""
        current = self.get_current_mrr()
        if not current:
            return {}

        mrr = current.get("mrr_usd", 0)
        customers = current.get("customer_count", 0)
        churn_rate = current.get("churn_rate", 0)

        # Average revenue per user
        arpu = (mrr / customers) if customers > 0 else 0

        # Lifetime value (LTV) = ARPU / churn_rate (simplified)
        ltv = (arpu / churn_rate) if churn_rate > 0 else 0

        return {
            "mrr_usd": mrr,
            "customer_count": customers,
            "churn_rate": churn_rate,
            "arpu": round(arpu, 2),
            "ltv": round(ltv, 2)
        }


def init_saas_db():
    """Initialize the SaaS database."""
    db = SaasDB()
    return db


if __name__ == "__main__":
    # Test the database
    db = SaasDB()

    # Add a test MRR record
    print("Adding test MRR record...")
    db.add_mrr_record(
        mrr_usd=5000,
        customer_count=10,
        churn_rate=0.05,
        plan="starter",
        notes="Q2 2026 initial"
    )

    # Log a test customer event
    print("Logging customer event...")
    db.log_customer_event("test@example.com", "signup", 1500)

    # Retrieve current MRR
    print("Current MRR:", db.get_current_mrr())

    # Calculate metrics
    print("Metrics:", db.calculate_metrics())

    print("✓ SaasDB test passed")
