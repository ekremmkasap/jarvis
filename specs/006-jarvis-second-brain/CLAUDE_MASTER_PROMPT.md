# Claude Master Prompt

Sen `Jarvis Mission Control` projesinin analiz ve planlama odakli AI ajanisin.

## Dogru Repo

- Aktif repo: `C:\Users\sergen\Desktop\jarvis-mission-control`
- `C:\Users\sergen\jarvis` eski / yan proje olabilir; ana implementasyon hedefi DEGIL.

## Calisma Amaci

Jarvis'i "ikinci beyin + masaustu ajan + copilot overlay" seviyesine tasimak istiyorum.

Bu turda senden istedigim sey:

1. Mevcut yetenekleri ve skill yuzeylerini repo icinde dogru dosyalardan cikar
2. Eksik yetenekleri netlestir
3. Obsidian second-brain mimarisini kurgula
4. Eklenecek ozellikler icin uygulanabilir bir plan ve gorev listesi olustur
5. Sonunda bana Codex'e verecegim toplu, sira numarali bir task listesi ver

Bu ilk turda devasa kod degisikligi yapma. Once analiz, mimari, spec/plan/tasks ve uygulama backlog'u cikar.

## Zorunlu Okuma Sirasi

Once su dosyalari oku:

- `AGENTS.md`
- `.claude/CLAUDE.md`
- `config/agents.yaml`
- `server/bridge.py`
- `specs/005-jarvis-autonomous-command/handoff.md`

Sonra su mevcut yetenek yuzeylerini incele:

- `server/skills/computer_control_skill.py`
- `server/skills/playwright_browser_skill.py`
- `server/skills/whatsapp_skill.py`
- `server/whatsapp/wa_bridge.js`
- `server/skills/dual_monitor_vision_skill.py`
- `server/agents/vision_analyzer.py`
- `server/skills/persona_obsidian_skill.py`
- `server/skills/obsidian_auto_writer.py`
- `server/skills/wiki_auto_writer.py`
- `server/skills/agent_memory_skill.py`
- `server/skills/telegram_voice_handler.py`
- `server/skills/telegram_tts_reply.py`
- `server/skills/sub_agent_runner.py`
- `apps/desktop-hologram/main.js`
- `apps/desktop-hologram/renderer.js`
- `apps/desktop-hologram/index.html`
- `apps/desktop-hologram/styles.css`

Vakit kalirsa ilgili testleri de tara:

- `tests/test_telegram_voice.py`
- `tests/test_dual_monitor_vision.py`
- `tests/test_playwright_browser_skill.py`
- `tests/test_persona_obsidian_skill.py`
- `tests/test_obsidian_auto_writer.py`
- `tests/test_wiki_auto_writer.py`
- `tests/test_agent_memory_skill.py`
- `tests/test_sub_agent_runner.py`

## Eklenecek / Guclendirilecek Ozellikler

### 1. Masaustu Dosya ve Not Defteri Kontrolu

Jarvis'e sunlari diyebilmeliyim:

- "Not defteri ac"
- "Masaustunde txt olustur"
- "Su yaziyi not defterine yaz: ... "
- "Bir dosya olustur ve icine sunlari yaz"

Beklenen davranis:

- Windows'ta Notepad veya guvenli bir txt dosyasi olusturma akisi
- Varsayilan hedef: kullanicinin masaustu
- Path traversal veya tehlikeli dosya erisimi engellenecek
- Bu yetenek hem sesli komut, hem bridge komutu, hem chat intent ile calisabilecek

### 2. WhatsApp Otomasyonu

Jarvis sunlari yapabilmeli:

- "WhatsApp'ta Ahmet'i ara"
- "WhatsApp'a mesaj yaz Ayse: toplantiyi 5'e alalim"
- "WhatsApp Web'i ac ve kisiyi bul"

Not:

- Kisisel WhatsApp icin resmi bir genel API yoksa browser otomasyonu / mevcut bridge / Playwright tabanli cozum planla
- Windows-first dusun
- Ne gercekten var, ne eksik, ne yeniden yazilmali bunu ayir

### 3. Google / Web Arama ve Senin Gibi Arastirma

Jarvis sunu yapabilmeli:

- "Google'da X ara"
- "Bu konuyu internette arastir"
- "Ilk sonuclari bana ozetle"

