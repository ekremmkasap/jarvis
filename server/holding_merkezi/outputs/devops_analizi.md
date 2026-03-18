# ADIM 1 — DEVOPS DARBOĞAZ ANALİZİ
Tarih: 2026-03-03

## ÖZET
- bridge.py: 1235 satır, v2.1
- Threading: Telegram handler için Thread() var, ancak skill işlemleri SYNC
- Ollama: timeout=120s, CPU-bound, blokluyor

## TESPİT EDİLEN DARBOĞAZLAR

### 1. Skill Importları — Tekrarlayan sys.path.insert() (ORTA)
Her komut handler fonksiyonu kendi içinde:
    sys.path.insert(0, "/opt/jarvis/skills")
Bu 14+ yerde tekrarlanıyor. Başlangıçta 1 kez yapılmalı.
FIX: bridge.py satır 165 dışındakiler kaldırılabilir.

### 2. Ollama timeout=120s (YÜKSEK)
call_ollama() fonksiyonu 120 saniye bekliyor.
Telegram thread'i bloklanmıyor (Thread() ile çalışıyor) AMA
aynı anda 3 kullanıcı mesaj atarsa 3 Ollama isteği paralel gider
→ llama3.2 CPU-only, tek seferinde 1 istek işleyebilir
→ 2. ve 3. istek sıralı bekleme moduna girer
FIX: Ollama request queue + öncelik sırası

### 3. Web Server — Senkron BaseHTTPRequestHandler (DÜŞÜK)
start_web() fonksiyonu tek thread'li HTTP server
Her web isteği sıraya giriyor
FIX: ThreadingHTTPServer kullan (1 satır değişiklik)

### 4. Content Factory Oturum State (DÜŞÜK)
CONTENT_FACTORY_SESSIONS dict — belleğe yazıyor, restart'ta siliyor
FIX: SQLite'a taşı (zaten content_factory_skill.py'de var)

## ASENKRON REFACTOR PLANI

### Kısa Vadeli (Bu Hafta)
1. Web server → ThreadingHTTPServer
2. sys.path tekrarları → tek satıra indir
3. Ollama request limiter (max 2 paralel istek)

### Uzun Vadeli (FAZ 2)
1. asyncio + aiohttp → tam async Ollama çağrıları
2. Redis queue → görev sıralaması
3. FastAPI → web dashboard

## MEVCUT KLASÖR YAPISI (/opt/jarvis)
agents/, ajans_projeleri/, config/, core/, knowledge/, logs/,
memory/, openclaw/, skills/, tenants/

## YENİ: holding_merkezi/ KURULDU
inputs/newsletter/, inputs/briefler/, inputs/hedef_kitle/
outputs/medya/, outputs/web_siteleri/, outputs/musteri_listesi/, outputs/reklam_kampanyalari/
swipe_file/gorseller, swipe_file/viral_postlar, swipe_file/email_sablonlari
onay_kuyrugu/
