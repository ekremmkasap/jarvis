# Jarvis Telegram Komutlari

Bu sayfa Telegram operator yuzeyinin kisa ve guncel ozetidir.
Calisan davranisin source of truth dosyasi `server/bridge.py`, runtime erisim kurallari ise `server/runtime_config.py` ve `.env.example` uzerindedir.

## Guvenlik

- Bot token, chat id ve diger kimlik bilgileri wikiye veya repoya duz metin olarak yazilmaz.
- Telegram kurulumu icin asgari ortam degiskenleri: `JARVIS_ENABLE_TELEGRAM`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
- Operator bildirimi veya health anonslari gerekiyorsa `ADMIN_CHAT_ID` ve ilgili Codex notify degiskenleri ayrica tanimlanir.
- Bu sayfa komut rehberidir; secret envanteri degildir.

## Komut Yuzeyi

Asagidaki liste operator tarafinda en cok kullanilan komutlari kategorik olarak toplar.
Tum alias ve deneysel komutlar burada tutulmaz; tam dispatch akisi icin `server/bridge.py` esas alinmalidir.

### Codex Orkestrasyonu

| Komut | Amac |
| --- | --- |
| `/codex [slot|auto] [gorev]` | Tek gorevi belirli slota veya otomatik secilen slota dispatch eder. |
| `/codex-swarm [gorev]` | Gorevi birden fazla Codex slotuna dagitmak icin kullanilir. |
| `/codex-durum` | Slot bazli ozet ve uygunluk gorunumu verir. |
| `/codex-kuyruk` | Bekleyen job listesini ozetler. |
| `/codex-saglik` | Slot health, stuck job ve cooldown sinyallerini ozetler. |
| `/codex-baslat [role] [gorev]` | Role tabanli operator dispatch girisi. |
| `/codex-durdur` | Aktif Codex islerini durdurmak icin kullanilir. |
| `/codex-cooldown-temizle` | Slot cooldown state temizligi yapar. |
| `/codex-sonuc [job_id]` | Tek bir job icin sonuc veya ozet dondurur. |
| `/codex-dispatch [gorev]` | Aktif persona slotuna gore otomatik dispatch yapar. |

### Autonomous ve Yerel Makine Kontrolu

| Komut | Amac |
| --- | --- |
| `/pc-durum` | CPU, RAM, disk ve Jarvis process ozetini verir. |
| `/ekran-goruntusu` | Whitelist kontrollu screenshot yollar. |
| `/ac <app>` | Whitelist icindeki uygulamayi acar. |
| `/dosya-gonder <path>` | Whitelist altindaki dosyayi Telegram uzerinden yollar. |
| `/jarvis-baslat` | Yerel launcher hattini tetikler. |
| `/jarvis-kapat` | Bilinen Jarvis processlerini kapatir. |
| `/hafiza [persona]` | Persona bazli yakin hafiza ozetini getirir. |
| `/ajanlarin-ozeti` | Persona veya ajan gorunumunu toplu verir. |

### Skill ve Framework Kopruleri

| Komut | Amac |
| --- | --- |
| `/octogent [durum|start|init|projects]` | Octogent runtime koprusu. |
| `/octogent-health` | Octogent runtime ve API snapshot ozeti. |
| `/crew` veya `/crewai` | CrewAI skill girisi. |
| `/openhands` | OpenHands koprusu. |
| `/upondhand` | Upondhand alias hatti. |
| `/devika` | Devika workflow koprusu. |
| `/aider` | Aider entegrasyonu. |
| `/cline` | Cline entegrasyon ozeti. |
| `/route [model] [soru]` | ClawRouter veya route bilgi yuzeyi. |
| `/cli [komut]` | CLI-Anything admin yuzeyi. |

### Bilgi, Spec ve Katalog

| Komut | Amac |
| --- | --- |
| `/wiki [konu]` | Wiki sayfasi getirir veya ilgili notu bulur. |
| `/wiki ekle [baslik] | [icerik]` | Wikiye yeni icerik ekler. |
| `/spec [komut]` | Hafif specify -> plan -> tasks akisi. |
| `/prompt [kategori]` | Prompt katalog aramasi. |
| `/catalog [arama]` | Agent katalog aramasi. |
| `/repo [arama]` | External repo havuzu veya entegrasyon durumu. |
| `/repo-oner [gorev]` | Goreve uygun repo veya arac onerisi. |
| `/claude_skills [kategori]` | Claude skills listesi. |
| `/sirket [komut]` | Isletme runtime veya Paperclip odakli ozetler. |

## Operasyon Notlari

- `/codex` ile `/codex-swarm` ayni sey degildir. Ilki tek dispatch, ikincisi coklu lane dagitimi icindir.
- `/codex-dispatch` aktif persona slotunu kullanir; operator elle slot secmek istemiyorsa bu daha guvenli giristir.
- `/codex-sonuc` ve `/codex-kuyruk` gozlem komutlaridir; yeni is baslatmazlar.
- `/wiki`, `/spec` ve benzeri Jarvis runtime komutlari, IDE icindeki native Codex slash komutlariyla karistirilmamalidir.

## Hardening Branch Notu

`jarvis-codex-swarm-hardening` tarafinda su an ayrica gelistirilen ama bu dalda henuz kesinlesmeyen yuzeyler var:

- GET `/api/codex/auth-status`
- GET ve POST `/api/codex/bus`
- GET `/api/autonomous/status`
- POST `/api/autonomous/pause`
- POST `/api/autonomous/resume`
- Telegram tarafinda planlanan `/otonom-durum`, `/otonom-durdur`, `/otonom-baslat`

Bu maddeler merge olduktan sonra bu sayfa "mevcut" komut listesine tasinmalidir; merge oncesi roadmap notu olarak okunmalidir.

## Ilgili Sayfalar

- [[codex-komutlari-ve-jarvis-runtime]]
- [[mimari-genel-bakis]]
- [[oz-ogrenme]]
