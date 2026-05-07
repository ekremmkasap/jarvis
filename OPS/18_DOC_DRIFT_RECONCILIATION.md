# OPS 18 - Doc Drift Reconciliation

Durum: active
Amac: hangi dokumanin neyi yanlis anlattigini ve ne kadar duzeldigini tek dosyada tutmak.

## Duzeltilen Dokumanlar

### 1. README.md

Eski sorun:
- runtime hikayesi fazla daginikti
- Telegram default davranisi net degildi

Yapilan:
- bridge/orchestrator/autonomous loop haritasi netlestirildi
- Telegram default warning eklendi

Hala acik:
- dependency listesi ile gercek environment farklari ayrica gozden gecirilmeli

### 2. .env.example

Eski sorun:
- blank credential + enabled Telegram

Yapilan:
- varsayilan Telegram kapatildi

### 3. JARVIS_BASLAT_README.txt

Eski sorun:
- 6 servislik eski startup miti

Yapilan:
- canonical runtime note dosyasi olarak yeniden yazildi

### 4. WEEK3_CALEB4_COMPLETION.md

Eski sorun:
- secret exposure
- completion dili asiri guclu

Yapilan:
- secret redaction

Hala acik:
- historical overclaim dili OPS claim tablosu ile disaridan dengeleniyor

### 5. Active OPS truth artefaktlari

Eski sorun:
- 5H handoff ve stability notlari stale dashboard fail iddiasi tasiyordu
- line-count gate kapanisi yeni namespace icin kayitli degildi
- `openclaw_web_only.cmd` durumu aktif dokumanlarda acik gorunuyordu

Yapilan:
- `OPS/CODEX_5H_HARDCORE_PROMPT_V2.txt` icin `10000` line count tekrar dogrulandi
- `OPS/12_5H_HARDCORE_MASTER_ROADMAP.md` icin `3509` line count tekrar dogrulandi
- `tests.test_dashboard` current rerunda `16/16 OK` olarak kayda gecirildi
- `openclaw_web_only.cmd` wrapper durumu aktif OPS dokumanlarina yansitildi

Hala acik:
- exact `117/117` toplam claimi current tree icin full rerun ile yeniden kanitlanmis degil

## Hala Drift Ureten Dokumanlar

### A. WEEK3_COMPLETION.md

Durum:
- tarihsel belge
- ama operator tarafinda kolayca bugunku truth gibi okunabilir

Karar:
- silinmedi
- yeniden yazilmadi
- truth kaynagi olarak degil claim inventory olarak ele aliniyor

### B. INTEGRATION_SUMMARY.md

Durum:
- planning phase complete
- complete integration gibi okunmaya musait

Karar:
- claim tablosunda CONTRADICTED / planning-only baglaminda tutulur

### C. CODEX_BRIDGE_INTEGRATION_CHECKLIST.md

Durum:
- acik checklist

Karar:
- integration complete iddiasina karsi dogrudan negatif kanit

### D. RUN_24H_AUTONOMOUS.md

Durum:
- demo/simulation artifactlari ile birlikte okunmadiginda fazla iddiali gorunebilir

Karar:
- audit dosyalariyla birlikte referanslanmali

## Dokuman Siniflandirma Kurali

- canonical
- auxiliary
- historical but useful
- stale but informative
- dead weight

## Bugunku Pratik Siniflandirma

- `README.md`: canonical operator guide
- `.env.example`: canonical fresh-clone default file
- `server/SOURCE_OF_TRUTH.md`: canonical runtime demotion guide
- `WEEK3_COMPLETION.md`: historical but useful
- `INTEGRATION_SUMMARY.md`: historical/planning
- `JARVIS_BASLAT_README.txt`: updated auxiliary launcher note

## Sonraki Dokuman Isleri

1. `AGENTS.md` icindeki runtime drift tekrar gozden gecir
2. `openclaw_web_only.cmd` ile iliskili dokumani bul ve hizala
3. dependency/install hikayesini reality-check ile tekrar daralt
4. historical completion dosyalari icin merkezi bir `read-this-as-claims-not-truth` notu dusun

## Kural

- docs gercegi takip edecek
- docs gercegi uretmeyecek
- docs kanit yerine kullanilmayacak
