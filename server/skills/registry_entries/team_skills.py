"""Team skills registry — 5 yeni specialist skill + swarm team dispatch."""
from __future__ import annotations

from server.skill_registry import SkillEntry, SkillRegistry

try:
    from server.skills.financial_analyst_skill import run_financial_analysis
    from server.skills.engineering_team_skill import run_engineering_team
    from server.skills.marketing_core_skill import run_marketing_core
    from server.skills.c_level_advisor_skill import run_c_level_advisory
    from server.skills.autoresearch_loop_skill import run_autoresearch_loop
except Exception:  # pragma: no cover
    from skills.financial_analyst_skill import run_financial_analysis  # type: ignore
    from skills.engineering_team_skill import run_engineering_team  # type: ignore
    from skills.marketing_core_skill import run_marketing_core  # type: ignore
    from skills.c_level_advisor_skill import run_c_level_advisory  # type: ignore
    from skills.autoresearch_loop_skill import run_autoresearch_loop  # type: ignore


def _wrap(fn):
    def _handler(args: str = "", context: dict | None = None):
        ctx = context or {}
        return fn(args or "", ctx)
    return _handler


def _wrap_autoresearch(args: str = "", context: dict | None = None):
    ctx = context or {}
    iters = int(ctx.get("max_iterations", 3))
    timeout = float(ctx.get("timeout", 120.0))
    return run_autoresearch_loop(args or "", max_iterations=iters, timeout=timeout, context=ctx)


def register_team_skills(registry: SkillRegistry) -> None:
    registry.register(SkillEntry(
        command="/finansal-analiz",
        handler=_wrap(run_financial_analysis),
        description="SaaS finansal analiz (MRR, ARPU, LTV, DCF)",
        aliases=["/financial-analyst", "/finans"],
        category="teams",
    ))
    registry.register(SkillEntry(
        command="/muhendislik-ekibi",
        handler=_wrap(run_engineering_team),
        description="Seda + Sabrican paralel engineering swarm",
        aliases=["/engineering-team", "/eng-team"],
        requires_args=True,
        min_args=1,
        category="teams",
    ))
    registry.register(SkillEntry(
        command="/pazarlama",
        handler=_wrap(run_marketing_core),
        description="Marketing core — landing/copy/CTA/lead magnet",
        aliases=["/marketing", "/marketing-core"],
        requires_args=True,
        min_args=1,
        category="teams",
    ))
    registry.register(SkillEntry(
        command="/c-level",
        handler=_wrap(run_c_level_advisory),
        description="C-Level strategic advisory (Sabri/atlas)",
        aliases=["/ceo-tavsiye", "/strateji"],
        requires_args=True,
        min_args=1,
        category="teams",
    ))
    registry.register(SkillEntry(
        command="/autoresearch-loop",
        handler=_wrap_autoresearch,
        description="Iteratif otonom arastirma (max 3 iter, 120s)",
        aliases=["/auto-arastir"],
        requires_args=True,
        min_args=1,
        category="teams",
    ))
