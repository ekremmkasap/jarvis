# Jarvis Mission Control — DEVLOG
*Son güncelleme: 23 Mart 2026*

---

## MEVCUT DURUM

- Jarvis CALISTIYOR — Pinokio uzerinden bridge.py aktif
- Model: minimax-m2.7:cloud (200K context)
- Web UI: http://127.0.0.1:8081
- Telegram bot: AKTIF

---

## KRITIK DOSYALAR

- bridge.py (AKTIF): C:/pinokio/api/ekrem/app/bridge.py
- bridge.py (mirror): C:/Users/sergen/Desktop/jarvis-mission-control/server/bridge.py
- anydesk_kabul.ps1: C:/Users/sergen/Desktop/jarvis-mission-control/anydesk_kabul.ps1
- anydesk_kabul.ps1: C:/pinokio/api/ekrem/app/anydesk_kabul.ps1 (kopya)
- .env: C:/Users/sergen/Desktop/jarvis-mission-control/.env
- JARVIS_BASLAT.bat: C:/Users/sergen/Desktop/JARVIS_BASLAT.bat
- Autostart: C:/Users/sergen/AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup/jarvis_autostart.vbs

---

## 23 MART 2026 - YAPILAN DEGISIKLIKLER

### 1. AnyDesk Duzeltmesi
- Sorun: /kabul komutu SendKeys yanlis pencereye (Bing'e) gidiyordu
- Cozum: anydesk_kabul.ps1 yeniden yazildi
  - Win32 API ile pencere bulma (EnumWindows, EnumChildWindows)
  - 3 katmanli fallback: BM_CLICK > PostMessage > SetForegroundWindow+SendKeys
  - Method 2 sonrasi continue - diger pencerelere yanlis tus gonderme engellendi
- Path duzeltildi: Desktop\anydesk_kabul.ps1 -> jarvis-mission-control\anydesk_kabul.ps1

### 2. Pinokio bridge.py'ye /kabul Eklendi
- Pinokio bridge.py'de hic /kabul yoktu
- send_button() ve answer_callback() metodlari eklendi
- _handle_update callback_query isleyecek sekilde guncellendi

### 3. Natural Language Intercept
- "gelen istegi kabul et", "anydesk" -> otomatik /kabul calistirir
- "ekran goruntusu" -> otomatik /ekran calistirir

### 4. Yeni Model Yapisi (MODEL_ROUTES)
- chat: qwen3:4b
- general: qwen3:8b
- code: qwen2.5-coder:7b
- reasoning: deepseek-v3.1:671b-cloud
- marketing: minimax-m2.7:cloud
- search: qwen3:8b
- Cloud model destegi: OLLAMA_API_KEY header ile gonderiliyor
- Yeni komutlar: /models, /model [route] [model]

### 5. Computer Control Skill
- Dosya: server/skills/computer_control_skill.py
- /mouse [x] [y], /tikla [x] [y], /yaz [metin], /tus [key], /kisayol [combo]
- NOT: pyautogui kurulumu gerekiyor

### 6. Pinokio'dan Bagimsiz Calisma
- JARVIS_BASLAT.bat masaustune eklendi
- jarvis_autostart.vbs Windows Startup'a eklendi - PC acilinca otomatik baslar

### 7. OLLAMA API Key
- Key: [redacted - use .env]
- .env dosyasina kaydedildi (.gitignore'a eklendi)
- call_ollama() cloud modeller icin Authorization: Bearer header gonderiyor

### 8. Kod Kalitesi (Simplify)
- ANYDESK_PS_SCRIPT sabit + _run_anydesk_kabul() helper
- 4 skill handler -> SKILL_DISPATCH tablosu

---

## BEKLEYEN GOREVLER

1. pyautogui kurulumu:
   python.exe -m pip install pyautogui --break-system-packages

2. qwen3:8b indirme - OpenClaw'dan indirme ikonuna tikla

3. GitHub push (commit edilmedi):
   git add anydesk_kabul.ps1 server/bridge.py server/skills/ start_jarvis.bat start_jarvis_hidden.vbs import_agents.py import_skills_to_bridge.py
   git commit -m "feat: AnyDesk duzeltme, cloud modeller, computer control"
   git push

4. computer_control_skill.py -> Pinokio'ya kopyala:
   cp server/skills/computer_control_skill.py C:/pinokio/api/ekrem/app/skills/

5. ReMe bellek entegrasyonu - "No module named 'reme'" sorunu

---

## API ANAHTARLARI (.env'de)

OLLAMA_API_KEY=[redacted - use .env]
TELEGRAM_BOT_TOKEN=[redacted - use .env]
TELEGRAM_CHAT_ID=[redacted - use .env]

---

## TELEGRAM KOMUTLARI (Guncel)

/help         -> Tum komutlar
/kabul        -> AnyDesk kabul (buton gosterir)
/ekran        -> Ekran goruntusu
/mouse x y    -> Mouse tasi
/tikla x y    -> Tikla
/yaz metin    -> Klavyeye yaz
/tus enter    -> Tus bas
/kisayol ctrl+c -> Kisayol
/models       -> Model listesi + route'lar
/model route m-> Route'u degistir
/cmd komut    -> Terminal komutu
/ara sorgu    -> AI arama
/agent isim   -> 624 ajan
/task hedef   -> Otonom gorev
/status       -> Sistem durumu
!! komut      -> Gelismis shell
$ komut       -> Guvenli shell

---

## MIMARI

Telegram (telefon)
  -> bridge.py (C:/pinokio/api/ekrem/app/)
    -> Ollama (http://127.0.0.1:11434)
      -> llama3.2, qwen3:4b, qwen2.5-coder:7b, deepseek-r1:8b (lokal)
      -> minimax-m2.7:cloud, deepseek-v3.1:671b-cloud (bulut)
    -> Skills (624 ajan + custom skill'ler)
    -> Web Dashboard (http://127.0.0.1:8081)

GitHub: https://github.com/ekremmkasap/jarvis
