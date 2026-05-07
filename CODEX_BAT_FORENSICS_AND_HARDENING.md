# Codex Task — Jarvis .bat Forensics + Hardening + Voice Recovery

**Repo:** `C:\Users\sergen\Desktop\jarvis-mission-control`
**Branch:** `008-swarm-skills-integration`
**Urgency:** High — kullanıcı "bilgisayarı kapat" dedikten sonra launcher .bat dosyalarının bozulduğunu/silindiğini fark etti. Geçici kurtarma yapıldı ama root cause bulunmalı ve tekrarlanması engellenmeli.

---

## Arka plan (ne oldu)

1. **20 Nisan 2026 akşamı** Ekrem "Jarvis, bilgisayarı kapat" dedi, PC'yi kapatıp tekrar açınca şunları fark etti:
   - Masaüstündeki `SISTEM_J.bat` ve `SISTEM_J_KAPAT.bat` kayıp
   - Repo kökündeki `JARVIS_BASLAT.bat` yerine **uzantısız `JARVIS_BASLAT`** (2 satır: `"JARVIS: COMPAT WRAPPER -"`)
   - `JARVIS_SES.bat`, `start_jarvis.bat`, `start_jarvis_detached.bat`, `start_all.bat`, `restart_jarvis.bat`, `force_restart.bat` silinmişti
2. **Geçici kurtarma (bugün 21 Nisan):** `worktrees/nexus/`'dan .bat'lar repo köküne kopyalandı, `JARVIS_BASLAT.bat` yeniden yazıldı (master_launcher.py çağırıyor), masaüstüne `SISTEM_J.bat` + `SISTEM_J_KAPAT.bat` yerleştirildi.
3. **Doğrulanmış veriler:**
   - Git history'de .bat silme commit'i **yok** → disk üzerinde (working tree) silindi, commit'e girmedi
   - "COMPAT WRAPPER" string'i repoda başka hiçbir dosyada **geçmiyor** (izole vaka)
   - `hey_jarvis.py:811`'deki `bilgisayari.*kapat|shut.*down` regex'i **yorum satırında** (devre dışı) — yani Windows `shutdown /s` tetiklenemezdi
   - `git reflog`: 20 Nisan 19:32:54'te `reset: moving to HEAD` (no-op reset, working tree korundu)
   - Son 8 gündür commit yok ama working tree'de bolca M var
4. **Eş zamanlı problem:** Voice runtime (`external-repos/Mark-XXXV/main.py`) Gemini Live API'da `[KeyPool] gemini: tüm keyler tükendi!` ve `APIError 1008 (policy violation)` veriyor. `google.generativeai` deprecated (→ `google.genai`).

---

## Codex — 3 iş kalemi

### Kalem 1 — Forensics: neden .bat silindi?

**Amaç:** "COMPAT WRAPPER" migration'ını çalıştıran kodu bul. Bu asla tekrar çalışmasın.

**Yapılacaklar:**
1. Repo (+ opsiyonel `external-repos/`) üzerinde derin arama:
   - String: `"COMPAT WRAPPER"`, `"compat_wrapper"`, `"compat-wrapper"`, `"migrate_bat"`, `"rewrite_bat"`, `"bat_migration"`
   - Pattern: `\.bat.*unlink|remove|delete|rewrite`, `Path\(.*\.bat.*\)\.write_text`, `open\(.*\.bat.*["\']w`, `shutil\.move.*\.bat`
2. Git log'da pickaxe araması:
   - `git log --all --source -S "COMPAT WRAPPER" --all`
   - `git log --all --source -S "compat wrapper"`
   - `git log --all --pretty=format:"%h %ai %s" --name-only -- "*.bat"`
3. Son 30 gün Claude Code hook log'ları: `server/logs/claude_hooks/*.jsonl` — `"bilgisayari kapat"` / `"shut down"` / `"kapat"` içeren prompt ve tool_call'ları çıkar
4. `server/logs/` altında son 48 saatlik her `.jsonl` / `.log` içinde `.bat`, `unlink`, `Remove-Item`, `del ` araması
5. `skills/execution/run_command.py`, `server/skills/permission_mode.py`, `server/skills/computer_agent_skill.py`, `server/agents/opencode_bridge.py` — son değişiklikleri (`git log -p --since="30 days ago" -- <file>`) gözden geçir; LLM tetikleyebileceği kod yazma/çalıştırma kapısı bul

**Çıktı:** `specs/jarvis-bat-loss-forensics.md` — bulgular, suçlu dosya/fonksiyon (veya "bulunamadı" + kanıt), timeline, önerilen patch'ler.

### Kalem 2 — Hardening: .bat yazma/silme koruması

**Amaç:** LLM, skill veya otomasyon tetiklemeli hiçbir kod repo kökündeki `.bat` dosyalarını bir daha silemesin / üzerine yazamasın.

