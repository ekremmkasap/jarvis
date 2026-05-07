# Sesli Persona Koprusu

## Amac

Masaustu `JARVIS.bat` ile acilan Mark-XXXV voice runtime, Jarvis Mission Control altindaki 7 persona ile konusabilmelidir. Mark-XXXV bu personlari taklit etmez; lokal bridge uzerinden gercek Jarvis persona katmanina baglanir.

## Aktif Persona Listesi

- Seda: code, debug, yazilim gelistirme
- Mert: arastirma, rakip analizi, kanit toplama
- Buse: marketing, icerik, sosyal medya, satis metni
- Eren: veri, KPI, dashboard, raporlama
- Luna: security, audit, risk
- Sabrican: ops, devops, deploy, servis takibi
- Sabri: strateji, fikir, teklif ve is modeli

## Mark-XXXV Tool Davranisi

Mark-XXXV icinde `jarvis_persona` tool'u vardir. Sesli veya yazili komutta kullanici persona niyeti verdiginde bu tool cagrilir.

Ornekler:

- "Seda'ya sor bu bug nerede?" -> `jarvis_persona(action="ask", persona="seda", message="bu bug nerede?")`
- "Buse ile konus" -> `jarvis_persona(action="switch", persona="buse")`
- "Hangi ajan aktif?" -> `jarvis_persona(action="status")`
- "Ajanlari listele" -> `jarvis_persona(action="list")`

## Bridge Hatti

`jarvis_persona`, `external-repos/Mark-XXXV/actions/jarvis_bridge.py` icindeki `send_chat_to_jarvis()` helper'ini kullanir.

Aktif HTTP hat:

```text
Mark-XXXV jarvis_persona
  -> actions/jarvis_bridge.py send_chat_to_jarvis()
  -> http://127.0.0.1:8081/api/chat
  -> server/bridge.py process_message()
  -> persona_manager active voice lane
```

Voice lane icin `chat_id=9998` kullanilir. Boylece web, telegram ve voice persona state'leri birbirinden ayrilabilir.

## Kritik Runtime Notu

2026-04-15'te progress hook eklenirken `_build_progress_messages()` yanlis yere yerlestigi icin `JarvisLive` class'i erken kapanmis ve `_on_text_command` methodu class disinda kalmisti. Bu hata voice thread'i baslangicta dusurup mikrofonun hic acilmamasina sebep oldu.

Duzeltilen davranis:

- `_build_progress_messages()` module-level helper olarak class disina alindi.
- `_queue_playback_audio`, `_drain_playback_batch`, `_on_text_command`, `_receive_audio`, `_execute_tool` gibi methodlar tekrar `JarvisLive` class'i icinde gorunur hale geldi.
- `JarvisLive(FakeUI())` smoke testi artik callback ve `jarvis_persona` tool path'ini crash olmadan dogruluyor.

## Operasyon Notu

Bu degisiklik aktif olan eski `JARVIS.bat` oturumuna otomatik yuklenmez. Canli kullanim icin masaustu Jarvis oturumu kapatilip yeniden baslatilmalidir.
