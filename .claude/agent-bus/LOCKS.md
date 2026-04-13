# Dosya Kilitleri

_Bir dosyaya dokunmadan önce buraya ekle. Bitince sil._

## Aktif Kilitler

| Dosya / Dizin | Agent | Başlangıç | Tahmini bitiş |
|---------------|-------|-----------|---------------|
| server/skills/antigravity_skills.py | Claude-Tab2 | 2026-04-13 | ~ |
| server/bridge.py (antigravity section) | Claude-Tab2 | 2026-04-13 | ~ |
| apps/desktop-hologram/ | Anti | 2026-04-13 | ~ |

## Kilit Alma Kuralları

1. Dosyayı düzenlemeden önce buraya ekle
2. Başka agent kilitlemişse bekle veya farklı dosyaya geç
3. Commit attıktan sonra kilidi kaldır
4. `server/bridge.py` özeldir — sadece bir agent aynı anda yazabilir

## Serbest Dosyalar (güvenli)

- `server/skills/` altında YENİ dosyalar → her zaman güvenli
- `state/` altındaki JSON'lar → her zaman güvenli  
- `tests/` → her zaman güvenli
- `apps/web-ui/` → Anti veya Tab2 değilse güvenli

---

## Kuralın Özeti
```
LOCK al → düzenle → commit → LOCK bırak
```
