# Codex Reel Analysis 031-065 Batch Spec

**Dil:** Turkce  
**Rol:** Block B - Buse/Eren / spark  
**Tarih:** 2026-04-15  
**Girdi CSV:** `outputs/batch_handles_031_065.csv`  
**Birincil veri kaynagi:** `instagram_analysis.json`  
**Ek kaynak:** `temp_videos/reel-notlari/reel_analiz_log.md`

## Gorev

Reel 031-065 araligindaki 35 Instagram kaydini batch olarak analiz et. Amac, Jarvis Instagram buyumesi icin hangi icerik formatlarinin, CTA kaliplarinin, konumlandirmalarin ve monetizasyon sinyallerinin en iyi calistigini cikarmak.

Canli scrape zorunlu degil. Yerel `instagram_analysis.json` kaydi yeterliyse once yerel analiz yap. Canli Instagram fetch sadece operator acikca izin verirse ve rate-limit/credential durumu uygunsa denenmeli.

## Girdi

CSV kolonlari:

```csv
hesap,platform,reel_no,url,shortcode,not
```

Kurallar:

- `hesap` alaninda `@handle` varsa profil bazli baglam icin kullan.
- `url` ve `shortcode` reel/post kimligi icin canonical kabul edilir.
- `not=metadata_error_owner_missing` olan Reel 056 icin owner bilinmiyor; analizde permalink ve shortcode ile devam et, profil bazli yorum yapma.
- Ayni hesap birden fazla kez gelebilir; duplicate silme. Ornek: `@githubsignals`, `@marc.kaz`, `@codingknowledge`, `@ohmo.ai`.

## Beklenen Cikti

Ana cikti onerilen yol:

```text
outputs/reel_analiz_batch_031_065.json
```

Opsiyonel ozet:

```text
outputs/reel_analiz_batch_031_065_summary.md
```

Ana JSON semasi:

```json
{
  "kapsam": {
    "reel_araligi": "031-065",
    "kaynaklar": [],
    "canli_fetch_yapildi_mi": false
  },
  "varsayimlar": [],
  "ozet": {
    "analiz_edilen_kayit": 35,
    "basarili": 0,
    "eksik_metadata": 0,
    "en_iyi_3_pattern": []
  },
  "comparison_matrix": [
    {
      "pattern": "comment_keyword_lead_magnet",
      "reel_nolari": [],
      "ortalama_engagement_rate_by_views": null,
      "ortalama_comment_like_ratio": null,
      "yorum": ""
    }
  ],
  "top_reels": [
    {
      "rank": 1,
      "reel_no": "061",
      "hesap": "@_eduard.d___",
      "neden": "",
      "jarvis_uyarlamasi": ""
    }
  ],
  "reels": [
    {
      "reel_no": "031",
      "shortcode": "",
      "url": "",
      "hesap": "",
      "format": "reel|post|unknown",
      "caption_ozeti": "",
      "metrikler": {
        "likes": null,
        "comments": null,
        "views": null,
        "total_interactions": null,
        "engagement_rate_by_views": null,
        "comment_like_ratio": null,
        "comment_view_ratio": null,
        "save_rate": null
      },
      "konumlandirma": "open_source|developer_tool|ai_agent|security|creator_economy|turkce_ai|other",
      "cta": {
        "tip": "comment_keyword|link_in_bio|follow_comment|none|unknown",
        "keyword": null,
        "netlik": "dusuk|orta|yuksek|cok_yuksek",
        "cta_proxy_score": 0
      },
      "monetizasyon": {
        "strateji": "lead_magnet|affiliate|sponsored|product_launch|newsletter|community|none|unknown",
        "sinyaller": [],
        "jarvis_firsati": ""
      },
      "jarvis_icin_alinacak_dersler": [],
      "uygulanabilir_fikirler": []
    }
  ]
}
```

## Analiz Kurallari

