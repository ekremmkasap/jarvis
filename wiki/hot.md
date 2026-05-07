# Jarvis Wiki - Sicak Onbellek

Claude, Codex ve diger ajanlar bu dosyayi once okumali. En guncel davranis ve karar notlari burada tutulur.

## Son Guncelleme
2026-04-15 - Slack -> Jarvis runtime bridge eklendi; tokenlar girilince `JARVIS_ENABLE_SLACK=1` ile aktif edilecek.

## En Guncel Davranis Notlari

- Masaustundeki `C:\Users\sergen\Desktop\JARVIS.bat`, `master_launcher.py` uzerinden aktif olarak `external-repos/Mark-XXXV/main.py` ses runtime'ini baslatir.
- Uzun gorevlerde Jarvis once konsola `[JARVIS] [PROGRESS] ...` satiri yazar.
- Ayni ilerleme mesaji `server/logs/desktop_assistant.json` runtime state'ine dusurulur; desktop hologram bu state'i `/api/desktop-assistant` uzerinden gosterir.
- Gorev yaklasik 4 saniyeden uzun surerse Jarvis kisa bir sesli ilerleme anonsu yapar; varsayilan tekrar araligi 8 saniye, maksimum anons sayisi 2'dir.
- Sesli ilerleme `JARVIS_VOICE_PROGRESS=0` ile kapatilabilir. Gecikme ve tekrarlar `JARVIS_VOICE_PROGRESS_DELAY`, `JARVIS_VOICE_PROGRESS_REPEAT_DELAY`, `JARVIS_VOICE_PROGRESS_MAX_UPDATES` ile ayarlanir.
- Jarvis komutlarinda `/task`, `/codex`, `/codex-swarm`, `/swarm`, `/spec`, `/wiki`, `/tarayici` gibi niyetler icin daha anlamli ilerleme cumleleri secilir.
- Mark-XXXV artik `jarvis_persona` tool'u ile Jarvis'in 7 persona hattina baglanir: Seda, Mert, Buse, Eren, Luna, Sabrican, Sabri.
- Sesle "Seda'ya sor", "Buse ile konus", "hangi ajan aktif", "ajanlari listele" gibi istekler lokal bridge `/api/chat` hattina gider.
- Voice lane icin `chat_id=9998` kullanilir; web ve telegram persona state'leriyle karismamasi hedeflenir.
- 7 persona artik kendi `llm_profile` alanina sahiptir; `GEMINI_KEY_SEDA`, `GEMINI_KEY_MERT`, `GEMINI_KEY_BUSE`, `GEMINI_KEY_EREN`, `GEMINI_KEY_LUNA`, `GEMINI_KEY_SABRICAN`, `GEMINI_KEY_SABRI`.
- `GEMINI_API_KEY` 8. Google key olarak global fallback; `GROQ_API_KEY` hizli fallback olarak tutulur.
- Persona key providerlari optionaldir; key eksikse boot bozulmaz, fallback model kullanilir.
- Jarvis'in yeni kuzey yildizi managed-agent mimarisidir: Agent Config (`config/agents.yaml`, model routing, skill registry), Environment (`master_launcher.py`, `.env`, MCP/OAuth connectorlari), Session (`state/`, ReMe memory, swarm task state, outputs).
- Lokal `JARVIS.bat` modu kullanici arayuzu ve ses/hologram katmani olarak kalir; uzun ve 24/7 calismasi gereken gorevler ileride managed/cloud session'a dispatch edilmelidir.
- "Jarvis 24/7 calissin", "managed agent", "cloud agent", "laptop kapaliyken calissin" gibi isteklerde [[claude-managed-agents-jarvis-roadmap]] referans alinmalidir.
- Claude veya baska ajan devralacaksa once `OPS/409_CLAUDE_CONTINUATION_HANDOFF_20260415.md` okunmalidir. Bu dosya operator isteklerini, yapilan patchleri, testleri, kaynaklari ve siradaki isleri tek yerde toplar.
- Slack baglantisi icin `server/slack_bridge.py` eklendi. `master_launcher.py`, `JARVIS_ENABLE_SLACK=1` ise SLACK process'ini baslatir; varsayilan kapali kalir. Ayrinti: [[slack-jarvis-baglantisi]].

## Codex ve Jarvis Komut Ayrimi

- Codex IDE slash komutlari (`/local`, `/auto-context`, `/review`, `/status` vb.) oturum kontrolu icindir.
- Jarvis runtime komutlari (`/task`, `/codex`, `/codex-swarm`, `/swarm`, `/spec`, `/wiki`, `/tarayici`) gercek is orkestrasyonu icindir.
- `.claude/commands` altindaki `buddy` ve `speckit.*` akislari repo-ici workflow dosyalaridir; native Codex IDE slash komut listesi degildir.
- Slot bazli gercek Codex isi isteniyorsa `/code` veya `/kod` yerine `/codex` ya da `/codex-swarm` tercih edilmelidir.

## Gunluk Calisma Icin Tavsiye

- Kod yazarken: Codex `/local`, `/auto-context`, `/review`, `/status`
- Buyuk feature veya paralel iste: Jarvis `/codex`, `/codex-swarm`, `/task`, `/spec`, `/agent`, `/wiki`
- Sesli masaustu akista: uzun islerde progress anonsunu acik tut, ama cok konusursa `JARVIS_VOICE_PROGRESS_MAX_UPDATES=1` yap.

## Ilgili Sayfalar

- [[sesli-ilerleme-anonslari]]
- [[sesli-persona-koprusu]]
- [[persona-key-havuzu]]
- [[claude-managed-agents-jarvis-roadmap]]
- [[slack-jarvis-baglantisi]]
- [[codex-komutlari-ve-jarvis-runtime]]
- [[sesli-asistan]]
- [[telegram-komutlari]]
- [[oz-ogrenme]]
