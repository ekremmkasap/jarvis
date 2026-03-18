# JARVIS DEVLOG - 2026-03-03

## YAPILDI
1. RAM temizligi + model optimizasyonu
2. bridge.py MODEL_ROUTES duzeltildi
3. run_shell_full (!! sudo prefix)
4. OLLAMA_KEEP_ALIVE=5m
5. /durum /task /gorevler /agent komutlari
6. ACTIVE_AGENTS sistemi (503 ajan)
7. OrchestratorSkill (Plan->Execute->Synthesize)
8. /ara [sorgu] - Web arama (DuckDuckGo POST)
9. /reklam [urun] - Reklam metni uretici
10. /icerik [metin] - Content Repurposer (5 platform)
11. /rakip [hedef] - Rakip analizi (web arama + AI)
12. /abtest [sayfa] - A/B Test Generator (ICE skoru)
13. /analiz [veri] - Marketing KPI analizi
14. call_ollama() -> max_tokens + num_ctx parametreleri eklendi
15. Marketing komutlari optimize edildi: 1024 token -> 110-130 token, num_ctx=512

## SUNUCU
jarvis(8080) + n8n(5678) + ollama + tenant_manager: AKTIF
bridge.py: 1257 satir

## HIZ DURUMU (2026-03-03)
llama3.2:latest ile marketing komutlari:
- /reklam: ~78sn (110 token, num_ctx=512)
- /analiz: ~53sn (120 token, num_ctx=512)
- /icerik: ~54sn (130 token, num_ctx=512)
SORUN: Cok yavas, kullanici daha hizli istiyor
SONRAKI DENEME: deepseek-coder:latest (776MB) vs llama3.2 (2GB) hiz testi

## SIRADAKI ADIM (ONCELIK SIRASI)
1. HIZ: deepseek-coder test et - kucuk model (776MB) daha hizli olabilir
2. Multi-tenant yapisi (tenants/ klasoru, her musteri ayri config)
3. Heartbeat guclendir (crash -> Telegram bildirim)
4. /ajans [kampanya] komutu (ajan zinciri: ara->reklam->icerik)
5. n8n bug incele

## CLAW DURUMU
C=OK, L=KISMI, A=OK, W=OK, S=KISMI, N=EKSIK

## KOMUT LISTESI (Guncel)
/ara /reklam /icerik /rakip /abtest /analiz
/task /gorevler /agent /durum /ebay /trendyol /plan /code

## KRITIK DOSYALAR
/opt/jarvis/openclaw/bridge.py (1257 satir)
/opt/jarvis/skills/web_search_skill.py
/opt/jarvis/skills/ollama_orchestrator.py
/opt/jarvis/skills/claude_agent_skill.py
Telegram: 8295826032:AAGn4XRJxQi98hqqZLRMcvOEaeowSGYDt-k | ChatID: 5847386182

## BAGLANTI
python (python3 degil) + paramiko, SFTP ile yaz/oku
Yeni sohbette: cat /opt/jarvis/DEVLOG.md
