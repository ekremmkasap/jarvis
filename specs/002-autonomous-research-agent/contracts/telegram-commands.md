# Telegram Command Contracts

**Feature**: 002-autonomous-research-agent  
**Router**: server/bridge.py

---

## Yeni Komutlar

| Komut | Açıklama | Yanıt Süresi |
|-------|----------|-------------|
| `/instagram takip @hesap` | Hesabı watch_list'e ekler | <5sn |
| `/instagram liste` | Takip edilen hesapları listeler | <3sn |
| `/instagram sil @hesap` | Hesabı watch_list'den çıkarır | <3sn |
| `/crewai [görev]` | CrewAI'a görev gönderir | <60sn (async) |
| `/crewai durum` | CrewAI kurulum/durum kontrolü | <10sn |
| `/openhands [görev]` | OpenHands'e görev gönderir | <60sn (async) |
| `/openhands durum` | OpenHands kurulum/durum kontrolü | <10sn |
| `/arastirma-durum` | Scheduler durumu, son brief zamanı | <3sn |
| `/sabah-brief` | Manuel brief tetikler (test) | <30sn |

---

## Örnek Yanıtlar

### `/instagram takip @fatihmakes`
```
✅ @fatihmakes takip listesine eklendi.
Platform: Instagram | Kontrol aralığı: 30 dakika
```

### `/instagram liste` (boş)
```
📋 Takip listesi boş.
Eklemek için: /instagram takip @hesap
```

### `/crewai durum` (kurulu)
```
✅ CrewAI hazır
Yol: external-repos/crewAI/
Kullanım: /crewai [görev açıklaması]
```

### `/crewai durum` (kurulu değil)
```
⚠️ CrewAI kurulu değil.
Kurulum: pip install crewai
Repo: external-repos/crewAI/
```

### `/arastirma-durum`
```
📊 Araştırma Scheduler Durumu
Son brief: 2026-04-13 08:00 ✅
Sonraki: 2026-04-14 08:00
Takip: 3 Instagram hesabı
Kaynaklar: GitHub, Reddit, X (Nitter)
```

---

## Mevcut Komut Uyumluluğu

Mevcut bridge.py komutlarının hiçbiri değişmez. Yeni komutlar sadece yeni `elif` blokları olarak eklenir.  
`/yardim` çıktısına yeni komutlar **eklenir** (mevcut liste korunur).

---

## Hata Yanıtları

| Durum | Yanıt |
|-------|-------|
| Instagram private hesap | "⚠️ @hesap gizli profil, takip edilemiyor." |
| Instagram hesap yok | "⚠️ @hesap bulunamadı." |
| Max 50 hesap aşıldı | "⚠️ Takip limiti doldu (50). Önce /instagram sil @hesap ile birini çıkar." |
| API çekilemiyor | "⚠️ [kaynak] şu an alınamıyor. Brief diğer kaynaklarla gönderildi." |
| Scheduler çalışmıyor | "⚠️ Araştırma scheduler'ı başlatılmamış. Jarvis'i yeniden başlat." |
