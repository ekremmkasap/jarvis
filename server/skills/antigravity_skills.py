"""
antigravity_skills.py — Top 10 Antigravity Awesome Skills entegrasyonu
Kaynak: external-repos/antigravity-awesome-skills/

Telegram komutları:
  /kod-incele    — Code Reviewer
  /github-issue  — GitHub Issue Creator
  /pazar-analiz  — Market Sizing Analysis
  /seo-analiz    — SEO Audit
  /rakip-analiz  — Competitor Intelligence
  /icerik-uret   — Content Creator
  /email-sira    — Email Sequence Designer
  /pazarlama-psy — Marketing Psychology
  /ajan-orkestra — Agent Orchestrator
  /anti-skills   — Mevcut skill listesi
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ANTIGRAVITY_ROOT = Path("external-repos/antigravity-awesome-skills/skills")

# ── Skill tanımları ────────────────────────────────────────────────────────────

SKILLS = {
    "code-reviewer": {
        "komut": "/kod-incele",
        "aciklama": "Kod inceleme uzmanı — kalite, güvenlik, best practice analizi",
        "prompt_prefix": (
            "Sen elite bir kod inceleme uzmanısın (code-reviewer skill). "
            "Verilen kodu incele: kalite, güvenlik açıkları, best practices, "
            "refactor önerileri. Türkçe özet yaz, sonra İngilizce detay.\n\nKod:\n"
        ),
    },
    "github-issue-creator": {
        "komut": "/github-issue",
        "aciklama": "Hata raporunu → temiz GitHub issue'ya çevir",
        "prompt_prefix": (
            "Sen GitHub issue uzmanısın. Verilen hata raporu veya açıklamayı "
            "professional bir GitHub issue'ya çevir: başlık, description, "
            "repro adımları, beklenen/gerçek davranış, impact. "
            "Markdown formatında yaz.\n\nGiriş:\n"
        ),
    },
    "market-sizing-analysis": {
        "komut": "/pazar-analiz",
        "aciklama": "TAM/SAM/SOM pazar büyüklüğü analizi",
        "prompt_prefix": (
            "Sen pazar analizi uzmanısın. Verilen sektör veya ürün için "
            "TAM (Total Addressable Market), SAM (Serviceable Available Market), "
            "SOM (Serviceable Obtainable Market) hesapla. "
            "Türk pazarına odaklan, kaynak ve varsayımları belirt.\n\nSektör/Ürün:\n"
        ),
    },
    "seo": {
        "komut": "/seo-analiz",
        "aciklama": "SEO analizi — teknik SEO, on-page, içerik kalitesi",
        "prompt_prefix": (
            "Sen kapsamlı bir SEO uzmanısın. Verilen URL veya içerik için "
            "teknik SEO, on-page optimizasyon, schema, içerik kalitesi, "
            "AI arama uyumluluğunu analiz et. Türkçe raporla.\n\nURL/İçerik:\n"
        ),
    },
    "apify-competitor-intelligence": {
        "komut": "/rakip-analiz",
        "aciklama": "Rakip analizi — strateji, içerik, fiyatlandırma",
        "prompt_prefix": (
            "Sen rakip istihbarat uzmanısın. Verilen marka veya sektör için "
            "rakip stratejilerini, içerik yaklaşımlarını, fiyatlandırmayı "
            "ve pazar konumlandırmasını analiz et. Türkçe özet.\n\nRakip/Sektör:\n"
        ),
    },
    "content-creator": {
        "komut": "/icerik-uret",
        "aciklama": "Platform bazlı içerik üretimi — blog, sosyal medya, SEO",
        "prompt_prefix": (
            "Sen profesyonel içerik üreticisisin. Verilen konu için "
            "marka sesi analizi, SEO optimizasyonu ve platform bazlı içerik üret. "
            "Platform belirtilmezse blog + LinkedIn + Instagram formatı yaz.\n\nKonu:\n"
        ),
    },
    "email-sequence": {
        "komut": "/email-sira",
        "aciklama": "Email dizisi tasarımı — nurture, satış, onboarding",
        "prompt_prefix": (
            "Sen email pazarlama uzmanısın. Verilen ürün/hedef kitle için "
            "email dizisi tasarla: konu satırları, içerik, CTA, timing. "
            "Türk kullanıcılara hitap edecek şekilde yaz.\n\nÜrün/Amaç:\n"
        ),
    },
    "marketing-psychology": {
        "komut": "/pazarlama-psy",
        "aciklama": "Davranışsal pazarlama — psikolojik kaldıraçlar ve modeller",
        "prompt_prefix": (
            "Sen pazarlama psikolojisi uzmanısın. Verilen pazarlama kararı veya "
            "senaryo için davranış bilimine dayalı psikolojik ilkeleri uygula. "
            "Etik sınırlar içinde, uygulanabilir öneriler ver. Türkçe raporla.\n\nSenaryo:\n"
        ),
    },
    "agent-orchestrator": {
        "komut": "/ajan-orkestra",
        "aciklama": "Multi-agent orkestrasyon — skill eşleme ve koordinasyon",
        "prompt_prefix": (
            "Sen agent orkestrasyon uzmanısın. Verilen görevi analiz et, "
            "hangi Jarvis skill'lerinin kullanılacağını belirle ve "
            "multi-step iş akışını tasarla. Mevcut skilllar: "
            "araştırma, kod, bulut, Telegram, Instagram takip, CrewAI, OpenHands.\n\nGörev:\n"
        ),
    },
}


# ── Ana handler fonksiyonları ─────────────────────────────────────────────────

def _call_llm_with_prompt(prompt: str) -> str:
    """Model router üzerinden LLM çağrısı yapar."""
    try:
        import sys
        sys.path.insert(0, "server")
        from model_router import route as model_route
        result = model_route(prompt, model="groq")
        return str(result)[:1500]
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return f"LLM hatası: {e}"


def handle_antigravity_skill(skill_key: str, args: str) -> str:
    """Verilen skill_key için LLM prompt'u oluşturur ve çağırır."""
    skill = SKILLS.get(skill_key)
    if not skill:
        return f"Bilinmeyen skill: {skill_key}"
    if not args.strip():
        return (
            f"Kullanım: {skill['komut']} <girdi>\n"
            f"Açıklama: {skill['aciklama']}"
        )
    full_prompt = skill["prompt_prefix"] + args.strip()
    return _call_llm_with_prompt(full_prompt)


