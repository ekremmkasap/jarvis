#!/usr/bin/env python3
"""
WEB AJANS SKILL - Holding Departmani
Brief -> Tek sayfalik HTML/Tailwind landing page
Kullanim: /websitesi [brief]
"""
import json as _json
import sqlite3
from datetime import datetime
from pathlib import Path

ROOT_DIR    = Path(__file__).resolve().parents[2]
OUTPUTS_DIR = ROOT_DIR / "holding_merkezi" / "outputs"
DB_PATH     = ROOT_DIR / "memory" / "holding.db"


def _ensure_dirs():
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def init_web_db():
    _ensure_dirs()
    with sqlite3.connect(str(DB_PATH)) as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS web_projeleri (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    TEXT NOT NULL,
            brief      TEXT NOT NULL,
            html_kod   TEXT,
            created_at REAL DEFAULT (strftime('%s','now'))
        );
        """)


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{baslik}</title>
<script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 font-sans">
<section class="bg-gradient-to-r from-blue-600 to-purple-700 text-white py-20 px-6 text-center">
  <div class="max-w-3xl mx-auto">
    <h1 class="text-4xl md:text-5xl font-bold mb-4">{hero_baslik}</h1>
    <p class="text-xl mb-8 opacity-90">{hero_altyazi}</p>
    <a href="#iletisim" class="bg-white text-blue-600 font-bold py-3 px-8 rounded-full text-lg hover:shadow-lg transition">{cta_text}</a>
  </div>
</section>
<section class="py-16 px-6">
  <div class="max-w-5xl mx-auto">
    <h2 class="text-3xl font-bold text-center text-gray-800 mb-12">{faydalar_baslik}</h2>
    <div class="grid md:grid-cols-3 gap-8">
      <div class="bg-white rounded-xl shadow p-6 text-center">
        <div class="text-4xl mb-4">&#10003;</div>
        <h3 class="font-bold text-lg mb-2">{fayda_1_baslik}</h3>
        <p class="text-gray-600">{fayda_1_aciklama}</p>
      </div>
      <div class="bg-white rounded-xl shadow p-6 text-center">
        <div class="text-4xl mb-4">&#10003;</div>
        <h3 class="font-bold text-lg mb-2">{fayda_2_baslik}</h3>
        <p class="text-gray-600">{fayda_2_aciklama}</p>
      </div>
      <div class="bg-white rounded-xl shadow p-6 text-center">
        <div class="text-4xl mb-4">&#10003;</div>
        <h3 class="font-bold text-lg mb-2">{fayda_3_baslik}</h3>
        <p class="text-gray-600">{fayda_3_aciklama}</p>
      </div>
    </div>
  </div>
</section>
<section class="bg-gray-100 py-16 px-6">
  <div class="max-w-4xl mx-auto text-center">
    <h2 class="text-3xl font-bold text-gray-800 mb-8">{musteri_baslik}</h2>
    <div class="bg-white rounded-xl shadow p-8 max-w-2xl mx-auto">
      <p class="text-gray-700 text-lg italic mb-4">"{yorum_1}"</p>
      <p class="font-bold text-blue-600">{yorum_1_kisi}</p>
    </div>
  </div>
</section>
<section id="iletisim" class="py-16 px-6 bg-blue-600 text-white text-center">
  <div class="max-w-2xl mx-auto">
    <h2 class="text-3xl font-bold mb-4">{final_cta_baslik}</h2>
    <p class="text-xl mb-8 opacity-90">{final_cta_aciklama}</p>
    <a href="https://wa.me/90XXXXXXXXXX" class="bg-white text-blue-600 font-bold py-3 px-8 rounded-full text-lg hover:shadow-lg transition inline-block">{final_cta_button}</a>
  </div>
</section>
<footer class="text-center py-6 text-gray-500 text-sm">&copy; 2025 {sirket_adi}</footer>
</body>
</html>"""


