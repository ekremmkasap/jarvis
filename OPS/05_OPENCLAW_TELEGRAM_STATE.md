# OPS 05 - OpenClaw Telegram State

Durum: partial
Secret politikasi: bu dosya token veya auth materyali yazmaz

## 1. En Kisa Sonuc

OpenClaw tarafinda local auth/pairing state var.

Ama:
- canlı end-to-end Telegram reply kanıtı yok
- PowerShell default CLI invocation sürtünüyor
- eski wrapper'lar yanlış path'e bakıyordu
- `--dev` canonical görünmüyor

## 2. Yerel Durum

Doğrulanan klasörler:
- `.openclaw\\agents\\main`
- `.openclaw\\devices\\paired.json`
- `.openclaw\\logs\\commands.log`
- `.openclaw\\logs\\config-health.json`

Gözlem:
- `agents` altında net görülen profil `main`
- `main` altında auth ve model state dosyaları var

## 3. Pairing Gercegi

Doğrulanan gerçek:
- `.openclaw\\devices\\paired.json` populated

Bu neyi kanıtlar:
- pairing veya operator token state'i oluşmuş

Bu neyi kanıtlamaz:
- Telegram transport başarılı
- agent-generated reply başarılı
- doğru profile ile routing yapıldığı

## 4. CLI Gercegi

Doğrudan gözlem:
- `Get-Command openclaw` bulundu
- PowerShell'de `openclaw --help` execution policy nedeniyle takıldı

Operasyonel sonuç:
- PowerShell üzerinden `openclaw.ps1` varsayılan yolu güvenilir değil
- Windows helper tarafında `openclaw.cmd` tercih etmek daha mantıklı

Bu sprintte yapılan:
- `server/openclaw_bridge.py` default komutu `openclaw.cmd` olacak şekilde yeniden yazıldı

## 5. Profile Gercegi

Eski helper durumu:
- `server/openclaw_bridge.py` eski halinde `OPENCLAW_PROFILE = "--dev"`

Kanıt problemi:
- `.openclaw\\agents` altında `dev` agent profili görülmedi
- görülen profil `main`

Yorum:
- `--dev` canonical değil
- main daha güvenilir kaynak

Bu sprintte yapılan:
- helper default profile boş bırakıldı
- `OPENCLAW_PROFILE` env ile explicit override zorunlu hale getirildi

## 6. Wrapper Drift

Eski durum:
- `openclaw.cmd`
- `install_openclaw_startup.cmd`
- muhtemel diğer wrapper'lar
olmayan `server/openclaw/bridge.py` yoluna bakıyordu

Bu sprintte yapılan:
- `openclaw.cmd` canonical `server/bridge.py` wrapper'ına çevrildi
- `install_openclaw_startup.cmd` aynı mantığa çevrildi

Not:
- `openclaw_web_only.cmd` ayrıca gözden geçirilmelidir

## 7. Yardimci Helper Gercegi

`server/openclaw_bridge.py` için doğru anlatım:
- canonical runtime değil
- optional helper
- Telegram send ve agent dispatch helper

Bu sprintte düzelen kritik bug:
- `send_hour_report_to_telegram()` artık olmayan instance method çağırmıyor

Bu sprintte düzeltilen diğer riskler:
- hardcoded chat id kaldırıldı
- default `--dev` kaldırıldı
- Windows command path iyileştirildi

## 8. Telegram Gercegi

Canonical runtime Telegram kanıtı bridge logunda:
- bridge kalkıyor
- `Jarvis Telegram bot basladi`
- ama send/getUpdates `WinError 10013` ile fail ediyor

Yorum:
- canonical Telegram yolu `server/bridge.py`
- OpenClaw helper bunu ispatlamıyor

## 9. Direct Send vs Agent Reply

### Direct send neyi ispatlar

- bot token geçerli mi
- chat pairing doğru mu
- outbound Telegram transport çalışıyor mu

### Direct send neyi ispatlamaz

- model auth
- agent routing
- message generation
- end-to-end assistant reply

### Agent-generated reply neyi ister

- inbound update polling
- routing
- model/provider auth
- reply compose
- outbound send

Bugünkü durum:
- transport katında zaten problem işareti var
- dolayısıyla agent-generated başarı iddiası kapatılamaz

## 10. Model/Auth Katmani

OpenClaw local state:
- auth profile dosyaları mevcut
- model profile dosyaları mevcut

Ama repo tarafı ayrıca şunları taşıyor:
- `config/account_registry.json`
- `state/codex-accounts/`
- `server/agents/profiles/*`
- missing `config/session_profiles.json` referansları

Yorum:
- profile/auth anlatısı parçalı
- tek canonical profile registry yok

## 11. Bu Sprintten Sonraki En Dogru Operasyon Tavsiyesi

Bugün için en güvenli öneri:
- canonical kullanıcı-facing runtime olarak `server/bridge.py` kullan
- OpenClaw helper'ı secondary path olarak tut
- explicit `OPENCLAW_PROFILE` verilmedikçe `--dev` kullanma
- canlı Telegram testini ayrı ve kontrollü bir operasyon adımı olarak yap

## 12. Gate Karari

Gate 3 durumu:
- green değil
- hard-failed de değil
- `PARTIAL / HARD-BLOCKED FOR LIVE SEND`

Sebep:
- pairing/auth state kanıtlandı
- helper drift azaltıldı
- ama canlı Telegram send/reply bu sprintte kontrollü olarak yürütülmedi
- mevcut bridge logları zaten transport sorunu gösteriyor
