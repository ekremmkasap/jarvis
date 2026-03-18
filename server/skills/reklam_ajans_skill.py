#!/usr/bin/env python3
"""
REKLAM AJANS SKILL - Holding Departmani
Brief -> Konsept + Gorsel Prompt + Reklam Kopyasi (3 varyant)
Kullanim: /reklam_ajans [brief]
"""
import sqlite3
from datetime import datetime
from pathlib import Path

# skills/ -> server/ -> jarvis-mission-control/ (ROOT)
ROOT_DIR    = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = ROOT_DIR / "holding_merkezi" / "outputs"
DB_PATH     = ROOT_DIR / "memory" / "holding.db"


def _ensure_dirs():
    for d in [OUTPUTS_DIR, DB_PATH.parent]:
        d.mkdir(parents=True, exist_ok=True)


def init_holding_db():
    _ensure_dirs()
    with sqlite3.connect(str(DB_PATH)) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS reklam_projeleri (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       TEXT NOT NULL,
            brief         TEXT NOT NULL,
            konsept       TEXT,
            gorsel_prompt TEXT,
            kopya_1       TEXT,
            kopya_2       TEXT,
            kopya_3       TEXT,
            durum         TEXT DEFAULT 'taslak',
            created_at    REAL DEFAULT (strftime('%s','now'))
        );
        """)


class ReklamAjansSkill:
    def __init__(self, call_ollama_fn):
        self.call_ollama = call_ollama_fn
        init_holding_db()

    def run(self, user_id: str, brief: str) -> str:
        brief = brief.strip()
        if not brief:
            return (
                "*Reklam Ajansi*\n\n"
                "Kullanim: `/reklam_ajans [brief]`\n"
                "Ornek: `/reklam_ajans handmade yun bere, hedef: 25-40 kadin, platform: Instagram`"
            )

        # ADIM 1: Konsept
        konsept = self.call_ollama(
            "llama3.2:latest",
            [{"role": "user", "content": (
                f"Brief: {brief}\n\n"
                "Reklam konsepti olustur:\n"
                "1. Hedef Kitle: (kim, yas, ihtiyac)\n"
                "2. Ana Mesaj: (tek cumle)\n"
                "3. Marka Sesi: (samimi/luks/eglenceli/guvenilir)\n"
                "4. Hook Fikri: (ilk 3 saniye)\n"
                "Kisa ve net. Turkce."
            )}],
            "Kademli reklam stratejistisin. Sadece Turkce.",
            max_tokens=200, num_ctx=512
        )

        # ADIM 2: Gorsel Prompt
        gorsel_prompt = self.call_ollama(
            "llama3.2:latest",
            [{"role": "user", "content": (
                f"Brief: {brief}\nKonsept: {konsept[:300]}\n\n"
                "Bu reklam icin Ingilizce Midjourney prompt yaz.\n"
                "Format: [konu], [stil], [isik], [atmosfer], --ar 4:5 --v 6\n"
                "Sadece prompt, aciklama yok."
            )}],
            "Visual art director for advertising. Output only the prompt.",
            max_tokens=120, num_ctx=512
        )

        # ADIM 3: 3 Kopya
        kopya_raw = self.call_ollama(
            "llama3.2:latest",
            [{"role": "user", "content": (
                f"Brief: {brief}\nKonsept: {konsept[:200]}\n\n"
                "3 farkli reklam kopyasi yaz (her biri max 2 cumle):\n"
                "A) Duygusal: kalbi hedef al\n"
                "B) Rasyonel: faydayi vurgula\n"
                "C) FOMO: aciliyet yarat\n"
                "Format:\nA) ...\nB) ...\nC) ..."
            )}],
            "Kademli reklam metin yazarisin. Kisa, etkili, Turkce.",
            max_tokens=200, num_ctx=512
        )

        # Kopyalari parse et
        kopya_1 = kopya_2 = kopya_3 = ""
        for line in kopya_raw.split("\n"):
            line = line.strip()
            if line.startswith("A)"):
                kopya_1 = line[2:].strip()
            elif line.startswith("B)"):
                kopya_2 = line[2:].strip()
            elif line.startswith("C)"):
                kopya_3 = line[2:].strip()

        # DB kaydet
        with sqlite3.connect(str(DB_PATH)) as db:
            db.execute(
                "INSERT INTO reklam_projeleri "
                "(user_id, brief, konsept, gorsel_prompt, kopya_1, kopya_2, kopya_3) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (user_id, brief, konsept, gorsel_prompt, kopya_1, kopya_2, kopya_3)
            )

        # Dosyaya kaydet
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            out_file = OUTPUTS_DIR / f"reklam_{ts}.txt"
            out_file.write_text(
                f"BRIEF:\n{brief}\n\nKONSEPT:\n{konsept}\n\n"
                f"GORSEL PROMPT:\n{gorsel_prompt}\n\n"
                f"KOPYA A:\n{kopya_1}\n\nKOPYA B:\n{kopya_2}\n\nKOPYA C:\n{kopya_3}\n",
                encoding="utf-8"
            )
            dosya_notu = f"_Kaydedildi: outputs/reklam_{ts}.txt_"
        except Exception:
            dosya_notu = ""

        return (
            f"*Reklam Ajansi - Kampanya Taslagi*\n\n"
            f"*Konsept:*\n{konsept}\n\n"
            f"*Gorsel Prompt (Midjourney):*\n`{gorsel_prompt}`\n\n"
            f"*A) Duygusal:*\n{kopya_1}\n\n"
            f"*B) Rasyonel:*\n{kopya_2}\n\n"
            f"*C) FOMO:*\n{kopya_3}\n\n"
            f"{dosya_notu}"
        )