class WebAjansSkill:
    def __init__(self, call_ollama_fn):
        self.call_ollama = call_ollama_fn
        init_web_db()

    def run(self, user_id: str, brief: str) -> str:
        brief = brief.strip()
        if not brief:
            return (
                "*Web Ajansi*\n\n"
                "Kullanim: \n"
                "Ornek: "
            )

        icerik_json = self.call_ollama(
            "llama3.2:latest",
            [{"role": "user", "content": (
                "Brief: " + brief + "\n\n"
                "Bu web sitesi icin Turkce icerik uret. SADECE JSON don:\n"
                '{"baslik":"...", "hero_baslik":"...", "hero_altyazi":"...", '
                '"cta_text":"...", "faydalar_baslik":"...", '
                '"fayda_1_baslik":"...", "fayda_1_aciklama":"...", '
                '"fayda_2_baslik":"...", "fayda_2_aciklama":"...", '
                '"fayda_3_baslik":"...", "fayda_3_aciklama":"...", '
                '"musteri_baslik":"...", "yorum_1":"...", "yorum_1_kisi":"...", '
                '"final_cta_baslik":"...", "final_cta_aciklama":"...", '
                '"final_cta_button":"...", "sirket_adi":"..."}'
            )}],
            "Web copywriter ve UX uzmansin. Sadece valid JSON don.",
            max_tokens=400, num_ctx=768
        )

        try:
            raw = icerik_json.strip()
            if "")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            data = _json.loads(raw.strip())
        except Exception:
            data = {
                "baslik": "Profesyonel Hizmet",
                "hero_baslik": brief[:60],
                "hero_altyazi": "Isleteninizi bir ust seviyeye tasiyoruz.",
                "cta_text": "Hemen Baslayalim",
                "faydalar_baslik": "Neden Biz?",
                "fayda_1_baslik": "Uzman Ekip", "fayda_1_aciklama": "Alaninda uzman profesyoneller.",
                "fayda_2_baslik": "Hizli Sonuc", "fayda_2_aciklama": "30 gunde olcumlenebilir sonuclar.",
                "fayda_3_baslik": "Tam Destek", "fayda_3_aciklama": "7/24 iletisim ve raporlama.",
                "musteri_baslik": "Musterilerimiz Ne Diyor?",
                "yorum_1": "Harika bir deneyimdi, kesinlikle tavsiye ederim.",
                "yorum_1_kisi": "Ahmet Y. - Isletme Sahibi",
                "final_cta_baslik": "Hazir misiniz?",
                "final_cta_aciklama": "Ucretsiz danismanlik icin bize ulasin.",
                "final_cta_button": "WhatsApp'tan Yaz",
                "sirket_adi": "Sirketiniz"
            }

        html = HTML_TEMPLATE.format(**data)

        with sqlite3.connect(str(DB_PATH)) as db:
            db.execute(
                "INSERT INTO web_projeleri (user_id, brief, html_kod) VALUES (?, ?, ?)",
                (user_id, brief, html)
            )

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_file = OUTPUTS_DIR / ("website_" + ts + ".html")
        try:
            html_file.write_text(html, encoding="utf-8")
            dosya_notu = "_HTML: outputs/website_" + ts + ".html_"
        except Exception:
            dosya_notu = ""

        return (
            "*Web Ajansi - Landing Page Olusturuldu*\n\n"
            "*Baslik:* " + data.get("baslik", "") + "\n"
            "*Hero:* " + data.get("hero_baslik", "") + "\n"
            "*CTA:* " + data.get("cta_text", "") + "\n\n"
            "*Faydalar:*\n"
            "- " + data.get("fayda_1_baslik","") + ": " + data.get("fayda_1_aciklama","") + "\n"
            "- " + data.get("fayda_2_baslik","") + ": " + data.get("fayda_2_aciklama","") + "\n"
            "- " + data.get("fayda_3_baslik","") + ": " + data.get("fayda_3_aciklama","") + "\n\n"
            + dosya_notu
        )
