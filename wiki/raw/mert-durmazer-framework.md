# Mert Durmazer Framework — Digital Academy Referansı

**Kaynak derlemesi:** 2026-04-20 WebSearch bulguları.

## Kim

Mert Durmazer — Türk AI automation girişimcisi. Digital Academy kurucusu (Türkiye'nin en aktif AI topluluğu). AI ajan kurulumu, n8n/Make otomasyonları, SaaS geliştirme (Cursor, AntiGravity), AI ajans/freelance hizmet kurma üzerine eğitim ve rehberlik veriyor.

## Kapsamlı Yaklaşım

Durmazer'in içerik çerçevesi (YouTube + Skool topluluk):

1. **AI Agent Setup** — Claude, Claude Code, ChatGPT tabanlı ajanlar
2. **Automation** — n8n ve Make üzerinden workflow otomasyonu
3. **SaaS Vibe Coding** — Cursor ve AntiGravity IDE ile hızlı prototip
4. **AI Ajans / Freelance** — satılabilir hizmet paketleme

## Jarvis Sabri Persona'sına Uyarlanan Fikirler

| Durmazer Yaklaşımı | Sabri'de Karşılığı |
|--------------------|-------------------|
| AI ajans pipeline (brief → copy → görsel → rapor) | `sabri_brief → sabri_copy → sabri_visual_prompt → sabri_campaign_plan` |
| Pure prompt + template, offline çalışır | Sabri skill LLM bağımsız, offline template-based |
| Müşteri brief'i JSON'a çevir, state'te sakla | `state/agent_memory/sabri/briefs/<brief_id>.json` |
| Platform başına karakter limitleri | `CHAR_LIMITS` — meta/google/linkedin/instagram/tiktok |
| Hedefe göre kanal mix | `PLATFORM_MIX_BY_GOAL` — awareness/conversion/lead/engagement |

## Sonraki İterasyon

- n8n bridge entegrasyonu — Jarvis'ten n8n webhook tetikleme (ayrı spec paketi)
- Claude Code skill kataloğu — Sabri'nin alt ajanlarını Claude Code skill olarak paketleme

## Kaynaklar

- [YouTube — Digital Academy](https://www.youtube.com/channel/UCCtwhjWO0NGOAhWOgv3DKFA)
- [LinkedIn — Mert Durmazer](https://www.linkedin.com/in/mert-durmazer-9a82aa1b8/)
- [Skool topluluk sayfası](https://www.skool.com/@mert-durmazer-3601)
