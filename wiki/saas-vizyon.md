# Jarvis — SaaS Vizyonu

## Konsept
Jarvis = self-hosted, Türkçe, sıfır API maliyetli AI asistan SaaS

## Hedef Kitle
- Türk KOBİ'leri ve girişimciler
- Multi-tenant: her müşteri ayrı bot token + soul.md + SQLite bellek

## Paketler

| Paket | Fiyat | Hedef |
|-------|-------|-------|
| Starter | ₺1.500/ay | Bireysel kullanım |
| Pro | ₺3.500/ay | KOBİ |
| Agency | ₺7.500/ay | Ajans/çoklu hesap |

## Finansal Hedef
- 20 müşteri → ₺80.000/ay

## Referans Kaynaklar
- Okyanusi (Akın Yılmaz)
- Digital Academy
- AgentClaw

## Teknik Altyapı

### Multi-Tenant Yönetimi
- `server/skills/tenant_manager.py` → `TenantManager` sınıfı
- İşlemler: `create_tenant`, `get_tenant`, `list_tenants`, `deactivate_tenant`, `get_tenant_stats`
- Admin komutları: `/admin_musteriler`, `/admin_stats`

### Ödeme Sistemi
- Stripe webhook entegrasyonu (yarım kaldı — Codex kotası bitti)
- Env değişkenleri:
  - `STRIPE_WEBHOOK_SECRET`
  - `STRIPE_STARTER_PRICE_ID`
  - `STRIPE_PRO_PRICE_ID`
  - `STRIPE_AGENCY_PRICE_ID`

### Landing Page
- `apps/web-ui/src/app/landing/page.tsx`
- SEO metadata + OG görseli (`jarvis-og.svg`)
- SSS bölümü

## Sonraki Adımlar
1. Stripe production webhook URL kaydı
2. Google OAuth credentials otomasyonu
3. Notion entegrasyon onboarding sadeleştirme
4. Multi-tenant bot token yönetimi UI

## İlgili Sayfalar
- [[entegrasyonlar]]
- [[mimari-genel-bakis]]
- [[telegram-komutlari]]
