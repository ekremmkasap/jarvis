#!/usr/bin/env python3
"""
CONTENT FACTORY AGENT -- Dan Koe Protokolu
Tek girdi (Newsletter) -> Cok platform cikti
X Thread + LinkedIn + YouTube Shorts Script
RAG + Swipe File + AI Mulakati

Kullanim: /agent content-factory (Telegram)
"""
import sqlite3, json, os, time, asyncio, random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

DB_PATH = "/opt/jarvis/memory/content_factory.db"
PROMPT_DIR = "/opt/jarvis/skills/content_prompts"


# --- VERITABANI KURULUMU -----------------------------------------------------

def init_content_db():
    """Swipe File + Prompt Library + Mulakat gecmisi tablolari"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with sqlite3.connect(DB_PATH) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS swipe_file (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            platform    TEXT NOT NULL,
            style       TEXT NOT NULL,
            hook        TEXT NOT NULL,
            content     TEXT NOT NULL,
            performance TEXT DEFAULT 'unknown',
            format_type TEXT DEFAULT 'new',
            tags        TEXT,
            created_at  REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS prompt_library (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL UNIQUE,
            platform     TEXT NOT NULL,
            style        TEXT NOT NULL,
            template     TEXT NOT NULL,
            success_rate REAL DEFAULT 0.0,
            usage_count  INTEGER DEFAULT 0,
            last_used    REAL
        );

        CREATE TABLE IF NOT EXISTS interview_sessions (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL,
            newsletter      TEXT,
            target_audience TEXT,
            has_story       TEXT,
            emotion_trigger TEXT,
            raw_context     TEXT,
            created_at      REAL DEFAULT (strftime('%s','now'))
        );

        CREATE TABLE IF NOT EXISTS generated_content (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id  INTEGER REFERENCES interview_sessions(id),
            platform    TEXT NOT NULL,
            content     TEXT NOT NULL,
            prompt_used TEXT,
            created_at  REAL DEFAULT (strftime('%s','now'))
        );

        CREATE INDEX IF NOT EXISTS idx_swipe_platform ON swipe_file(platform, performance);
        CREATE INDEX IF NOT EXISTS idx_prompt_platform ON prompt_library(platform, success_rate);
        """)
    _seed_prompt_library()
    return True


def _seed_prompt_library():
    """Temel prompt sablonlarini yukle"""
    prompts = [
        {
            "name": "x_patient_observer",
            "platform": "x_thread",
            "style": "patient_observer",
            "template": "Herkes {konu} hakkinda yanlis biliyor.\nBen 3 yil izledim.\n\n{bullet_points}\n\nSonuc: {paradox}\n\n(Devami gelecek)"
        },
        {
            "name": "x_quiet_devastator",
            "platform": "x_thread",
            "style": "quiet_devastator",
            "template": "{stat_veya_gercek}\n\nBu sizi rahatsiz etmeli.\n\nNeden:\n{nedenler}\n\nCozum degil. Gercek."
        },
        {
            "name": "x_dramatic_profit",
            "platform": "x_thread",
            "style": "dramatic_profit",
            "template": "{sayi} gunde {sonuc}.\n\nFormul: {formul}\n\nAdimlar:\n{adimlar}\n\nSiz de yapabilirsiniz."
        },
        {
            "name": "linkedin_contrast",
            "platform": "linkedin",
            "style": "contrast",
            "template": "Herkes {yanlis_inanc} der.\n\nBen once inanirdim.\n\nSonra {donusum_ani} oldu.\n\nSimdi {yeni_perspektif}.\n\nNe dusunuyorsunuz?"
        },
        {
            "name": "linkedin_paradox",
            "platform": "linkedin",
            "style": "paradox",
            "template": "Ne kadar cok {eylem}, o kadar az {beklenen_sonuc}.\n\nParadoks: {paradoks_aciklama}\n\nBenim yaklasimim: {cozum}\n\n#{etiket1} #{etiket2}"
        },
        {
            "name": "youtube_hook_story",
            "platform": "youtube_shorts",
            "style": "story",
            "template": "[HOOK - 3 saniye] {dikkat_ceken}\n\n[PROBLEM] {izleyici_acisi}\n\n[DONUSUM] {hikaye}\n\n[CTA] {cagri}"
        },
    ]
    with sqlite3.connect(DB_PATH) as db:
        for p in prompts:
            db.execute(
                """INSERT OR IGNORE INTO prompt_library (name, platform, style, template)
                   VALUES (:name, :platform, :style, :template)""",
                p
            )


# --- RAG: SWIPE FILE ----------------------------------------------------------

