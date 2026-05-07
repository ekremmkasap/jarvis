#!/usr/bin/env python3
"""
JARVIS CONVERSATION LEARNER
Her Telegram komutunu loglar, pattern çıkarır, öğrenir.
"""

import json
import time
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Callable

log = logging.getLogger("jarvis.conversation_learner")


class ConversationLearner:
    """
    Her komutu loglar. Periyodik olarak Ollama ile analiz eder.
    Öğrendiklerini wiki/hot.md ve server/logs/learning/insights.md'ye yazar.
    """

    def __init__(self, call_ollama_fn: Callable, data_dir: str = "server/logs/learning"):
        self.call_ollama = call_ollama_fn
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.conv_log = self.data_dir / "conversations.jsonl"
        self.insights_file = self.data_dir / "insights.md"
        self.wiki_hot = Path("wiki/hot.md")

        log.info("[ConversationLearner] Hazır")

    # ------------------------------------------------------------------ #
    # LOG
    # ------------------------------------------------------------------ #

    def log_command(
        self,
        command: str,
        chat_id: int,
        user_input: str,
        response: str,
        duration_ms: float,
        status: str = "success",  # success | error | timeout
        error: Optional[str] = None,
    ):
        """Her komutu logla."""
        entry = {
            "ts": datetime.now().isoformat(),
            "command": command,
            "chat_id": str(chat_id),
            "input_len": len(user_input),
            "response_len": len(response),
            "duration_ms": round(duration_ms, 1),
            "status": status,
            "error": error,
        }
        try:
            with open(self.conv_log, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            log.error(f"Log yazma hatası: {e}")

    # ------------------------------------------------------------------ #
    # ANALİZ
    # ------------------------------------------------------------------ #

    def analyze(self, limit: int = 200) -> str:
        """Son N konuşmayı Ollama ile analiz et. Öğrenilen pattern'leri döndür."""
        entries = self._read_recent(limit)
        if not entries:
            return "Henüz yeterli veri yok."

        # İstatistik hesapla
        stats = self._compute_stats(entries)

        # Ollama'ya gönder
        prompt = self._build_analysis_prompt(stats, entries[-20:])
        try:
            insight = self.call_ollama(
                "llama3.2:latest",
                [{"role": "user", "content": prompt}],
                system="Sen Jarvis'in öz-öğrenme analistisin. Türkçe yaz. Kısa ve öz ol.",
                max_tokens=400,
            )
        except Exception as e:
            log.error(f"Ollama analiz hatası: {e}")
            insight = f"Analiz yapılamadı: {e}"

        # Kaydet
        self._save_insight(insight, stats)
        return insight

    def get_last_insight(self) -> str:
        """Son kaydedilen insight'ı döndür."""
        if not self.insights_file.exists():
            return "Henüz analiz yapılmadı. `/ogren` komutunu çalıştır."
        return self.insights_file.read_text(encoding="utf-8")

    # ------------------------------------------------------------------ #
    # İÇ METODLAR
    # ------------------------------------------------------------------ #

    def _read_recent(self, limit: int) -> list:
        if not self.conv_log.exists():
            return []
        try:
            lines = self.conv_log.read_text(encoding="utf-8").splitlines()
            entries = []
            for line in lines[-limit:]:
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
            return entries
        except Exception as e:
            log.error(f"Log okuma hatası: {e}")
            return []

    def _compute_stats(self, entries: list) -> dict:
        command_counts = {}
        command_errors = {}
        command_durations = {}
        total = len(entries)
        errors = 0

        for e in entries:
            cmd = e.get("command", "unknown")
            command_counts[cmd] = command_counts.get(cmd, 0) + 1
            if e.get("status") != "success":
                errors += 1
                command_errors[cmd] = command_errors.get(cmd, 0) + 1
            dur = e.get("duration_ms", 0)
            if cmd not in command_durations:
                command_durations[cmd] = []
            command_durations[cmd].append(dur)

        # Ortalama süre
        avg_durations = {
            cmd: round(sum(durs) / len(durs))
            for cmd, durs in command_durations.items()
        }

        # En çok kullanılan 5
        top_commands = sorted(command_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        # En çok hata veren 3
        top_errors = sorted(command_errors.items(), key=lambda x: x[1], reverse=True)[:3]

        return {
            "total": total,
            "error_rate": round(errors / total * 100, 1) if total > 0 else 0,
            "top_commands": top_commands,
            "top_errors": top_errors,
            "avg_durations_ms": avg_durations,
        }

    def _build_analysis_prompt(self, stats: dict, recent: list) -> str:
        recent_cmds = [f"- {e['command']} ({e['status']}, {e['duration_ms']}ms)" for e in recent]
        return f"""Jarvis bot kullanım istatistikleri:

GENEL:
- Toplam komut: {stats['total']}
- Hata oranı: {stats['error_rate']}%

EN ÇOK KULLANILAN KOMUTLAR:
{chr(10).join([f"- {cmd}: {cnt} kez" for cmd, cnt in stats['top_commands']])}

EN ÇOK HATA VEREN KOMUTLAR:
{chr(10).join([f"- {cmd}: {cnt} hata" for cmd, cnt in stats['top_errors']]) if stats['top_errors'] else "- Hata yok"}

SON 20 KOMUT:
{chr(10).join(recent_cmds)}

Analiz et:
1. Kullanıcı en çok ne istiyor?
2. Hangi komutlar sorunlu, neden?
3. Jarvis neyi öğrenmeli veya iyileştirmeli?
4. 2-3 somut öneri yaz."""

    def _save_insight(self, insight: str, stats: dict):
        """Insight'ı hem insights.md hem wiki/hot.md'ye yaz."""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M")

        # insights.md
        content = f"""# Jarvis Öğrenme Raporu — {ts}

## İstatistikler
- Toplam komut: {stats['total']}
- Hata oranı: {stats['error_rate']}%
- En çok kullanılan: {', '.join([c[0] for c in stats['top_commands'][:3]])}

## Analiz
{insight}

---
"""
        try:
            existing = ""
            if self.insights_file.exists():
                existing = self.insights_file.read_text(encoding="utf-8")
            self.insights_file.write_text(content + existing, encoding="utf-8")
        except Exception as e:
            log.error(f"Insight kaydetme hatası: {e}")

        # wiki/hot.md güncelle
        self._update_wiki_hot(insight, ts, stats)

    def _update_wiki_hot(self, insight: str, ts: str, stats: dict):
        """wiki/hot.md'nin başına öğrenme özetini ekle."""
        if not self.wiki_hot.exists():
            return
        try:
            existing = self.wiki_hot.read_text(encoding="utf-8")
            learning_section = f"""## Son Öğrenme — {ts}
- Komut sayısı: {stats['total']} | Hata: {stats['error_rate']}%
- {insight[:300].replace(chr(10), ' ')}...

"""
            # "## Son Güncelleme" satırından önce ekle
            if "## Son Güncelleme" in existing:
                updated = existing.replace(
                    "## Son Güncelleme",
                    learning_section + "## Son Güncelleme"
                )
            else:
                updated = learning_section + existing

            self.wiki_hot.write_text(updated, encoding="utf-8")
        except Exception as e:
            log.error(f"Wiki hot.md güncelleme hatası: {e}")
