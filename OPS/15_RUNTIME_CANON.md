# OPS 15 - Runtime Canon

Durum: active
5H adaptation note: bridge-first canonical hikaye korunur; ama parallel runtime gercegi gizlenmez.

## En Kisa Canon

Bu repo tek runtime değildir.

Gerçek tablo:
- bir bridge-first runtime
- bir ayrı FastAPI orchestrator runtime
- bir ayrı autonomous loop runtime
- birkaç sidecar ve legacy yüzey

## 1. Canonical Windows Runtime

Birincil runtime:
- `server/bridge.py`

Niye canonical:
- `server/SOURCE_OF_TRUTH.md` bunu açıkça canonical gösteriyor
- Windows launcherlar fiilen bridge-first akıyor
- Telegram + embedded HTTP + monitoring helper importleri burada birleşiyor

Ana sorumluluklar:
- Telegram long polling
- `/api/chat`
- embedded web dashboard/API
- model routing
- memory/state entegrasyonları
- bazı team/task helper akışları

## 2. Parallel Runtime

İkinci gerçek runtime:
- `services/orchestrator/main.py`

Ne yapıyor:
- `/task`
- `/tasks`
- `/tasks/{id}/confirm`
- `/agents`
- `/voice`
- `/ws`

Alt parçaları:
- `services/orchestrator/task_queue.py`
- `services/orchestrator/agent_runner.py`
- `services/orchestrator/safety.py`
- `services/orchestrator/ws_broadcaster.py`

Önemli not:
- bu runtime bridge'in alt modülü değil
- paralel ikinci backend yüzeyi

## 3. Third Runtime

Üçüncü bağımsız runtime:
- `server/autonomous_loop.py`

Rol:
- worktree tabanlı iteratif autonomous maintenance
- validation
- commit/report akışı

Sınır:
- launcherlar varsayılan akışta bunu boot etmiyor
- bridge/orchestrator ile tek bir kanonik supervisor altında birleşmiş değil

## 4. Sidecar Yüzeyler

Manuel dashboard sidecar:
- `server/monitoring/dashboard_server.py`

Ne bekliyor:
- ayrı aiohttp server

Gerçek durum:
- default launcher zincirinde standart değil
- dashboard split yaratıyor

Voice sidecar:
- `services/voice/voice_service.py`

Durum:
- master launcher bunu başlatabilir
- bridge ile aynı süreç değil

## 5. Legacy / Drift / Secondary Surfaces

Legacy bridge:
- `server/bridge_server.py`

Sorunlar:
- Linux-centric pathler
- 8080 legacy davranışı
- canonical değil

OpenClaw wrapper family:
- `openclaw.cmd`
- `openclaw_web_only.cmd`
- `install_openclaw_startup.cmd`

Eski durum:
- wrapper ailesi tarihsel olarak olmayan `server/openclaw/bridge.py` yoluna bakiyordu

Guncel durum:
- `openclaw.cmd` canonical bridge wrapper mantigina cekildi
- `install_openclaw_startup.cmd` canonical bridge wrapper mantigina cekildi
- `openclaw_web_only.cmd` `server/bridge.py --web-only` delegasyonu yapiyor

Yorum:
- wrapper drift azaldi
- bu aile hala auxiliary launch surface, canonical runtime degil

Watchdog:
- `server/watchdog.py`

Durum:
- standalone helper
- heartbeat/lock producer kontratı zayıf
- canonical runtime supervisor diye anlatılamaz

## 6. Launcher Canon

### `master_launcher.py`

Gerçekte başlattıkları:
- bridge
- voice
- hologram

Gerçekte başlatmadığı halde dokümanlarda adı geçenler:
- watchdog
- gateway
- team
- OpenCode

Yorum:
- ownership drift buradan çıkıyor

### `start_jarvis.bat`

Gerçekte:
- bridge-first yol

### `start_all.bat`

Gerçekte:
- orchestrator-first yol
- UI için ayrı manuel adım gerekiyor

## 7. Port Canon

Bridge:
- `8081`

Orchestrator:
- `8091`

Monitoring dashboard sidecar:
- `8888`

Ollama:
- `11434`

Drift örnekleri:
- eski orchestrator dokümanları `8090`
- eski OpenClaw wrapper `8080`

## 8. Dashboard Canon

Bu repo tek dashboard taşımıyor:
- bridge embedded dashboard
- `apps/web-ui` FastAPI orchestrator UI
- `apps/monitoring-dashboard` sidecar UI

Yorum:
- dashboard ownership üçe bölünmüş
- kullanıcıya tek canonical UI diye anlatılamaz

## 9. Task Ownership Canon

Bridge tarafı `/task`:
- gerçek autonomous loop değildir
- Week1/team/agent runtime helper zincirine gider

Orchestrator tarafı `/task`:
- TaskQueue -> AgentRunner akışıdır

Autonomous loop:
- kendi CLI ve state akışını kullanır

## 10. Memory Canon

Bridge tarafı:
- JSON runtime state
- SQLite long-term memory
- ReMe path

Team orchestrator tarafı:
- JSONL audit/memory

Sonuç:
- tekil memory sistemi yok
- ama bridge runtime için primary yol artık daha tutarlı

## 11. Runtime Cümlesi

Bu repo için bugün kullanılabilecek en doğru tek cümle:

`server/bridge.py` Windows tarafında birincil canonical runtime'dır; `services/orchestrator/main.py` ve `server/autonomous_loop.py` ise ondan ayrı çalışan paralel runtime yüzeyleridir.

## 12. Neyi Production-Ready Diye Anlatmamak Gerekir

Söylenmemesi gerekenler:
- "tek runtime"
- "tüm servisleri launcher yönetiyor"
- "dashboard tek noktada birleşti"
- "OpenClaw wrapper canonical"
- "autonomous loop bridge task endpoint'inin içidir"

## 13. Bu Sprintte Runtime Canon İçin Yapılanlar

- README port/runtime haritası güncellendi
- `.env.example` Telegram default davranışı daha güvenli hale getirildi
- launcher note dosyası canonical gerçeğe göre yeniden yazıldı
- OpenClaw wrapper eksik path yerine canonical bridge'e yönlendirildi
- `server/openclaw_bridge.py` helper seviyesiyle sınırlı tutuldu