def get_best_prompt(platform: str) -> dict:
    """
    %33 Proven Formats: En yuksek basarisiz promptu sec
    %67 New Formats: Dusuk kullanim sayili promptu sec
    """
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        if random.random() < 0.33:
            row = db.execute(
                "SELECT * FROM prompt_library WHERE platform=? "
                "ORDER BY success_rate DESC, usage_count DESC LIMIT 1",
                (platform,)
            ).fetchone()
        else:
            row = db.execute(
                "SELECT * FROM prompt_library WHERE platform=? "
                "ORDER BY usage_count ASC, RANDOM() LIMIT 1",
                (platform,)
            ).fetchone()
        return dict(row) if row else {}


def get_swipe_examples(platform: str, limit: int = 2) -> str:
    """RAG: Platform icin en iyi ornekleri getir"""
    with sqlite3.connect(DB_PATH) as db:
        db.row_factory = sqlite3.Row
        rows = db.execute(
            "SELECT hook, content FROM swipe_file "
            "WHERE platform=? AND performance IN ('viral','good') "
            "ORDER BY RANDOM() LIMIT ?",
            (platform, limit)
        ).fetchall()
    if not rows:
        return ""
    examples = []
    for i, r in enumerate(rows, 1):
        examples.append(f"ORNEK {i}:\nKanca: {r['hook']}\nIcerik: {r['content'][:200]}...")
    return "\n\n".join(examples)


def save_content_to_swipe(platform: str, style: str, hook: str,
                          content: str, performance: str = "test"):
    """Uretilen icerigi swipe file'a kaydet"""
    with sqlite3.connect(DB_PATH) as db:
        db.execute(
            "INSERT INTO swipe_file (platform, style, hook, content, performance) VALUES (?,?,?,?,?)",
            (platform, style, hook, content, performance)
        )


def update_prompt_success(prompt_name: str, success: bool):
    """Prompt basari oranini guncelle"""
    with sqlite3.connect(DB_PATH) as db:
        row = db.execute(
            "SELECT success_rate, usage_count FROM prompt_library WHERE name=?",
            (prompt_name,)
        ).fetchone()
        if row:
            old_rate, count = row
            new_count = count + 1
            new_rate = ((old_rate * count) + (1.0 if success else 0.0)) / new_count
            db.execute(
                "UPDATE prompt_library SET success_rate=?, usage_count=?, last_used=? WHERE name=?",
                (new_rate, new_count, time.time(), prompt_name)
            )


# --- AI MULAKATI --------------------------------------------------------------

