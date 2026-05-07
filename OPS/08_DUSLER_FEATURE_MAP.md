# Düşler (Dreams) Feature Map — OpenClaw 2026.4.22

**Tarih:** 2026-04-24  
**OpenClaw sürümü:** 2026.4.22 (00bd2cf)  
**Araştıran:** Claude Code (Opus 4.7)  
**Hedef okuyucu:** Codex — Görev 3 implementasyonundan önce referans.

---

## Tek satır özet

Düşler, OpenClaw'un **short-term konuşma kaydı → uyku fazları (light/rem/deep) → uzun süreli MEMORY.md promosyonu** akışıdır. Biyolojik uyku metaforu: light sleep = hatırlama, REM = tema yansıması, deep = kalıcı gerçeklere taşıma.

**"Uyku sırasında bellek kopması"** (UI panelindeki mesaj) = dreaming cycle çalıştı ama bugünün deep fazı **0 kalıcı aday** üretti → MEMORY.md'ye yeni bir şey eklenmedi. Yani "kopma" = konsolidasyon boşa gitti, feature bozuk değil.

---

## Dosya sistemi yapısı

```
~/.openclaw/workspace/memory/
├── .dreams/
│   ├── session-corpus/           # Ham günlük konuşma metinleri
│   │   ├── 2026-04-23.txt
│   │   └── 2026-04-24.txt
│   ├── session-ingestion.json    # Corpus yükleme metadata
│   ├── short-term-recall.json    # En son yakalanan memory entry'leri
│   ├── phase-signals.json        # Hangi entry light/REM/deep hit aldı, kaç kez
│   └── events.jsonl              # memory.recall.recorded + memory.dream.completed
└── dreaming/
    ├── light/
    │   └── 2026-04-24.md         # Light sleep raporu (kısa-vade recall)
    ├── rem/
    │   └── 2026-04-24.md         # REM raporu (tema yansımaları + lasting truth adayları)
    └── deep/
        └── 2026-04-24.md         # Deep sleep raporu (MEMORY.md'ye kalıcı taşınan adaylar)
```

Her fazın günlük raporu, o gün icra edilen "uyku" işleminin çıktısıdır.

---

## Faz akışı

### 1. Light sleep (hatırlama)
- Kaynak: `session-corpus/*.txt`
- Çıktı: `dreaming/light/YYYY-MM-DD.md`
- Phase signal: `lightHits` sayacı her entry için artar
- Amaç: "son 24 saatte ne konuştuk, neyi tekrar hatırlamaya değer"

### 2. REM sleep (tema yansıması)
- Kaynak: light sleep çıktısı + short-term-recall
- Çıktı: `dreaming/rem/YYYY-MM-DD.md`
- Yapı:
  ```markdown
  # REM Sleep
  ### Reflections
  - Theme: `<keyword>` kept surfacing across N memories.
    - confidence: 0.00-1.00
    - evidence: memory/.dreams/session-corpus/...:line-line
    - note: reflection
  ### Possible Lasting Truths
  - <candidate truth lines> OR "No strong candidate truths surfaced."
  ```
- Bugünkü REM (örnek): 14 memory'de "user", 12'sinde "gateway", 12'sinde "heartbeat.md" teması tekrar etmiş. Lasting truth çıkmamış.

### 3. Deep sleep (kalıcı promosyon)
- Kaynak: REM raporu
- Çıktı: `dreaming/deep/YYYY-MM-DD.md`
- Ne yapar:
  - Adayları skor/ağırlıkla sıralar (`memory promote` tek başına da çağrılabilir)
  - `--apply` verilirse MEMORY.md'ye append eder
- Bugünkü deep raporu (örnek):
  ```
  # Deep Sleep
  - Ranked 0 candidate(s) for durable promotion.
  - Promoted 0 candidate(s) into MEMORY.md.
  ```
  Yani **today's consolidation empty** — REM fazı tema buldu ama hiçbiri "lasting truth" eşiğini geçemedi. Bu Ekrem'in UI'da "bellek kopması" olarak gördüğü durum.

---

## CLI yüzeyi (`openclaw memory`)

```
index           Reindex memory files
promote         Rank short-term recalls and optionally append top entries to MEMORY.md
promote-explain Explain a specific promotion candidate and its score breakdown
rem-backfill    Write grounded historical REM summaries into DREAMS.md for UI review
rem-harness     Preview REM reflections, candidate truths, and deep promotions without writing
search          Search memory files
status          Show memory search index status (supports --fix, --deep)
```

**Önemli flag'ler:**
- `memory promote --limit 10 --min-score 0.75` — kaç aday, hangi eşik üstü
- `memory promote --apply` — gerçekten MEMORY.md'ye yaz
- `memory rem-harness` — dry-run, yazmaz
- `memory rem-backfill` — eski günleri retroaktif işle, DREAMS.md'ye yazsın (UI için)

---

## Gateway WS RPC'leri (2026.4.22'de görüldü)

Gateway startup loglarında:
- `doctor.memory.dreamDiary` — Düşler doktor probe'u (UI paneli muhtemelen bunu poll ediyor)
- `doctor.memory.status` — memory index durumu