**Yapılacaklar:**
1. Korunacak whitelist: `JARVIS_BASLAT.bat`, `JARVIS_SES.bat`, `start_jarvis.bat`, `start_jarvis_detached.bat`, `start_all.bat`, `restart_jarvis.bat`, `force_restart.bat`, `clone_all_repos.bat`, `clone_repos.bat`
2. `server/skills/execution/run_command.py` (+ `skills/execution/run_command.py`) içindeki BLOCKED listesine ekle:
   - `del *.bat`, `del /f *.bat`, `Remove-Item *.bat`, `erase *.bat`
   - Repo kökü path + `*.bat` kombinasyonu
   - `rename *.bat`, `ren *.bat`, `move *.bat`
3. `server/skills/computer_agent_skill.py` — `blocked` listesi zaten var, oraya `.bat` pattern ekle
4. Claude Code `PreToolUse` hook: `.claude/hooks/protect_launcher_bats.py` — path'i whitelist'teki .bat'larla eşleşen Bash/PowerShell/Write komutlarını blokla, ekrana uyarı bastır
5. **Unit test:** `tests/test_launcher_bat_protection.py` — her blocked pattern için `run_command.py` + hook'un `denied` döndüğünü assert et
6. `.claude/rules/autonomous-loop-guardrails.md`'a satır ekle: "Launcher .bat dosyaları (whitelist) yalnızca elle düzenlenebilir; otonom/LLM çalışması yazamaz/silmez"

**Çıktı:** Kod değişiklikleri + test + doküman. `pytest tests/test_launcher_bat_protection.py` yeşil geçmeli.

### Kalem 3 — Voice runtime kurtarma (Mark-XXXV)

**Amaç:** `external-repos/Mark-XXXV/main.py` canlı voice oturumu kopmadan çalışsın; Gemini quota yönetimi çalışsın.

**Yapılacaklar:**
1. `external-repos/Mark-XXXV/main.py` içinde `google.generativeai` → `google.genai` migration (satır numarasıyla değişen yerler, `client = genai.Client(...)`, `client.aio.live.connect(...)` API şeması)
2. `external-repos/Mark-XXXV/memory/memory_manager.py:369` aynı migration
3. `actions/web_search.py` — `duckduckgo_search` → `ddgs` import güncellemesi (`pip install ddgs` + import rename)
4. **KeyPool audit:** `state/key_pool_state.json` oku, exhausted key'leri `GEMINI_API_KEY`, `GEMINI_KEY_SEDA` env değerleri ile karşılaştır. Hangi key'ler tükenmiş, hangileri hâlâ geçerli? Kota rotasyon mantığını `server/model_router.py` içinde kontrol et, yanlış key düşüşü varsa düzelt.
5. **Quota yönetimi:** Gemini Live API'da `1008 policy violation` döndüğünde runtime'ı yeniden başlatmak yerine 60 saniye cooldown'a al, diğer key'e (veya Groq fallback'ine) geç.
6. Mark-XXXV hâlâ sık hata alıyorsa `config/jarvis.yaml` veya env'de `VOICE_RUNTIME=classic` seçeneğiyle kullanıcı eski `hey_jarvis.py` rotasına dönebilsin (`master_launcher.py`'ya switch ekle).

**Çıktı:** Migration patch'leri + voice fallback switch. Smoke test: `python external-repos/Mark-XXXV/main.py` 2 dakika kesintisiz çalışabilmeli (Gemini key geçerliyse), keysiz de classic hey_jarvis'e düşebilmeli.

---

## Tüm işler için ortak kurallar

- **Backward-safe:** `server/bridge.py` HTTP route'ları bozulmaz, sadece additive
- **Secret redaction:** `.env` değerleri log'a / commit'e sızmaz (forensics'te key görürsen sadece isim yaz)
- **Commit stratejisi:** Her kalem ayrı commit. Mesaj formatı: `feat/fix/chore: kısa özet` (Türkçe ok)
- **Branch:** Zaten `008-swarm-skills-integration` — yeni feature branch açma
- **Test:** `python -m pytest tests/ -q` tüm suite yeşil kalmalı
- **Lint:** `ruff check server/` clean

## Teslim

Bitince repo köküne `CODEX_BAT_FORENSICS_RESULT.md` yaz:
- Kalem 1 özet (root cause + kanıt veya "bulunamadı")
- Kalem 2 değişen dosya listesi + test komutu
- Kalem 3 migration özeti + fallback test sonucu
- Açık risk/kalan iş listesi

---

## Yasaklar

- Repo kökündeki .bat'ları silme/yeniden adlandırma
- `master_launcher.py`'a ask-first olmadan büyük değişiklik yapma
- `server/bridge.py`'ta mevcut route'u kaldırma (ekle — sil değil)
- `main` veya `master` branch'e push
- `.env` değerlerini log'a / file'a basma
- `--no-verify` ile hook bypass
