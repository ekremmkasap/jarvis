# Codex Slash Komutları ve Jarvis Runtime Ayrımı

## Özet

15 Nisan 2026 itibarıyla VS Code/IDE içindeki resmi Codex slash komutları sadece şunlar:

- `/auto-context`
- `/cloud`
- `/cloud-environment`
- `/feedback`
- `/local`
- `/review`
- `/status`

Bu komutlar proje içi işi doğrudan çalıştıran komutlar değil, **Codex oturumunun nasıl davranacağını kontrol eden** komutlardır.

Jarvis Mission Control tarafındaki slash komutları ise bunun tersidir: `server/bridge.py` içinde tanımlı `/task`, `/swarm`, `/agent`, `/spec`, `/codex`, `/wiki`, `/tarayici` gibi komutlar gerçek ajan, slot, wiki, browser ve otomasyon akışlarını yürütür.

Kısa ayrım:

- **Codex IDE slash komutları** -> oturum kontrolü
- **Jarvis runtime slash komutları** -> iş orkestrasyonu
- **`.claude/commands` içeriği** -> repo içi workflow belgeleri, native Codex slash listesi değil

## Katmanlar

### 1. Codex IDE Slash Komutları

En faydalı set:

- `/local` -> günlük local coding için varsayılan mod
- `/auto-context` -> dosya/bağlam toplama
- `/review` -> commit/PR öncesi inceleme
- `/status` -> thread/context/rate-limit görünürlüğü

`/cloud` ve `/cloud-environment` sadece işi özellikle remote ortamda koşturmak istendiğinde değerli olur.

### 2. Jarvis Runtime Komutları

İşi gerçekten yaptıran komut seti:

- `/task` -> yüksek seviyeli hedeften plan + execute
- `/codex` -> gerçek slot/job dispatch
- `/codex-swarm` -> çoklu Codex slot dağıtımı
- `/swarm` -> multi-agent orchestration
- `/agent` -> persona/ajan değiştirme
- `/spec` -> hafif spec-plan-tasks akışı
- `/wiki` -> repo hafızası / bilgi kaydı
- `/tarayici` -> görünen Chromium üstünde Playwright otomasyonu

### 3. Repo-İçi Workflow Komutları

`.claude/commands/` altında bulunan `buddy` ve `speckit.*` dosyaları repo içi workflow tanımlarıdır. Bunlar OpenAI Codex IDE'nin native slash komut listesine otomatik eklenen komutlar değildir.

## Davranış Notları

### En kritik ayrım: `/code` veya `/kod` ile `/codex`

Help metni bazı yerlerde `/kod` veya `/code` hattını Codex worker gibi anlatıyor. Ancak gerçek slot bazlı dispatch hattı `/codex` komutundadır.

Pratik kural:

- Basit model çağrısı veya code-route için `/code` / `/kod`
- Gerçek Codex slotu, job kuyruğu ve worker dispatch için `/codex`

Slot bazlı iş isteniyorsa doğru komut `/codex` veya `/codex-swarm` olmalıdır.

## Tavsiye Edilen Kullanım

### Günlük VS Code çalışma modu

1. `/local`
2. `/auto-context`
3. `/review`
4. `/status`

### Büyük feature veya paralel orkestrasyon

1. Jarvis `/codex` veya `/codex-swarm`
2. Jarvis `/task`
3. Jarvis `/spec` veya repo içindeki `speckit.*`
4. Jarvis `/agent`
5. Jarvis `/wiki`

## Jarvis İçin Öğrenme Notu

Komut yorumlarken şu kural uygulanmalı:

- Eğer kullanıcı IDE içindeki çalışma biçimini, bağlamı, review akışını veya oturum durumunu soruyorsa önce **Codex IDE slash komutları** düşünülmeli.
- Eğer kullanıcı "bir işi yap", "ajan dağıt", "swarm başlat", "wikiye yaz", "browser aç" gibi operasyonel bir istek veriyorsa önce **Jarvis runtime komutları** düşünülmeli.
- Eğer prompt iki katmanı karıştırıyorsa, önce kullanıcı niyetinin **oturum kontrolü mü yoksa iş orkestrasyonu mu** olduğuna karar verilmeli.

## Kaynaklar

- OpenAI Codex IDE slash commands
- OpenAI Codex IDE commands / IDE docs
- `server/bridge.py`
- `server/skills/swarm_skill.py`
- `server/skills/obsidian_sync_skill.py`
- `.claude/commands/speckit.jarvis.md`
- `.claude/commands/buddy.md`

## İlgili Sayfalar

- [[telegram-komutlari]]
- [[oz-ogrenme]]
- [[mimari-genel-bakis]]
