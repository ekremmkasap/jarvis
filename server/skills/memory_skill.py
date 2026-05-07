"""
Jarvis Memory System - SQLite tabanli kalici hafiza
Konusma gecmisi, kullanici bilgileri, ogrenilen gercekler
"""
import sqlite3, json, os, time, re
import contextlib
import io
from datetime import datetime
from pathlib import Path

try:
    import numpy as np
except Exception:
    np = None

try:
    from sentence_transformers import SentenceTransformer
except Exception:
    SentenceTransformer = None

try:
    import chromadb
except Exception:
    chromadb = None

SEMANTIC_AVAILABLE = bool(np is not None and SentenceTransformer is not None)
CHROMADB_AVAILABLE = chromadb is not None
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
_EMBEDDING_MODEL = None

DEFAULT_DB_PATH = Path(__file__).resolve().parents[1] / "data" / "jarvis_memory.db"
DB_PATH = Path(os.environ.get("JARVIS_MEMORY_DB", str(DEFAULT_DB_PATH))).expanduser()


def get_db_path() -> Path:
    env_override = os.environ.get("JARVIS_MEMORY_DB")
    if env_override:
        return Path(env_override).expanduser()
    return Path(DB_PATH).expanduser()


def _conn() -> sqlite3.Connection:
    db_path = get_db_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_embedding_table(db: sqlite3.Connection):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS memory_embeddings (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        memory_id   INTEGER NOT NULL,
        embedding   BLOB NOT NULL,
        FOREIGN KEY(memory_id) REFERENCES conversations(id)
    );

    CREATE INDEX IF NOT EXISTS idx_memory_embeddings_memory_id ON memory_embeddings (memory_id);
    """)


def _load_embedding_model():
    global _EMBEDDING_MODEL, SEMANTIC_AVAILABLE

    if not SEMANTIC_AVAILABLE:
        return None
    if _EMBEDDING_MODEL is not None:
        return _EMBEDDING_MODEL

    try:
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            _EMBEDDING_MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME, local_files_only=True)
    except TypeError:
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                _EMBEDDING_MODEL = SentenceTransformer(EMBEDDING_MODEL_NAME)
        except Exception:
            SEMANTIC_AVAILABLE = False
            _EMBEDDING_MODEL = None
            return None
    except Exception:
        SEMANTIC_AVAILABLE = False
        _EMBEDDING_MODEL = None
        return None

    return _EMBEDDING_MODEL


def _initialize_semantic_support() -> bool:
    global SEMANTIC_AVAILABLE

    if _load_embedding_model() is None:
        return False

    try:
        db_path = get_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(str(db_path)) as db:
            _ensure_embedding_table(db)
        return True
    except Exception:
        SEMANTIC_AVAILABLE = False
        return False


def _encode_text(text: str):
    model = _load_embedding_model()
    if model is None or np is None:
        return None

    clean_text = (text or "").strip()
    if not clean_text:
        return None

    try:
        vector = model.encode(clean_text, convert_to_numpy=True, show_progress_bar=False)
    except TypeError:
        vector = model.encode(clean_text)
    except Exception:
        return None

    return np.asarray(vector, dtype=np.float32)


def _embedding_to_blob(vector) -> bytes:
    return np.asarray(vector, dtype=np.float32).tobytes()


def _embedding_from_blob(blob):
    if np is None or blob is None:
        return None
    return np.frombuffer(blob, dtype=np.float32)


def _save_embedding(db: sqlite3.Connection, memory_id: int, message: str):
    if not SEMANTIC_AVAILABLE:
        return

    vector = _encode_text(message)
    if vector is None:
        return

    _ensure_embedding_table(db)
    db.execute("DELETE FROM memory_embeddings WHERE memory_id=?", (memory_id,))
    db.execute(
        "INSERT INTO memory_embeddings (memory_id, embedding) VALUES (?, ?)",
        (memory_id, sqlite3.Binary(_embedding_to_blob(vector)))
    )


def _row_to_search_result(row: sqlite3.Row, score: float = None) -> dict:
    return {
        "id": row["id"],
        "role": row["role"],
        "content": row["message"],
        "timestamp": row["timestamp"],
        "command": row["command"],
        "session_id": row["session_id"],
        "score": score,
    }


def _keyword_search_memory(user_id: str, query: str, top_k: int = 5) -> list:
    init_db()
    clean_query = (query or "").strip()
    limit = max(1, int(top_k))
    if not clean_query:
        return []

    with _conn() as db:
        rows = db.execute(
            "SELECT id, role, message, timestamp, command, session_id "
            "FROM conversations "
            "WHERE user_id=? AND message LIKE ? "
            "ORDER BY timestamp DESC LIMIT ?",
            (str(user_id), f"%{clean_query}%", limit)
        ).fetchall()

    return [_row_to_search_result(row) for row in rows]


_initialize_semantic_support()


def init_db():
    """Veritabani tablolarini olustur"""
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
        if SEMANTIC_AVAILABLE:
            _ensure_embedding_table(db)
    return True


# -------------------- KONUSMA GECMISI --------------------

def save_message(user_id: str, role: str, message: str,
                 command: str = None, session_id: str = None):
    """Mesaji kaydet"""
    init_db()
    stored_message = (message or "")[:2000]
    with _conn() as db:
        cursor = db.execute(
            "INSERT INTO conversations (user_id, role, message, command, session_id) VALUES (?,?,?,?,?)",
            (str(user_id), role, stored_message, command, session_id)
        )
        if SEMANTIC_AVAILABLE:
            _save_embedding(db, cursor.lastrowid, stored_message)
    # Extract facts in background
    if role == "user" and len(stored_message) > 10:
        _extract_facts(user_id, stored_message)


def search_memory(user_id: str, query: str, top_k: int = 5) -> list:
    """Mesaj hafizasinda ara; semantic yoksa keyword aramaya don."""
    clean_query = (query or "").strip()
    limit = max(1, int(top_k))
    if not clean_query:
        return []

    if not SEMANTIC_AVAILABLE:
        return _keyword_search_memory(user_id, clean_query, limit)

    query_vector = _encode_text(clean_query)
    if query_vector is None:
        return _keyword_search_memory(user_id, clean_query, limit)

    query_norm = float(np.linalg.norm(query_vector))
    if query_norm == 0.0:
        return _keyword_search_memory(user_id, clean_query, limit)

    init_db()
    with _conn() as db:
        rows = db.execute(
            "SELECT c.id, c.role, c.message, c.timestamp, c.command, c.session_id, me.embedding "
            "FROM conversations c "
            "JOIN memory_embeddings me ON me.memory_id = c.id "
            "WHERE c.user_id=?",
            (str(user_id),)
        ).fetchall()

    scored_rows = []
    for row in rows:
        vector = _embedding_from_blob(row["embedding"])
        if vector is None or vector.size != query_vector.size:
            continue

        vector_norm = float(np.linalg.norm(vector))
        if vector_norm == 0.0:
            continue

        score = float(np.dot(query_vector, vector) / (query_norm * vector_norm))
        scored_rows.append((score, row))

    if not scored_rows:
        return _keyword_search_memory(user_id, clean_query, limit)

    scored_rows.sort(key=lambda item: item[0], reverse=True)
    return [_row_to_search_result(row, score=score) for score, row in scored_rows[:limit]]


def get_history(user_id: str, limit: int = 10, command: str = None) -> list:
    """Son konusma gecmisini al"""
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
    """Ollama mesaj formatina cevir"""
    history = get_history(user_id, limit)
    return [{"role": m["role"], "content": m["content"]} for m in history]


def get_conversation_summary(user_id: str) -> str:
    """Kullanicinin konusma istatistikleri"""
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


# -------------------- KULLANICI BILGILERI --------------------

def save_fact(user_id: str, key: str, value: str, source: str = "manual"):
    """Kullanici hakkinda bilgi kaydet"""
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
    """Kullanici hakkinda bilinen gercekler"""
    init_db()
    with _conn() as db:
        rows = db.execute(
            "SELECT fact_key, fact_value FROM user_facts WHERE user_id=?",
            (str(user_id),)
        ).fetchall()
    return {r["fact_key"]: r["fact_value"] for r in rows}


def get_user_context(user_id: str) -> str:
    """Sistem promptu icin kullanici baglami"""
    facts = get_facts(user_id)
    if not facts:
        return ""
    lines = ["[Kullanici hakkinda bilinen bilgiler]"]
    for k, v in facts.items():
        lines.append(f"- {k}: {v}")
    return "\n".join(lines)


_NAME_BLACKLIST = {
    "bir", "iki", "şu", "bu", "o", "çok", "az", "ne", "nasıl", "kim",
    "hatalı", "yorgun", "mutlu", "üzgün", "sinirli", "açım", "bitkin",
    "iyi", "kötü", "burada", "evde", "işte", "burda",
}

_NAME_PREDICATE_SUFFIXES = (
    "yim", "im", "um", "üm", "yum", "yüm",
    "ciyim", "cıyım", "cuyum", "cüyüm", "çiyim", "çıyım",
    "liyim", "lıyım", "luyum", "lüyüm",
    "siyim", "sıyım", "suyum", "süyüm",
)


def _extract_facts(user_id: str, message: str):
    """Mesajdan otomatik bilgi cikar (basit kural tabanli)"""
    capture_patterns = [
        (r"benim\s+ad[ıi]m\s+([a-zçğıöşü]+)", "isim"),
        (r"ad[ıi]m\s+([a-zçğıöşü]+)", "isim"),
        (r"ben\s+([a-zçğıöşü]+)\s*[,\.!?]", "isim"),
        (r"ben\s+([a-zçğıöşü]+)\s*$", "isim"),
        (r"([a-zçğıöşü]+)\s+(?:şehrinde|sehrinde|sehirde|ilinde|ilçesinde)\s+(?:yaşıyorum|yasiyorum|oturuyorum|kalıyorum|kaliyorum)", "şehir"),
        (r"([a-zçğıöşü]+)['’]?(?:da|de|ta|te)\s+(?:yaşıyorum|yasiyorum|oturuyorum|kalıyorum|kaliyorum)", "şehir"),
        (r"(?:yaşım|yasim)\s+(\d+)", "yaş"),
        (r"(\d+)\s+(?:yaşındayım|yasindayim)", "yaş"),
        (r"(?:mesleğim|meslegim|işim|isim)\s+(?:olarak\s+)?([a-zçğıöşü]+)", "meslek"),
        (r"([a-zçğıöşü]+)(?:cıyım|ciyim|cuyum|cüyüm|çıyım|çiyim)\b", "meslek"),
    ]
    static_patterns = [
        (r"e[- ]?ticaret\s+(?:yapıyorum|yapiyorum|satıyorum|satiyorum|işi|isi)", "ilgi_alani", "e-ticaret"),
        (r"shopify\s+(?:mağazam|magazam|store)", "platform", "shopify"),
        (r"(?:trendyol|hepsiburada|amazon|ebay|etsy)\s+(?:satıcıyım|saticiyim|mağazam|magazam)", "platform", "pazaryeri"),
        (r"saas\s+(?:kurucusuyum|kuruyorum|yapıyorum|yapiyorum)", "ilgi_alani", "saas"),
        (r"(?:startup|girişim|girisim)\s+(?:kurucusuyum|kuruyorum)", "rol", "kurucu"),
    ]
    msg_lower = (message or "").lower()

    for pattern, key, value in static_patterns:
        if re.search(pattern, msg_lower):
            save_fact(user_id, key, value, source="auto")

    locked_keys = set()
    for pattern, key in capture_patterns:
        if key in locked_keys:
            continue
        match = re.search(pattern, msg_lower)
        if not match:
            continue
        captured = match.group(1).strip()
        if not captured or len(captured) < 2:
            continue
        if key == "isim":
            if captured in _NAME_BLACKLIST:
                continue
            if captured.endswith(_NAME_PREDICATE_SUFFIXES):
                continue
        save_fact(user_id, key, captured, source="auto")
        locked_keys.add(key)


# -------------------- GOREV TAKIBI --------------------

def add_task(user_id: str, title: str, priority: str = "normal", notes: str = None) -> int:
    """Gorev ekle"""
    init_db()
    with _conn() as db:
        cursor = db.execute(
            "INSERT INTO tasks (user_id, title, priority, notes) VALUES (?,?,?,?)",
            (str(user_id), title, priority, notes)
        )
    return cursor.lastrowid


def get_tasks(user_id: str, status: str = None) -> str:
    """Gorevleri listele"""
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
    """Gorev durumunu guncelle"""
    init_db()
    with _conn() as db:
        db.execute(
            "UPDATE tasks SET status=?, updated_at=strftime('%s','now') WHERE id=? AND user_id=?",
            (status, task_id, str(user_id))
        )
    return f"✅ Görev #{task_id} → {status}"


# -------------------- OZET RAPOR --------------------

def daily_memory_report(user_id: str) -> str:
    """Hafiza ozet raporu"""
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


# -------------------- TEST --------------------
if __name__ == "__main__":
    # Quick test
    DB_PATH = Path("/tmp/test_memory.db")
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
