"""
ReMe - Jarvis Uzun Vadeli Hafıza Modülü
SQLite tabanlı, async, Ollama embedding opsiyonel.
bridge.py'nin beklediği API'yi tam karşılar.
"""
import asyncio
import json
import logging
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

log = logging.getLogger("reme")


@dataclass
class Memory:
    id: int
    content: str
    user_name: str
    created_at: float

    def __repr__(self):
        return f"<Memory user={self.user_name} content={self.content[:60]}>"


class ReMe:
    """
    Basit SQLite tabanlı uzun vadeli hafıza.
    bridge.py ile uyumlu async API sunar.
    """

    def __init__(
        self,
        working_dir: str = ".reme",
        enable_logo: bool = False,
        log_to_console: bool = False,
        default_llm_config: dict = None,
        default_embedding_model_config: dict = None,
        default_vector_store_config: dict = None,
    ):
        self.working_dir = Path(working_dir)
        self.working_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = self.working_dir / "memory.db"
        self._conn: Optional[sqlite3.Connection] = None
        self._ready = False

        if log_to_console:
            logging.basicConfig(level=logging.INFO)

    async def start(self):
        """DB bağlantısı kur, tabloyu oluştur."""
        self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        """)
        self._conn.execute("CREATE INDEX IF NOT EXISTS idx_user ON memories(user_name)")
        self._conn.commit()
        self._ready = True
        log.info(f"ReMe hazır: {self.db_path}")

    async def add_memory(self, memory_content: str, user_name: str = "ekrem") -> Memory:
        """Yeni bellek kaydı ekle."""
        if not self._ready:
            raise RuntimeError("ReMe henüz başlatılmadı, start() çağır.")
        now = time.time()
        cur = self._conn.execute(
            "INSERT INTO memories (user_name, content, created_at) VALUES (?, ?, ?)",
            (user_name, memory_content, now)
        )
        self._conn.commit()
        log.debug(f"Bellek kaydedildi: {memory_content[:60]}")
        return Memory(id=cur.lastrowid, content=memory_content, user_name=user_name, created_at=now)

    async def list_memory(self, user_name: str = "ekrem", limit: int = 5) -> list[Memory]:
        """Son N bellek kaydını getir."""
        if not self._ready:
            return []
        rows = self._conn.execute(
            "SELECT id, content, user_name, created_at FROM memories "
            "WHERE user_name = ? ORDER BY created_at DESC LIMIT ?",
            (user_name, limit)
        ).fetchall()
        return [Memory(id=r[0], content=r[1], user_name=r[2], created_at=r[3]) for r in rows]

    async def search_memory(self, query: str, user_name: str = "ekrem", limit: int = 5) -> list[Memory]:
        """Keyword araması (vector search yoksa basit LIKE)."""
        if not self._ready:
            return []
        rows = self._conn.execute(
            "SELECT id, content, user_name, created_at FROM memories "
            "WHERE user_name = ? AND content LIKE ? ORDER BY created_at DESC LIMIT ?",
            (user_name, f"%{query}%", limit)
        ).fetchall()
        return [Memory(id=r[0], content=r[1], user_name=r[2], created_at=r[3]) for r in rows]

    async def delete_memory(self, memory_id: int):
        """Bellek kaydını sil."""
        if not self._ready:
            return
        self._conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        self._conn.commit()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None
            self._ready = False