Beklenti:

- Playwright veya mevcut browser skill uzerinden
- Sonuclari sesli ve metin olarak donebilsin
- Uzun arastirma sonucunda Obsidian / wiki kaydi olusturulsun

### 4. Coklu Monitor Ekran Analizi

Jarvis su an sadece tek ekran goruyorsa bunu duzelt:

- "Ekranimi analiz et"
- "Iki monitoru de tara"
- "Soldaki ekranda ne var, sagdaki ekranda ne var?"

Beklenti:

- En az 2 monitor senaryosu
- Ayrik analiz + birlesik analiz modu
- Vision sonucu kayit altina alinabilsin

### 5. Hologram / Copilot Tarzi Panel

Istedigim deneyim:

- "Hey Jarvis" dedigimde veya global kisayolla Jarvis paneli aninda acilsin
- Tek pencere, sade, duzgun, her sey bir arada olsun
- Mevcut hologram daginiksa toparlansin
- Mevcut Electron app kullanilsin

Ek ilham:

- `https://particles.casberry.in/`
- Bu siteyi birebir kopyalama
- Ama partikullu, canli, durum odakli, modern bir hologram/copilot hissi icin ilham olarak kullan
- Idle / listening / thinking / speaking durumlari icin gorsel sistem oner
- Mümkünse "Export Formation" benzeri bir akista uretilen sekil/ayarlar local component'e tasinabilsin

### 5A. 3D Particle Swarm Hologram

Bu basligi ayri bir alt deliverable olarak ele al:

- Jarvis'in klasik kutu/pencere hissinden cikmasi
- Tek merkezde, canli bir "zeka cekirdegi" gibi davranmasi
- Electron hologram UI veya gerekiyorsa web-ui tarafinda gomulebilir bir `ParticleHologram` component yapisinin planlanmasi

Beklenen durum davranislari:

- `idle`: dusuk yogunluk, sakin drift
- `listening`: merkeze cekilme, mikrofon/ses enerjisine tepki
- `thinking`: yörüngesel donus, daha hizli ama kontrollu hareket
- `speaking`: TTS veya ses frekansina bagli daha guclu amplitude / pulse
- `offline` veya `muted`: soluk, seyrek, stabil gorunum

Teknik beklenti:

- Runtime'da dis siteye bagimli olma; export edilen yapi veya parametreler lokalde tutulmali
- Uygulama tarafi Electron ise `renderer.js` / `index.html` / `styles.css` entegrasyon yuzeyi netlestirilmeli
- Eger React/Three tabanli daha dogruysa `apps/web-ui` veya hologram renderer tarafinda uygun entegrasyon alternatifi yazilmali
- GPU yuku, FPS, low-end cihaz davranisi ve fallback modu belirtilmeli
- Gerekiyorsa "particle preset" mantigi tasarla: `minimal`, `cinematic`, `performance`

### 6. Obsidian Ikinci Beyin

Jarvis'in beyni Obsidian olacak.

Istiyorum ki:

- Jarvis ile yaptigim onemli konusmalar kayit olsun
- Yapilan analizler Obsidian'a dussun
- Wiki ile Obsidian senkron mantigi olsun
- Claude / Codex / Antiye gibi ajanlarin yaptigi isler de kayda gecsin
- Repo ozetleri ve fikirler Obsidian'da kalici bilgiye donussun

Ozellikle su yetenekleri tasarla:

- `bridge.py` -> Obsidian kayit akisi
- Jarvis kendi kodunu analiz ettiginde Obsidian notu dusmesi
- Yapilan gelistirme fikirlerinin backlog / note / wiki kaydi
- Gecmis oturum ozetlerinin tutulmasi

### 7. Jarvis Kendi Kaynak Kodunu Analiz Etsin

Sunu diyebilmeliyim:

- "Jarvis kendi kaynak kodunu analiz et"
- "Bu repoda eksik yetenekleri bul"
- "Bana gelistirme fikirleri sun"

Beklenen davranis:

- Repo tarama
- Skill/env/bridge/test surface analizi
- TODO/FIXME/eksik test/eksik entegrasyon tespiti
- Sonucu bana ozetlemesi
- Obsidian ve wiki'ye kaydetmesi
- Gerekirse Codex / Claude / Antiye icin gorev cikarmasi

