# Sesli Ilerleme Anonslari

## Amac

Ekrem masaustundeki `JARVIS.bat` ile Jarvis'i baslattiginda, yapilan islerin ilerlemesi hem gorunur hem de gerekirse sesli olmalidir. Bu sayfa Jarvis'in bu davranisi nasil uygulayacagini anlatir.

## Launcher Zinciri

Aktif masaustu zinciri:

```text
C:\Users\sergen\Desktop\JARVIS.bat
  -> master_launcher.py
     -> external-repos/Mark-XXXV/main.py
```

Bu nedenle sesli ilerleme davranisi oncelikle `external-repos/Mark-XXXV/main.py` icinde uygulanir. `hey_jarvis.py` fallback olarak kalir; masaustu bat su anda Mark-XXXV runtime'ini tercih eder.

## Gorunurluk Kurali

Jarvis bir kullanici istegi veya tool/bridge komutu islerken:

- Masaustu BAT konsoluna `[JARVIS] [PROGRESS] ...` satiri yazilir.
- Runtime state `server/logs/desktop_assistant.json` uzerinden guncellenir.
- Desktop hologram bu state'i `/api/desktop-assistant` ile okuyup `thinking` fazinda gosterir.
- Kisa islerde sesli araya girilmez; cevap gelince normal cevap okunur.

## Sesli Anons Kurali

Gorev yaklasik 4 saniyeden uzun surerse Jarvis kisa bir ilerleme anonsu yapar. Varsayilan davranis:

- Ilk anons gecikmesi: `4.0` saniye
- Tekrar araligi: `8.0` saniye
- Maksimum sesli anons: `2`
- Gorev bitince progress takip thread'i durdurulur.

Bu ayarlar ortam degiskenleriyle kontrol edilir:

```text
JARVIS_VOICE_PROGRESS=0                 # sesli progress kapatir
JARVIS_VOICE_PROGRESS_DELAY=4.0         # ilk anons gecikmesi
JARVIS_VOICE_PROGRESS_REPEAT_DELAY=8.0  # tekrar araligi
JARVIS_VOICE_PROGRESS_MAX_UPDATES=2     # maksimum anons sayisi
```

## Niyet Bazli Mesajlar

Jarvis kullanici metninden niyeti sezerek daha anlamli ilerleme cumleleri secer:

- `/codex-swarm` veya `/swarm`: ajanlari dagitiyorum, sonucu topluyorum.
- `/codex`: Codex slotunu hazirliyorum, job sonucunu bekliyorum.
- `/task` veya gorev: gorevi plana ayiriyorum, ajan atamasini kontrol ediyorum.
- `/spec` veya speckit: spec akisini hazirliyorum, kabul kriterlerini duzenliyorum.
- `/wiki`: wiki kaydini hazirliyorum, index ve sicak onbellek guncelleniyor.
- `/tarayici`, browser veya Playwright: tarayici otomasyonunu hazirliyorum.
- `/agent`, persona veya ajan: aktif rolu degistiriyorum.

Genel islerde varsayilan mesaj: "Istegini isliyorum."

## Operasyon Notu

Kod degisikligi aktif oturuma otomatik yuklenmez. Yeni davranisin canli calismasi icin masaustundeki `JARVIS.bat` oturumu kapatilip yeniden baslatilmalidir.
