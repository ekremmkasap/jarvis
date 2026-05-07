# Jarvis Subagent Mapping

Bu dosya `VoltAgent/awesome-codex-subagents` referansindan Jarvis icin secilen dar subagent setini tutar.

## Secim Ilkesi
- En fazla 6-10 kritik alt ajan
- Jarvis runtime ve backend omurgasina dogrudan fayda
- Rollere gore dar ve guclu secim

## Backend Core
- `backend-developer`
  - `bridge.py`, backend dispatch, runtime patch'leri
- `api-designer`
  - `/api/dashboard-summary`, command/API contract netligi
- `code-mapper`
  - `bridge.py` icinde sahiplik ve etki alani analizi

## Voice / Hologram
- `electron-pro`
  - desktop hologram ve Electron entegrasyon sorunlari
- `powershell-5.1-expert`
  - Windows launcher, batch, runtime readiness, shell uyumlulugu

## Video / Workspace
- `data-analyst`
  - signal/backlog/candidate uretimi, intelligence ozetleri
- `trend-analyst`
  - trend sinyali, workspace backlog tetikleme mantigi

## Security / Review
- `security-auditor`
  - policy gate, secret redaction, review oncesi risk taramasi
- `reviewer`
  - bug/regression/security odakli son kontrol

## Mission Control Notu
- `task-distributor`
  - `swarm` / mission-control routing mantigi icin ikinci faz adayi
- `knowledge-synthesizer`
  - workspace + intelligence + dashboard summary birlestirme icin ikinci faz adayi

## Jarvis'e Uyarlama Notu
- Bu subagent'ler birebir kopyalanmayacak.
- Jarvis tarafinda rol bazli davranis kumesi olarak dusunulecek.
- Source of truth: `server/config/agent_manifests.json`

## Shortcut Layer
- Repo-local prompt shortcuts: `tools/subagents/`
- Hedef: bu repo icin hizli ve tutarli delegation promptlari uretmek
- Komutlar bu repoyu varsayilan hedef kabul eder; sadece `-Scope` ile daraltma yapilir
- Bu katman subagent calistirmaz; Codex'e yapistirilacak delegation promptu uretir
- Calisma dizisi: `external-repos/awesome-codex-subagents/` -> `.codex/agents/` -> `tools/subagents/`

Ornekler:
- `tools\subagents\jarvis-sub-help.cmd`
- `tools\subagents\jarvis-sub-map.cmd "login timeout handling" -Scope "server/bridge.py" -Copy`
- `tools\subagents\jarvis-sub-backend.cmd "task routing bug" -Scope "server/bridge.py" -Copy`
- `tools\subagents\jarvis-sub-frontend.cmd "dashboard panel regression" -Scope "apps/web-ui/src" -Copy`
- `tools\subagents\jarvis-sub-ai.cmd "tool-call fallback issue" -Scope "server/services" -Copy`

Notlar:
- `-Copy` olusturulan prompt'u Windows clipboard'una yollar.
- `start_jarvis.bat --subagent-help` sadece yardimi basar; watchdog baslatmaz.
- Codex bu ajanlari otomatik spawn etmez; promptta acikca `Use backend-developer ...` gibi delegation istenmelidir.
- `.codex/agents/` degisirse gerekirse Codex session refresh edilir; bunun icin OpenCode restart gerekmez.

## Codex'te Kullanim

1. Shortcut komutuyla prompt uret:
   - `tools\subagents\jarvis-sub-backend.cmd "task routing bug" -Scope "server/bridge.py" -Copy`
2. Uretilen prompt'u aktif Codex session'ina yapistir.
3. Codex ilgili project-specific agent'i `.codex/agents/` altindan kullanir.

## Hangi Komut Ne Zaman

- `jarvis-sub-search`
  Bilmedigin bir davranisin hangi klasor veya dosyada yasadigini bulmak icin.
- `jarvis-sub-map`
  Sahip kod yolu, entrypoint, branch point ve side effect cikarmak icin.
- `jarvis-sub-bug` / `jarvis-sub-debug`
  Once nedenini anlamak istedigin hata ve regression isleri icin.
- `jarvis-sub-fix`
  Sahiplik kesin degilken guvenli fix akisi baslatmak icin.
- `jarvis-sub-backend` / `jarvis-sub-frontend`
  Sahip katman zaten belliyse dogrudan implementer'a gitmek icin.
- `jarvis-sub-review`
  Degisiklikten sonra bug, regression, security ve test bosluklarini kontrol etmek icin.
- `jarvis-sub-organize`
  Tek agent yerine temiz alt gorev zinciri kurmak icin.

## Onerilen Zincirler

1. Sahiplik belirsiz bug:
   `search -> map -> fix -> review`
2. Mevcut regression:
   `bug -> backend veya frontend -> review`
3. Policy, routing veya guvenlik etkili degisiklik:
   `audit -> fix -> review`
4. Buyuk gorev:
   `organize -> uzman implementer -> review`

Direkt prompt ornegi:

```text
Use backend-developer to implement or fix task routing bug in the Jarvis repo at C:\Users\sergen\Desktop\jarvis-mission-control, focused on server/bridge.py. Trace the entrypoint and side effects first, make the smallest coherent change, and return changed files plus success and failure validation notes.
```

Cok adimli prompt ornegi:

```text
Use search-specialist first to narrow the owner area for intermittent Telegram command failure in the Jarvis repo at C:\Users\sergen\Desktop\jarvis-mission-control, then use code-mapper to trace the confirmed flow, then use backend-developer to implement the smallest safe fix, and finally use reviewer to check regressions and missing tests.
```