def handle_list_skills(_args: str = "") -> str:
    """Mevcut Antigravity skill listesini döner."""
    lines = ["🚀 *Antigravity Skills*\n"]
    for key, info in SKILLS.items():
        lines.append(f"{info['komut']} — {info['aciklama']}")
    lines.append("\nKullanım: /komut <girdi>")
    return "\n".join(lines)


# ── Kısa wrapper'lar (bridge.py'den çağrılır) ─────────────────────────────────

def run_code_reviewer(args: str) -> str:
    return handle_antigravity_skill("code-reviewer", args)

def run_github_issue(args: str) -> str:
    return handle_antigravity_skill("github-issue-creator", args)

def run_market_analysis(args: str) -> str:
    return handle_antigravity_skill("market-sizing-analysis", args)

def run_seo(args: str) -> str:
    return handle_antigravity_skill("seo", args)

def run_competitor(args: str) -> str:
    return handle_antigravity_skill("apify-competitor-intelligence", args)

def run_content_creator(args: str) -> str:
    return handle_antigravity_skill("content-creator", args)

def run_email_sequence(args: str) -> str:
    return handle_antigravity_skill("email-sequence", args)

def run_marketing_psychology(args: str) -> str:
    return handle_antigravity_skill("marketing-psychology", args)

def run_agent_orchestrator(args: str) -> str:
    return handle_antigravity_skill("agent-orchestrator", args)