Yani UI "Düşler" paneli, gateway üzerinden `doctor.memory.dreamDiary` RPC'sine bakıp light/rem/deep özet veriyor.

---

## Olaylar (`events.jsonl` şeması)

```jsonl
{"type":"memory.recall.recorded","timestamp":"...","query":"__dreaming_sessions__:YYYY-MM-DD","resultCount":N,"results":[...]}
{"type":"memory.dream.completed","timestamp":"...","phase":"light|rem|deep","reportPath":"...md","lineCount":N,"storageMode":"separate"}
```

Jarvis tarafında bu event stream'i `tail -f` ile izlemek, dreaming cycle bitince hook fırlatmak için ideal.

---

## Tetikleyici/Zamanlama

- Bugün 00:00:11 UTC (~03:00 local) otomatik çalıştı. Muhtemelen OpenClaw'ın iç cron/heartbeat mekanizması. `openclaw cron list` ile doğrulanabilir.
- Manuel tetiklemek için: `openclaw memory promote --apply` (yalnız deep faz) veya `openclaw memory rem-backfill` (eski günler retroaktif).

---

## Jarvis entegrasyonu için somut noktalar (Görev 3 input'u)

Codex'e not: `server/skills/openclaw_dreams_skill.py` yazarken aşağıdakileri kullan.

### a) Snapshot API (opsiyon 1 — dosya okuma)
Direkt dosya oku, en güvenli yol:
```python
DREAMS_ROOT = Path.home() / ".openclaw" / "workspace" / "memory" / "dreaming"
def get_todays_dream(phase: str = "rem") -> str | None:
    today = datetime.now().strftime("%Y-%m-%d")
    fp = DREAMS_ROOT / phase / f"{today}.md"
    return fp.read_text(encoding="utf-8") if fp.exists() else None
```

### b) Snapshot API (opsiyon 2 — CLI çağrısı)
```python
subprocess.run([OPENCLAW_COMMAND, "memory", "rem-harness"], capture_output=True, text=True)
```
REM çıktısını stdout'tan al — dry-run, diske yazmaz.

### c) Persona memory bridge
Önerilen skill yapısı:
```python
def capture_dream_snapshot(persona_id: str = None) -> dict:
    """
    - REM raporunu oku (~/.openclaw/workspace/memory/dreaming/rem/YYYY-MM-DD.md)
    - Markdown'dan 'Theme: X kept surfacing across N memories' satırlarını regex ile çek
    - Her tema için persona_manager.remember(persona_id, f"[dream-theme] {theme}: {count} kez") çağır
    - Dönen dict: {"themes_captured": int, "lasting_truths": int, "target_persona": str, "report_path": str}
    """
```

### d) Komut yüzeyi
- `/dusler-snapshot` → Sabrican aktifken → capture_dream_snapshot çağır
- `/dusler-rapor [light|rem|deep]` → Bugünün raporunu oku, Telegram'a stream et
- Policy: `evaluate_operator_action("dreams_snapshot", persona_id=..., require_approval=False)` — `operator.high_risk` matrisinde yeri yok; Sabrican için default allow.

---

## Open sorular (Codex/Ekrem karar verecek)

1. **Session corpus kaynağı:** OpenClaw hangi konuşmalardan corpus üretiyor? Telegram bridge mi, webchat mi, CLI agent turn mu? Eğer Jarvis'ten gelen trafik corpus'a girmiyorsa, `session-ingestion.json` üzerinden manuel feed gerekli.
2. **Light phase neden 25 satırken deep 2 satır?** Promosyon eşiği yüksek — `memory promote --min-score 0.5` ile düşürülüp denenebilir.
3. **REM lasting truths neden boş?** Tema tekrarı güçlü (14 kez) ama "truth candidate" üretimi için muhtemelen farklı bir LLM çağrısı gerekiyor ve gateway logunda gemini-2.5-flash 400 hatası var:
   ```
   error=LLM request failed: provider rejected the request schema or tool payload. rawError=400
   ```
   Bu Düşler'in eksik kalmasının asıl sebebi olabilir. Gemini schema bug → REM lasting truth generator çöküyor.
4. **DREAMS.md nerede?** `rem-backfill` description'ında "Write grounded historical REM summaries into DREAMS.md" diyor ama dosya henüz yok; backfill çalıştırılması lazım.

---

## Verification komutları (Codex kullanımı)

```bash
# Status
"$APPDATA/npm/openclaw.cmd" memory status

# REM dry-run
"$APPDATA/npm/openclaw.cmd" memory rem-harness

# Promosyon explain (eşik/puan detayı)
"$APPDATA/npm/openclaw.cmd" memory promote-explain --help

# Bugünkü raporları oku
cat ~/.openclaw/workspace/memory/dreaming/{light,rem,deep}/$(date +%Y-%m-%d).md

# Son 20 dream event
tail -20 ~/.openclaw/workspace/memory/.dreams/events.jsonl | jq -c '.'
```