1. Reel numarasi eslemesi:
   - `instagram_analysis.json` icindeki 11. kayit `Reel 031` kabul edilir.
   - Son kayit `Reel 065` kabul edilir.
   - CSV'deki `shortcode` ile JSON kaydini eslestir; index varsayimina koru olarak dayanma.

2. Metrik hesaplari:
   - `total_interactions = likes + comments`
   - `likes = -1` ise `likes = null` kabul et.
   - `engagement_rate_by_views = (likes + comments) / views`; views yoksa `null`.
   - `comment_like_ratio = comments / likes`; likes yoksa `null`.
   - `comment_view_ratio = comments / views`; views yoksa `null`.
   - `save_rate` kaynakta yoksa `null`.

3. CTA siniflandirma:
   - Caption icinde `comment`, `yorum`, `escribe`, `write`, `follow & comment` gibi ifade varsa comment CTA kabul et.
   - Keyword varsa aynen yakala: ornek `NEXUS`, `AI Agent`, `tarayici`, `STACK`, `Skills`, `graph`, `PYNK`, `repo`, `CLAUDE`, `AGENTS`, `Ai`.
   - Link in bio, GitHub/repo, newsletter, DM, free guide gibi ifadeleri monetizasyon sinyali olarak ayir.

4. Konumlandirma siniflandirma:
   - AI agent / Claude Code / automation / open-source / security / creator economy / Turkish AI / ecommerce gibi ana tema sec.
   - Tek kayit birden fazla tema tasiyorsa birincil tema sec, digerlerini `tags` veya `sinyaller` alanina ekle.

5. Jarvis odakli yorum:
   - Her kayitta Jarvis icin uygulanabilir bir ders yaz.
   - Sadece genel pazarlama yorumu yapma; Jarvis'in mevcut konumuna bagla: local/private agent, voice/hologram, multi-agent, Turkish KOBI, setup guide, DM funnel.

## Oncelikli Incelenecek Kayitlar

- Reel 061 `@_eduard.d___`: 205K views, 10K likes, 13K comments; `CLAUDE` keyword lead magnet.
- Reel 057 `@mr.pynk`: 50K views, 3.9K likes, 11.5K comments; `PYNK` workflow CTA.
- Reel 039 `@brunobracaioli`: 3.381 likes, 3.503 comments; token azaltma pain point'i.
- Reel 049 `@tenfoldmarc`: `graph` keyword; Claude/AI install guide.
- Reel 036 `@isanurdogdu`: Turkce `tarayici` DM CTA; Jarvis Turkce pazar icin kritik.
- Reel 054 `@cicekileteknoloji`: Turkce AI video, 154K views; `KOMUT` CTA.
- Reel 063 `@ohmo.ai`: 260K views; trading bot hikayesi, yuksek reach ama yorum orani dusuk.
- Reel 032 `@allyoucanchi`: Jarvis ismiyle dogrudan rekabet/benchmark.

## Kabul Kriterleri

- `outputs/reel_analiz_batch_031_065.json` valid JSON olmali.
- 35 kaydin tamami bulunmali; eksik metadata olan Reel 056 ayrica isaretlenmeli.
- En az 5 pattern iceren comparison matrix olmali.
- Top 5 reel ve Jarvis'e uygulanacak net 5 aksiyon cikarilmali.
- Operator-facing metinler Turkce olmali.
- Baskalarinin degisiklikleri revert edilmemeli.

## Riskler ve Notlar

- Kaynak dosyada bazi caption metinleri encoding bozulmasi tasiyor; metrikler ve shortcode daha guvenilir kabul edilmeli.
- Canli Instagram scrape 403/rate-limit verebilir; bu gorev lokal veriyle tamamlanabilir.
- Reel 056 icin owner bilgisi yok; batch analizde `metadata_error_owner_missing` olarak raporlanmali.
- CTR ve save-rate gercek metrikleri yok; proxy skor olarak yorum oranlari kullanilmali.