class ContentInterviewer:
    """
    Kullaniciyi mulakata ceker, ham Newsletter'i zenginlestirir.
    Durum: WAITING_NEWSLETTER -> WAITING_AUDIENCE -> WAITING_STORY
           -> WAITING_EMOTION -> READY
    """
    QUESTIONS = {
        "WAITING_NEWSLETTER": (
            "*Content Factory aktif!*\n\n"
            "Newsletter veya ana fikrinizi yazin:\n"
            "_(Ham, taslak, notlar -- ne olursa olsun)_"
        ),
        "WAITING_AUDIENCE": (
            "Harika!\n\n"
            "*Soru 1:* Bu icerik kime hitap ediyor?\n"
            "_(Ornek: 25-40 yas, e-ticaret yapan girisimciler)_"
        ),
        "WAITING_STORY": (
            "*Soru 2:* Bu konuyla ilgili kisisel bir hikayen var mi?\n"
            "_(Basarili/basarisiz deney, ders, donusum ani)_\n"
            "Yoksa 'hayir' yaz."
        ),
        "WAITING_EMOTION": (
            "*Soru 3:* Okuyucuda hangi duyguyu tetiklemek istiyorsun?\n"
            "1 - Aciyi hatirlatmak (Pain point)\n"
            "2 - Paradoks / Sasirtmak\n"
            "3 - Umut / Donus hikayesi\n"
            "4 - Kiskandirmak / Ispatlamak\n"
            "Sayi yaz: 1, 2, 3 veya 4"
        ),
    }

    EMOTION_MAP = {
        "1": "pain_point",
        "2": "paradox",
        "3": "transformation",
        "4": "aspiration",
    }

    def __init__(self):
        self._sessions = {}

    def get_state(self, user_id: str) -> str:
        return self._sessions.get(user_id, {}).get("state", "WAITING_NEWSLETTER")

    def is_active(self, user_id: str) -> bool:
        return user_id in self._sessions

    def start(self, user_id: str) -> str:
        self._sessions[user_id] = {"state": "WAITING_NEWSLETTER", "data": {}}
        return self.QUESTIONS["WAITING_NEWSLETTER"]

    def process(self, user_id: str, text: str) -> tuple:
        """
        Kullanicinin cevabini isle.
        Returns: (response_text, is_ready, context_dict)
        """
        if user_id not in self._sessions:
            self.start(user_id)

        session = self._sessions[user_id]
        state = session["state"]
        data = session["data"]

        if state == "WAITING_NEWSLETTER":
            data["newsletter"] = text
            session["state"] = "WAITING_AUDIENCE"
            return self.QUESTIONS["WAITING_AUDIENCE"], False, {}

        elif state == "WAITING_AUDIENCE":
            data["target_audience"] = text
            session["state"] = "WAITING_STORY"
            return self.QUESTIONS["WAITING_STORY"], False, {}

        elif state == "WAITING_STORY":
            data["story"] = None if text.lower() in ["hayir", "yok", "no"] else text
            session["state"] = "WAITING_EMOTION"
            return self.QUESTIONS["WAITING_EMOTION"], False, {}

        elif state == "WAITING_EMOTION":
            data["emotion"] = self.EMOTION_MAP.get(text.strip(), "paradox")
            session["state"] = "READY"
            context = dict(data)
            self._save_session(user_id, context)
            summary = (
                "*Mulakat tamamlandi!*\n\n"
                f"Hedef: {data['target_audience']}\n"
                f"Duygu: {data['emotion']}\n"
                f"Hikaye: {'VAR' if data.get('story') else 'YOK'}\n\n"
                "_Icerikler uretiliyor... (X, LinkedIn, YouTube)_"
            )
            del self._sessions[user_id]
            return summary, True, context

        return "Bilinmeyen durum.", False, {}

    def _save_session(self, user_id: str, data: dict):
        with sqlite3.connect(DB_PATH) as db:
            db.execute(
                """INSERT INTO interview_sessions
                   (user_id, newsletter, target_audience, has_story, emotion_trigger, raw_context)
                   VALUES (?,?,?,?,?,?)""",
                (
                    str(user_id),
                    data.get("newsletter", ""),
                    data.get("target_audience", ""),
                    str(bool(data.get("story"))),
                    data.get("emotion", ""),
                    json.dumps(data, ensure_ascii=False)
                )
            )


# --- CONTENT MULTIPLIER -------------------------------------------------------