### 8. 32 Repo / Dis Repo Hafizasi

Jarvis'in beynine repo ozetleri de girsin.

Yapman gereken:

- Repoda veya konfigde gecen repo listelerini bul
- 32 repo gercekten nerede, hangi klasorde, hangi formatta kayitli bunu tespit et
- Her repo icin ozet / kullanim / entegrasyon notu cikarma stratejisi oner
- Obsidian ve wiki tarafinda nasil indekslenecegini tasarla

### 9. Telegram Sesli Konusma Kanali

Jarvis ile Telegram uzerinden sesli konusmak istiyorum.

Beklenti:

- Voice message al
- STT ile metne cevir
- Intent islet
- Yaniti tekrar TTS ile ses olarak dondur
- Mumkunse Obsidian / memory kaydi da olustur

## Teknik Arastirma Protokolu

Uygulanabilirlik arastirmasi yaparken:

- Once repo icindeki mevcut implementasyonu oku
- Sonra gerekiyorsa resmi dokumantasyon / primary source dogrulasi yap
- Ozellikle su basliklarda resmi kaynak kontrol et:
  - Playwright browser automation
  - Electron global shortcut / transparent overlay / alwaysOnTop
  - Telegram bot voice download ve send_voice
  - Obsidian entegrasyon secenekleri
  - Multi-monitor screenshot yakalama

Context7 veya benzeri dokuman cekme araclari varsa kullan.

## Kurallar

- `server/bridge.py` APPEND-ONLY
- Var olan calisan yuzeyleri gereksiz bozma
- Windows-first dusun
- Her dosyayi yazmadan once oku
- Ilk cevapta buyuk kod dump'i yapma
- Once analiz + tablo + plan + gorev listesi ver
- Eger bir ozellik zaten kismen varsa bunu "var / kismi / yok" diye net ayir
- Riskleri saklama; ozellikle WhatsApp ve wake-word tarafinda teknik sinirlari yaz

## Benden Beklenen Cikti Formati

Cevabini su sirayla ver:

### 1. Aktif Repo Teyidi
- Dogru repo yolu
- Yanlis repo / eski repo varsa not

### 2. Mevcut Skill ve Capability Listesi
Tablo formatinda:
- Ozellik
- Mevcut dosya(lar)
- Durum: `var` / `kismi` / `yok`
- Not

### 3. Gap Analizi
- Her hedef ozellik icin ne eksik
- En kritik engeller
- Hangi kisim yeniden yazilmali, hangi kisim reuse edilmeli

### 4. Mimari Oneri
- Obsidian second brain akisi
- Bridge routing akisi
- Telegram / voice / memory / wiki / Codex baglantilari
- Hologram UI akisi
- Particle swarm render akisi ve state machine eslesmesi

### 5. Uygulama Fazlari
Faz 1, Faz 2, Faz 3 diye ayir.
Her faz icin:
- hedef
- dosyalar
- test / smoke
- risk

### 6. Codex'e Verilecek Toplu Gorev Listesi
T001, T002, T003... formatinda yaz.
Her task icin:
- amac
- dosyalar
- kabul kriteri
- dogrulama komutu

### 7. Uretilecek / Guncellenecek Spec Dosyalari
Su klasor altinda oner:

- `specs/006-jarvis-second-brain/spec.md`
- `specs/006-jarvis-second-brain/plan.md`
- `specs/006-jarvis-second-brain/tasks.md`
- gerekirse `research.md` ve `contracts/`

### 8. Kisa Sonuc
- En iyi baslangic sirasi
- Ilk uygulanacak 3 task

## Ek Not

005 kapanis durumunu dikkate al:

- `specs/005-jarvis-autonomous-command/handoff.md`

Bu dosyada backend smoke ve frontend smoke dogrulandi. 006 planini bunun ustune kur.

## Son Direktif

Bana yari yamalak fikir degil, repo okumus, dosya yuzeylerini gormus, uygulanabilir, sirali bir master plan ver.

Ilk hedef: masaustu not defteri/yazi yazma + coklu monitor + Obsidian second brain omurgasi.

Ikinci hedef: WhatsApp + Google/web + Telegram voice + self-analysis.

Ucuncu hedef: hologram/copilot panelini modernlestirip tek merkez haline getirmek.
