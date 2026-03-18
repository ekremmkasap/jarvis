#!/usr/bin/env python3
"""
SATIS DEPARTMANI SKILL - Holding Departmani
4 Sub-Agent pipeline: Arastirmaci + Copywriter + SalesOps + Kapanis
Kullanim: /satis [urun veya hizmet]
"""
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT_DIR    = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = ROOT_DIR / "holding_merkezi" / "outputs"
DB_PATH     = ROOT_DIR / "memory" / "holding.db"


def _ensure_dirs():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_satis_db():
    _ensure_dirs()
    with sqlite3.connect(str(DB_PATH)) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS satis_projeleri (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         TEXT NOT NULL,
            urun            TEXT NOT NULL,
            pazar_analizi   TEXT,
            deger_onerisi   TEXT,
            satis_email     TEXT,
            kapanis_script  TEXT,
            created_at      REAL DEFAULT (strftime('%s','now'))
        );
        """)


class SatisDepartmani:
    """
    4 sub-agent sirali pipeline:
      1. Arastirmaci  -> pazar + acı noktaları analizi
      2. Copywriter   -> değer önerisi + USP
      3. SalesOps     -> soğuk e-posta taslağı
      4. Kapanış Uzmanı -> telefon/DM kapanış scripti
    """

    def __init__(self, call_ollama_fn):
        self.call_ollama = call_ollama_fn
        init_satis_db()

    def run(self, user_id: str, urun: str) -> str:
        urun = urun.strip()
        if not urun:
            return (
                "*Satis Departmani*\n\n"
                "Kullanim: `/satis [urun veya hizmet]`\n"
                "Ornek: `/satis sosyal medya yonetimi paketi, aylik 3500TL`"
            )

        # AGENT 1: Arastirmaci
        pazar = self.call_ollama(
            "llama3.2:latest",
            [{"role": "user", "content": (
                f"Urun/Hizmet: {urun}\n\n"
                "Pazar analizi yap:\n"
                "- Hedef musteri kim? (3 profil)\n"
                "- En buyuk aci noktasi nedir?\n"
                "- Rakipler ne yapiyor?\n"
                "- Fiyat duyarliligi nasil?\n"
                "Kisa, Turkce."
            )}],
            "Pazar arastirmacisisin. Gercekci, veri odakli. Sadece Turkce.",
            max_tokens=200, num_ctx=512
        )

        # AGENT 2: Copywriter - Deger Onerisi
        deger = self.call_ollama(
            "llama3.2:latest",
            [{"role": "user", "content": (
                f"Urun: {urun}\nPazar analizi: {pazar[:300]}\n\n"
                "Satis copywriting yaz:\n"
                "- USP (benzersiz satis onerimiz): 1 guclu cumle\n"
                "- Fayda listesi: 3 madde (rakamla destekle)\n"
                "- Sosyal kanit acisi: nasil konusuriz?\n"
                "Kisa, ikna edici, Turkce."
            )}],
            "Kıdemli satis metin yazarisin. Dönüşüm odakli. Sadece Turkce.",
            max_tokens=200, num_ctx=512
        )

        # AGENT 3: SalesOps - Soguk E-posta
        email = self.call_ollama(
            "llama3.2:latest",
            [{"role": "user", "content": (
                f"Urun: {urun}\nDeger onerisi: {deger[:200]}\n\n"
                "Soguk e-posta taslagi yaz (max 5 satir):\n"
                "- Konu satirı: dikkat cekici\n"
                "- Giris: kisisel, aci noktasi\n"
                "- Teklif: net, risksiz\n"
                "- CTA: tek net adim\n"
                "Format:\nKonu: ...\n---\n[email metni]"
            )}],
            "B2B satis uzmanisin. Kisa email'ler yaz. Sadece Turkce.",
            max_tokens=180, num_ctx=512
        )

        # AGENT 4: Kapanis Scripti
        kapanis = self.call_ollama(
            "llama3.2:latest",
            [{"role": "user", "content": (
                f"Urun: {urun}\nDeger: {deger[:150]}\n\n"
                "DM/telefon kapanis scripti yaz:\n"
                "- Itiraz: 'pahali' -> cevap\n"
                "- Itiraz: 'dusuneyim' -> cevap\n"
                "- Son kapanis cumlesi\n"
                "Her itiraz icin 1-2 cumle. Turkce."
            )}],
            "Kapanis uzmanisin. Yumusak ama ikna edici. Sadece Turkce.",
            max_tokens=180, num_ctx=512
        )

        # DB kaydet
        with sqlite3.connect(str(DB_PATH)) as db:
            db.execute(
                "INSERT INTO satis_projeleri "
                "(user_id, urun, pazar_analizi, deger_onerisi, satis_email, kapanis_script) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, urun, pazar, deger, email, kapanis)
            )

        # Dosya kaydet
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            out = OUTPUTS_DIR / f"satis_{ts}.txt"
            out.write_text(
                f"URUN: {urun}\n\nPAZAR ANALIZI:\n{pazar}\n\n"
                f"DEGER ONERISI:\n{deger}\n\nSOGUK EMAIL:\n{email}\n\n"
                f"KAPANIS SCRIPT:\n{kapanis}\n",
                encoding="utf-8"
            )
            dosya_notu = f"_Kaydedildi: outputs/satis_{ts}.txt_"
        except Exception:
            dosya_notu = ""

        return (
            f"*Satis Departmani - 4 Agent Analizi*\n\n"
            f"*Pazar Analizi:*\n{pazar}\n\n"
            f"*Deger Onerisi & USP:*\n{deger}\n\n"
            f"*Soguk E-posta:*\n{email}\n\n"
            f"*Kapanis Scripti:*\n{kapanis}\n\n"
            f"{dosya_notu}"
        )
