"""
Jarvis Memory System — SQLite tabanlı kalıcı hafıza
Konuşma geçmişi, kullanıcı bilgileri, öğrenilen gerçekler
"""
import sqlite3, json, os, time, re
from datetime import datetime

DB_PATH = "/opt/jarvis/memory/jarvis_memory.db"


def _conn() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Veritabanı tablolarını oluştur"""
    with _conn() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS conversations (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            role        TEXT NOT NULL,  -- 'user' veya 'assistant'
            message     TEXT NOT NULL,
            command     TEXT,
            timestamp   REAL DEFAULT (strftime('%s', 'now')),
            session_id  TEXT
        );

        CREATE TABLE IF NOT EXISTS user_facts (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            fact_key    TEXT NOT NULL,
            fact_value  TEXT NOT NULL,
            confidence  REAL DEFAULT 1.0,
            source      TEXT,
            updated_at  REAL DEFAULT (strftime('%s', 'now')),
            UNIQUE(user_id, fact_key)
        );

        CREATE TABLE IF NOT EXISTS tasks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     TEXT NOT NULL,
            title       TEXT NOT NULL,
            status      TEXT DEFAULT 'todo',  -- todo/doing/done
            priority    TEXT DEFAULT 'normal',
            created_at  REAL DEFAULT (strftime('%s', 'now')),
            updated_at  REAL DEFAULT (strftime('%s', 'now')),
            notes       TEXT
        );

        CREATE INDEX IF NOT EXISTS idx_conv_user ON conversations (user_id, timestamp);
        CREATE INDEX IF NOT EXISTS idx_facts_user ON user_facts (user_id);
        """)
    return True


# ─── KONUŞMA GEÇMİŞİ ─────────────────────────────────────────────────────────

def save_message(user_id: str, role: str, message: str,
                 command: str = None, session_id: str = None):
    """Mesajı kaydet"""
    init_db()
    with _conn() as db:
        db.execute(
            "INSERT INTO conversations (user_id, role, message, command, session_id) VALUES (?,?,?,?,?)",
            (str(user_id), role, message[:2000], command, session_id)
        )
    # Extract facts in background
    if role == "user" and len(message) > 10:
        _extract_facts(user_id, message)


def get_history(user_id: str, limit: int = 10, command: str = None) -> list:
    """Son konuşma geçmişini al"""
    init_db()
    with _conn() as db:
        if command:
            rows = db.execute(
                "SELECT role, message, timestamp FROM conversations "
                "WHERE user_id=? AND command=? ORDER BY timestamp DESC LIMIT ?",
                (str(user_id), command, limit)
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT role, message, timestamp FROM conversations "
                "WHERE user_id=? ORDER BY timestamp DESC LIMIT ?",
                (str(user_id), limit)
            ).fetchall()
    return [{"role": r["role"], "content": r["message"]} for r in reversed(rows)]


def format_history_for_ollama(user_id: str, limit: int = 6) -> list:
    """Ollama mesaj formatına çevir"""
    history = get_history(user_id, limit)
    return [{"role": m["role"], "content": m["content"]} for m in history]


def get_conversation_summary(user_id: str) -> str:
    """Kullanıcının konuşma istatistikleri"""
    init_db()
    with _conn() as db:
        total = db.execute(
            "SELECT COUNT(*) as cnt FROM conversations WHERE user_id=?", (str(user_id),)
        ).fetchone()["cnt"]
        last = db.execute(
            "SELECT timestamp FROM conversations WHERE user_id=? ORDER BY timestamp DESC LIMIT 1",
            (str(user_id),)
        ).fetchone()
    
    if total == 0:
        return "Henüz konuşma geçmişi yok."
    
    last_time = datetime.fromtimestamp(last["timestamp"]).strftime("%d.%m.%Y %H:%M") if last else "?"
    return f"📊 {total} mesaj | Son: {last_time}"


# ─── KULLANICI BİLGİLERİ ─────────────────────────────────────────────────────

def save_fact(user_id: str, key: str, value: str, source: str = "manual"):
    """Kullanıcı hakkında bilgi kaydet"""
    init_db()
    with _conn() as db:
        db.execute(
            """INSERT INTO user_facts (user_id, fact_key, fact_value, source, updated_at)
               VALUES (?,?,?,?,strftime('%s','now'))
               ON CONFLICT(user_id, fact_key)
               DO UPDATE SET fact_value=excluded.fact_value,
                             source=excluded.source,
                             updated_at=strftime('%s','now')""",
            (str(user_id), key.lower(), value, source)
        )


def get_facts(user_id: str) -> dict:
    """Kullanıcı hakkında bilinen gerçekler"""
    init_db()
    with _conn() as db:
        rows = db.execute(
            "SELECT fact_key, fact_value FROM user_facts WHERE user_id=?",
            (str(user_id),)
        ).fetchall()
    return {r["fact_key"]: r["fact_value"] for r in rows}


