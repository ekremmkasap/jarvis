"""
Skill: memory_compactor
Kategori: cognitive
chat_history.jsonl dolunca eski konuşmaları özetleyip sıkıştırır.
Her 50 mesajda bir çalışır, eski kısmı özet olarak saklar.
"""
import json
import logging
import subprocess
import datetime
from pathlib import Path

log = logging.getLogger("skill.memory_compactor")

CHAT_HISTORY = Path("/opt/jarvis/memory/working_memory/chat_history.jsonl")
SUMMARY_FILE = Path("/opt/jarvis/memory/project_memory/chat_summaries.md")
CLAUDE_BIN   = "/home/userk/.npm-global/bin/claude"

COMPACT_THRESHOLD = 50   # kaç mesajdan sonra sıkıştır
KEEP_RECENT       = 10   # sıkıştırma sonrası kaç yeni mesaj bırak

MANIFEST = {
    "name": "memory_compactor",
    "version": "1.0",
    "category": "cognitive",
    "inputs": {"force": "bool"},
    "outputs": {"compacted": "bool", "summary": "str"},
    "permissions": ["read", "write"],
    "failure_modes": ["claude_error", "file_error"],
    "logs": ["message_count", "compacted", "summary_length"]
}


def run(force: bool = False) -> dict:
    if not CHAT_HISTORY.exists():
        return {"compacted": False, "summary": "Geçmiş yok.", "error": None}

    lines = [l for l in CHAT_HISTORY.read_text(encoding="utf-8").strip().split("\n") if l.strip()]
    messages = []
    for l in lines:
        try:
            messages.append(json.loads(l))
        except Exception:
            pass

    count = len(messages)
    log.info(f"Chat history: {count} mesaj")

    if count < COMPACT_THRESHOLD and not force:
        return {"compacted": False, "summary": f"{count} mesaj var, henüz sıkıştırma gerekmez ({COMPACT_THRESHOLD} eşik).", "error": None}

    # Özetlenecek eski kısım
    old_messages = messages[:-KEEP_RECENT]
    recent_messages = messages[-KEEP_RECENT:]

    if not old_messages:
        return {"compacted": False, "summary": "Özetlenecek eski mesaj yok.", "error": None}

    # Claude ile özetle
    conversation_text = "\n".join(
        f"{'Kullanıcı' if m.get('role') == 'user' else 'Jarvis'}: {m.get('content', '')}"
        for m in old_messages
    )
    prompt = (
        f"Aşağıdaki {len(old_messages)} mesajlık konuşmayı kısa, bilgi odaklı özetle. "
        f"Önemli kararlar, öğrenilen şeyler, yapılan işlemler vurgulanmalı. "
        f"Türkçe, 200 kelime max:\n\n{conversation_text[:3000]}"
    )

    summary = ""
    try:
        result = subprocess.run(
            [CLAUDE_BIN, "-p", prompt],
            capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace"
        )
        summary = result.stdout.strip() or "Özet alınamadı."
    except Exception as e:
        log.error(f"Claude özet hatası: {e}")
        # Fallback: ilk ve son 3 mesajı al
        sample = old_messages[:3] + old_messages[-3:]
        summary = f"[Otomatik özet alınamadı] {len(old_messages)} mesaj sıkıştırıldı."

    # Özeti kaydet
    date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M")
    summary_entry = f"\n## {date_str} ({len(old_messages)} mesaj özetlendi)\n{summary}\n"
    SUMMARY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SUMMARY_FILE, "a", encoding="utf-8") as f:
        f.write(summary_entry)

    # chat_history.jsonl'i sadece son mesajlarla güncelle
    with open(CHAT_HISTORY, "w", encoding="utf-8") as f:
        for msg in recent_messages:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")

    log.info(f"Sıkıştırıldı: {len(old_messages)} mesaj → özet, {len(recent_messages)} mesaj korundu")
    return {
        "compacted": True,
        "summary": summary[:300],
        "kept": len(recent_messages),
        "archived": len(old_messages),
        "error": None
    }


if __name__ == "__main__":
    r = run(force=True)
    print(f"Sıkıştırıldı: {r['compacted']}")
    print(f"Özet: {r['summary'][:200]}")
