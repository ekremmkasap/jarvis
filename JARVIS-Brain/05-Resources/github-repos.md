---
tags: [resources, github, external]
date: 2026-04-16
---

# GitHub Repoları — Takip ve Entegrasyon

## 🎯 Aktif Takip

| Repo | Alan | Not |
|---|---|---|
| [microsoft/VibeVoice](https://github.com/microsoft/VibeVoice) | Voice AI (ASR+TTS+streaming) | `hey_jarvis.py` için aday |
| [hesamsheikh/octogent](https://github.com/hesamsheikh/octogent) | Multi-agent framework | Swarm alternatifi |
| [mo-tunn/OpenGuider](https://github.com/mo-tunn/OpenGuider) | Desktop AI assistant (Electron) | Mark-XXXV ile aynı kulvar — pattern extraction: coord pointer + replanner |
| Shadowbroker (local) | — | Zaten klonlu: `C:/Users/sergen/Desktop/Shadowbroker` |

---

## 🔥 Trending Tarama Linkleri

Haftalık/günlük taramak için:
- https://github.com/trending?since=daily
- https://github.com/trending?since=weekly
- https://github.com/trending?since=monthly
- https://github.com/trending/developers

---

## 👤 Profil Takibi

- https://github.com/hesamsheikh — Octogent yazarı, multi-agent içerik üretiyor

---

## 💡 Jarvis İçin Potansiyel Entegrasyonlar

| Repo | Entegrasyon Fikri | Etki |
|---|---|---|
| **VibeVoice** | `hey_jarvis.py` STT/TTS katmanı upgrade | Yüksek — multi-speaker + uzun form |
| **Octogent** | Swarm skill alternatifi olarak değerlendir | Orta — mevcut swarm skill var |
| **Claude-Mem** | 3-layer memory pattern → agent_memory refactor | Orta — fikir kaynağı |
| **Graphify** | Token optimization → conversation graph | Yüksek — uzun session maliyeti |

---

## Trending Tarama Şablonu (Haftalık)

Her hafta çalıştırılır, `05-Resources/trending-YYYY-WW.md` dosyasına kayıt:

```
Tarih: __________
Kaynak: github.com/trending (daily/weekly)

### Dikkat Çekenler
- [ ] repo: _________ — neden: _________ 
- [ ] repo: _________ — neden: _________

### İzleme Listesine Ekle
- [ ] _________

### Jarvis Entegrasyon Aday
- [ ] _________ — alan: _________ — POC süresi: _________
```

## İlgili
- [[instagram-sources]]
- [[03-Knowledge/vibevoice-microsoft]]