class ContentMultiplier:
    """
    Asenkron icerik uretici.
    Tek Newsletter -> X Thread + 2x LinkedIn + YouTube Shorts Script
    """

    EMOTION_INSTRUCTIONS = {
        "pain_point": "Okuyucunun acisina dokunarak yaz. Empati kur.",
        "paradox": "Beklentilerin tersini soyleyerek basla. Zit gerceklerle sok.",
        "transformation": "Donusum hikayesini anlat. Once kotu, sonra iyi. Umut ver.",
        "aspiration": "Basariya dair somut sayilar ve ispatlar kullan.",
    }

    def __init__(self, ollama_func):
        self.call_ollama = ollama_func
        self.executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="content_worker")

    def _build_system(self, platform: str, style: str, context: dict, examples: str) -> str:
        audience = context.get("target_audience", "girisimciler")
        emotion = context.get("emotion", "paradox")
        story = context.get("story")
        emotion_inst = self.EMOTION_INSTRUCTIONS.get(emotion, "")

        system = (
            f"Sen uzman bir {platform} icerik yazarisin. Dan Koe yaklasimini kullaniyorsun.\n"
            f"Platform: {platform.upper()}\n"
            f"Hedef Kitle: {audience}\n"
            f"Duygu Tetikleyici: {emotion_inst}\n"
            f"Stil: {style}\n\n"
            "KURALLAR:\n"
            "- Ilk cumle KANCA olmali: Durdurucu, merak uyandirici\n"
            "- Uzun paragraflar YASAK: Her fikir max 2-3 satir\n"
            "- Samimi, dogal Turkce: Robotik dil YASAK\n"
            "- Sonunda mutlaka etkilesilim (soru / CTA / devam merak)\n"
        )
        if story:
            system += f"\nKISISEL HIKAYE EKLE: {story[:200]}\n"
        if examples:
            system += f"\nBASARILI ORNEKLER (referans):\n{examples}\n"
        return system

    def _generate_x_thread(self, context: dict) -> str:
        prompt_data = get_best_prompt("x_thread")
        style = prompt_data.get("style", "patient_observer")
        template = prompt_data.get("template", "")
        examples = get_swipe_examples("x_thread")
        system = self._build_system("x_thread", style, context, examples)
        messages = [{
            "role": "user",
            "content": (
                f"Newsletter:\n{context['newsletter'][:800]}\n\n"
                f"Yukaridaki newsletter'dan bir X Thread yaz.\n"
                f"Sablon (referans):\n{template[:300]}\n\n"
                "Thread formati:\n"
                "- Tweet 1: Kanca (max 280 karakter)\n"
                "- Tweet 2-5: Her biri ayri bir fikir\n"
                "- Son tweet: Sonuc + CTA\n\n"
                "SADECE thread metnini yaz."
            )
        }]
        result = self.call_ollama("llama3.2:latest", messages, system, max_tokens=400, num_ctx=1024)
        if prompt_data.get("name"):
            update_prompt_success(prompt_data["name"], len(result) > 100)
        return result

    def _generate_linkedin(self, context: dict, variant: int) -> str:
        styles = ["contrast", "paradox"]
        style = styles[variant % len(styles)]
        prompt_data = get_best_prompt("linkedin")
        examples = get_swipe_examples("linkedin")
        system = self._build_system("linkedin", style, context, examples)
        messages = [{
            "role": "user",
            "content": (
                f"Newsletter:\n{context['newsletter'][:800]}\n\n"
                f"LinkedIn postu yaz ({style.upper()} tarz).\n"
                "- Max 1500 karakter\n"
                "- Paragraflar kisa\n"
                "- Sonunda bir soru sor\n\n"
                "SADECE post metnini yaz."
            )
        }]
        return self.call_ollama("llama3.2:latest", messages, system, max_tokens=350, num_ctx=1024)

    def _generate_youtube_shorts(self, context: dict) -> str:
        prompt_data = get_best_prompt("youtube_shorts")
        examples = get_swipe_examples("youtube_shorts")
        system = self._build_system("youtube_shorts", "story", context, examples)
        messages = [{
            "role": "user",
            "content": (
                f"Newsletter:\n{context['newsletter'][:800]}\n\n"
                "YouTube Shorts scripti yaz (max 60 saniye = ~150 kelime).\n"
                "Format:\n"
                "[KANCA - 0-3 sn]: ...\n"
                "[PROBLEM - 3-15 sn]: ...\n"
                "[COZUM/HIKAYE - 15-50 sn]: ...\n"
                "[CTA - 50-60 sn]: ...\n\n"
                "SADECE script yaz."
            )
        }]
        return self.call_ollama("llama3.2:latest", messages, system, max_tokens=300, num_ctx=1024)

    def multiply(self, context: dict) -> dict:
        """ThreadPoolExecutor ile 4 platform paralel uretim"""
        futures = {
            "x_thread":       self.executor.submit(self._generate_x_thread, context),
            "linkedin_1":     self.executor.submit(self._generate_linkedin, context, 0),
            "linkedin_2":     self.executor.submit(self._generate_linkedin, context, 1),
            "youtube_shorts": self.executor.submit(self._generate_youtube_shorts, context),
        }
        results = {}
        for platform, future in futures.items():
            try:
                results[platform] = future.result(timeout=180)
            except Exception as e:
                results[platform] = f"Hata: {e}"
        return results


def format_output(results: dict) -> str:
    """Uretilen icerikleri Telegram formatinda duzenle"""
    labels = {
        "x_thread":       "X THREAD",
        "linkedin_1":     "LINKEDIN 1 (Karsilastirma)",
        "linkedin_2":     "LINKEDIN 2 (Paradoks)",
        "youtube_shorts": "YOUTUBE SHORTS SCRIPT",
    }
    parts = ["*CONTENT FACTORY -- CIKTI*\n"]
    for key, content in results.items():
        label = labels.get(key, key.upper())
        separator = "-" * 30
        parts.append(f"\n*{label}*\n{separator}\n{content}\n")
    return "\n".join(parts)


# --- SINGLETON INSTANCES ------------------------------------------------------

_interviewer = ContentInterviewer()
_multiplier = None


def get_interviewer() -> ContentInterviewer:
    return _interviewer


def get_multiplier(call_ollama_func) -> "ContentMultiplier":
    global _multiplier
    if _multiplier is None:
        _multiplier = ContentMultiplier(call_ollama_func)
    return _multiplier


if __name__ == "__main__":
    init_content_db()
    print("Content Factory DB kuruldu:", DB_PATH)
    print("Prompt library:")
    with sqlite3.connect(DB_PATH) as db:
        for row in db.execute("SELECT name, platform FROM prompt_library"):
            print(f"  - {row[0]} ({row[1]})")