def get_user_context(user_id: str) -> str:
    """Sistem promptu için kullanıcı bağlamı"""
    facts = get_facts(user_id)
    if not facts:
        return ""
    lines = ["[Kullanıcı hakkında bilinen bilgiler]"]
    for k, v in facts.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


def _extract_facts(user_id: str, message: str):
    """Mesajdan otomatik bilgi çıkar (basit kural tabanlı)"""
    patterns = [
        (r"ben\s+(\w+)(?:yim|im|um|üm)", "isim"),
        (r"ad[ım]+\s+(\w+)", "isim"),
        (r"(\w+)\s+(?:şehrinde|şehirde|ilinde)\s+(?:yaşıyorum|oturuyorum)", "şehir"),
        (r"(?:yaşım|yaşındayım)\s+(\d+)", "yaş"),
        (r"(\d+)\s+yaşındayım", "yaş"),
        (r"(?:işim|mesleğim|çalışıyorum)\s+(?:olarak\s+)?(\w+)", "meslek"),
        (r"e[- ]?ticaret\s+(?:yapıyorum|satıyorum)", "ilgi_alani", "e-ticaret"),
        (r"shopify\s+(?:mağazam|store)", "platform", "shopify"),
    ]
    msg_lower = message.lower()
    for pattern_data in patterns:
        if len(pattern_data) == 3 and not pattern_data[1].startswith("("):
            # Static fact
            pattern, key, value = pattern_data
            if re.search(pattern, msg_lower):
                save_fact(user_id, key, value, source="auto")
        elif len(pattern_data) == 2:
            pattern, key = pattern_data
            match = re.search(pattern, msg_lower)
            if match:
                save_fact(user_id, key, match.group(1), source="auto")


# ─── GÖREV TAKİBİ ─────────────────────────────────────────────────────────────

def add_task(user_id: str, title: str, priority: str = "normal", notes: str = None) -> int:
    """Görev ekle"""
    init_db()
    with _conn() as db:
        cursor = db.execute(
            "INSERT INTO tasks (user_id, title, priority, notes) VALUES (?,?,?,?)",
            (str(user_id), title, priority, notes)
        )
    return cursor.lastrowid


def get_tasks(user_id: str, status: str = None) -> str:
    """Görevleri listele"""
    init_db()
    with _conn() as db:
        if status:
            rows = db.execute(
                "SELECT * FROM tasks WHERE user_id=? AND status=? ORDER BY priority, created_at",
                (str(user_id), status)
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM tasks WHERE user_id=? AND status!='done' ORDER BY priority, created_at",
                (str(user_id),)
            ).fetchall()
    
    if not rows:
        return "📋 Aktif görev yok."
    
    emoji = {"high": "🔴", "normal": "🟡", "low": "🟢"}
    status_emoji = {"todo": "⬜", "doing": "🔄", "done": "✅"}
    
    lines = ["📋 **Görevler:**\n"]
    for r in rows:
        e = emoji.get(r["priority"], "⬜")
        s = status_emoji.get(r["status"], "⬜")
        lines.append(f"{s}{e} {r['title']} (#{r['id']})")
    
    return "\n".join(lines)


def update_task(user_id: str, task_id: int, status: str) -> str:
    """Görev durumunu güncelle"""
    init_db()
    with _conn() as db:
        db.execute(
            "UPDATE tasks SET status=?, updated_at=strftime('%s','now') WHERE id=? AND user_id=?",
            (status, task_id, str(user_id))
        )
    return f"✅ Görev #{task_id} → {status}"


# ─── ÖZET RAPOR ──────────────────────────────────────────────────────────────

def daily_memory_report(user_id: str) -> str:
    """Hafıza özet raporu"""
    init_db()
    facts = get_facts(user_id)
    conv_summary = get_conversation_summary(user_id)
    
    lines = ["🧠 **Jarvis Hafıza Raporu**\n"]
    lines.append(f"💬 Konuşmalar: {conv_summary}")
    
    if facts:
        lines.append("\n📌 **Bildiğim bilgiler:**")
        for k, v in facts.items():
            lines.append(f"  • {k}: {v}")
    
    return "\n".join(lines)


# ─── TEST ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Quick test
    DB_PATH = "/tmp/test_memory.db"
    init_db()
    save_message("123", "user", "Merhaba, benim adım Sergen")
    save_message("123", "assistant", "Merhaba Sergen! Nasıl yardımcı olabilirim?")
    save_fact("123", "sehir", "Istanbul")
    save_fact("123", "platform", "shopify,trendyol,ebay")
    
    print(get_conversation_summary("123"))
    print()
    print(get_user_context("123"))
    print()
    print(get_tasks("123"))
    add_task("123", "Shopify token al", "high")
    add_task("123", "Printify entegrasyonu", "normal")
    print(get_tasks("123"))
    print()
    print(daily_memory_report("123"))
