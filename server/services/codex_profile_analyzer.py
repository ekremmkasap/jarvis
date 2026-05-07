"""
Codex Profile Analyzer — Instagram profil'lerinin paralel analiz'i

Workflow:
1. Ekrem: Instagram profil list'i gönder
2. Codex: Scrape + engagement + themes + monetization (parallel)
3. Claude (Me): Strategic synthesis + playbook generation
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import aiohttp

logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class EngagementMetrics:
    """Profil'in engagement baseline'ı"""
    avg_likes: float
    avg_comments: float
    avg_shares: float
    avg_saves: float
    engagement_rate: float
    total_posts_analyzed: int
    date_range_days: int


@dataclass
class ContentTheme:
    """Bir content kategorisi ve performans'ı"""
    theme: str  # "education", "behind-the-scenes", "product", "philosophy", etc.
    frequency_percent: float  # Bu theme'nin %'si
    avg_engagement_for_theme: float  # Bu theme posts'un ortalama engagement'ı
    examples: List[str] = field(default_factory=list)  # Post descriptions


@dataclass
class MonetizationModel:
    """Para kazanma yöntemi ve sinyalleri"""
    primary_model: str  # "education+lead-gen", "product-sales", "agency-services", "community", etc.
    secondary_models: List[str] = field(default_factory=list)
    cta_pattern: str  # "Comment X for...", "Link in bio", "DM for", etc.
    lead_magnet: Optional[str] = None  # "checklist", "guide", "template", etc.
    monetization_clarity: str  # "Explicit" or "Implicit"
    estimated_mrr_range: Optional[str] = None  # "₺5K-10K" or similar


@dataclass
class GrowthSignals:
    """Profil'in momentum'u"""
    follower_count: int
    growth_rate_percent_per_week: float
    posting_frequency_per_week: float
    content_consistency: str  # "High", "Medium", "Low"
    audience_composition: Dict[str, float]  # {"18-24": 0.25, "25-34": 0.45, ...}


@dataclass
class ProfileAnalysis:
    """Full profil analiz'i — Codex output'u"""
    handle: str
    platform: str  # "instagram"
    profile_url: str
    
    # Metrics
    engagement: EngagementMetrics
    
    # Content strategy
    content_themes: List[ContentTheme]
    top_performing_theme: str
    
    # Monetization
    monetization: MonetizationModel
    
    # Growth
    growth: GrowthSignals
    
    # Analysis metadata
    analyzed_post_count: int
    analysis_date: str
    analysis_tool: str = "codex-v1"
    
    # Raw data (for debugging)
    raw_posts: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class AggregateInsights:
    """Ekrem'e sunulacak strategic playbook"""
    analyzed_profiles: int
    analysis_date: str
    
    # Pattern findings
    top_5_content_themes: List[Dict[str, Any]]  # theme, frequency, avg_engagement
    monetization_models_ranking: List[Dict[str, Any]]  # model, profile_count, avg_engagement
    growth_benchmarks: Dict[str, float]  # "avg_weekly_growth", "avg_engagement_rate", etc.
    
    # Turkish market signals
    turkish_market_specific: Dict[str, Any]  # educator credibility signals, autonomy narrative, etc.
    
    # Recommendations
    jarvis_strategic_playbook: Dict[str, Any]  # Actionable recommendations
    
    # Detailed profile rankings
    profile_rankings: List[Dict[str, Any]]  # Sorted by engagement/growth/monetization


# ============================================================================
# CODEX INTERFACE (Stub for now — actual Codex API call)
# ============================================================================

class CodexProfileScraper:
    """
    Codex'e gönderilen paralel profile scraping task'ı
    
    Real implementation: REST API to Codex instance
    Stub implementation: Mock data for testing
    """
    
    def __init__(self, codex_base_url: str = "http://localhost:9090"):
        self.codex_base_url = codex_base_url
        self.session = None
    
    async def init_session(self):
        """Initialize aiohttp session"""
        self.session = aiohttp.ClientSession()
    
    async def close_session(self):
        """Cleanup"""
        if self.session:
            await self.session.close()
    
    async def analyze_profile(self, handle: str, platform: str = "instagram") -> Optional[Dict[str, Any]]:
        """
        Single profile'ı Codex'e gönder ve analiz'i al
        
        Codex endpoint: POST /tasks/analyze-instagram-profile
        Input: { "handle": "leadgenman", "posts_to_analyze": 30 }
        Output: ProfileAnalysis (JSON)
        """
        
        payload = {
            "handle": handle,
            "platform": platform,
            "posts_to_analyze": 30,  # Last 30 posts
            "metrics": [
                "engagement_rate",
                "content_themes",
                "monetization_signals",
                "growth_signals",
                "audience_demographics"
            ]
        }
        
        try:
            # Real Codex API call
            async with self.session.post(
                f"{self.codex_base_url}/tasks/analyze-instagram-profile",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.error(f"Codex error for {handle}: {resp.status}")
                    return None
        
        except Exception as e:
            logger.error(f"Failed to analyze {handle}: {e}")
            return None
    
    async def analyze_profiles_parallel(
        self,
        handles: List[str],
        max_concurrent: int = 5
    ) -> List[Optional[Dict[str, Any]]]:
        """
        Multiple profiles'ı parallel'de analiz et
        
        Semaphore: max_concurrent tasks at once (Codex rate limit)
        """
        
        await self.init_session()
        
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def analyze_with_semaphore(handle: str):
            async with semaphore:
                logger.info(f"Analyzing {handle}...")
                result = await self.analyze_profile(handle)
                logger.info(f"✓ Completed {handle}")
                return result
        
        tasks = [analyze_with_semaphore(handle) for handle in handles]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        await self.close_session()
        
        return results


# ============================================================================
# ANALYSIS AGGREGATION (Claude — Me)
# ============================================================================

class ProfileAnalysisAggregator:
    """
    Codex output'larını aggregate ederek strategic insights'a dönüştür
    """
    
    def __init__(self):
        self.analyses: List[ProfileAnalysis] = []
    
    def add_analysis(self, analysis: Dict[str, Any]):
        """Codex output'unu ProfileAnalysis'e dönüştür"""
        try:
            profile = ProfileAnalysis(**analysis)
            self.analyses.append(profile)
        except Exception as e:
            logger.error(f"Failed to parse analysis: {e}")
    
    def calculate_top_content_themes(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Tüm profile'daki content theme'lerini aggregate et
        """
        theme_scores = {}
        
        for analysis in self.analyses:
            for theme in analysis.content_themes:
                if theme.theme not in theme_scores:
                    theme_scores[theme.theme] = {
                        "theme": theme.theme,
                        "total_frequency": 0,
                        "total_engagement": 0,
                        "count": 0
                    }
                
                theme_scores[theme.theme]["total_frequency"] += theme.frequency_percent
                theme_scores[theme.theme]["total_engagement"] += theme.avg_engagement_for_theme
                theme_scores[theme.theme]["count"] += 1
        
        # Calculate averages
        for theme_data in theme_scores.values():
            theme_data["avg_frequency"] = theme_data["total_frequency"] / theme_data["count"]
            theme_data["avg_engagement"] = theme_data["total_engagement"] / theme_data["count"]
        
        # Sort by engagement
        ranked = sorted(
            theme_scores.values(),
            key=lambda x: x["avg_engagement"],
            reverse=True
        )[:top_n]
        
        return ranked
    
    def calculate_monetization_rankings(self) -> List[Dict[str, Any]]:
        """
        Monetization model'lerini profile distribution'u ile rank'le
        """
        model_stats = {}
        
        for analysis in self.analyses:
            model = analysis.monetization.primary_model
            
            if model not in model_stats:
                model_stats[model] = {
                    "model": model,
                    "profile_count": 0,
                    "total_engagement": 0,
                    "total_growth": 0,
                    "profiles": []
                }
            
            model_stats[model]["profile_count"] += 1
            model_stats[model]["total_engagement"] += analysis.engagement.engagement_rate
            model_stats[model]["total_growth"] += analysis.growth.growth_rate_percent_per_week
            model_stats[model]["profiles"].append(analysis.handle)
        
        # Calculate averages
        for model_data in model_stats.values():
            model_data["avg_engagement"] = (
                model_data["total_engagement"] / model_data["profile_count"]
            )
            model_data["avg_growth"] = (
                model_data["total_growth"] / model_data["profile_count"]
            )
        
        # Sort by engagement
        ranked = sorted(
            model_stats.values(),
            key=lambda x: x["avg_engagement"],
            reverse=True
        )
        
        return ranked
    
    def calculate_growth_benchmarks(self) -> Dict[str, float]:
        """
        Market-wide growth benchmarks hesapla
        """
        if not self.analyses:
            return {}
        
        total_engagement_rate = sum(a.engagement.engagement_rate for a in self.analyses)
        total_growth = sum(a.growth.growth_rate_percent_per_week for a in self.analyses)
        total_posting_freq = sum(a.growth.posting_frequency_per_week for a in self.analyses)
        
        count = len(self.analyses)
        
        return {
            "avg_engagement_rate": total_engagement_rate / count,
            "median_engagement_rate": self._median([a.engagement.engagement_rate for a in self.analyses]),
            "avg_weekly_growth_percent": total_growth / count,
            "avg_posting_frequency": total_posting_freq / count,
            "total_profiles_analyzed": count,
            "date_analyzed": datetime.now().isoformat()
        }
    
    def identify_turkish_market_signals(self) -> Dict[str, Any]:
        """
        Turkish market'a özel pattern'ları identify et
        
        Known signals (from previous research):
        - Educator credibility + autonomy narrative = 2.0-2.43x engagement
        - Philosophical positioning = 1.6K+ engagement
        - Behind-the-scenes = higher than feature dumps
        - Community CTA ("Comment X") = lead generation
        """
        
        signals = {
            "educator_profiles": 0,
            "autonomy_narrative_profiles": 0,
            "philosophical_positioning_profiles": 0,
            "behind_scenes_heavy_profiles": 0,
            "community_led_monetization_profiles": 0,
            "avg_engagement_educator": 0,
            "recommendations": []
        }
        
        educator_engagement = []
        
        for analysis in self.analyses:
            # Check educator signals
            if any(t.theme in ["education", "tutorial", "guide"] for t in analysis.content_themes):
                signals["educator_profiles"] += 1
                educator_engagement.append(analysis.engagement.engagement_rate)
            
            # Check autonomy narrative
            if any(t.theme in ["automation", "efficiency", "productivity"] for t in analysis.content_themes):
                signals["autonomy_narrative_profiles"] += 1
            
            # Check behind-the-scenes heavy
            if any(
                t.theme == "behind-the-scenes" and t.frequency_percent > 20
                for t in analysis.content_themes
            ):
                signals["behind_scenes_heavy_profiles"] += 1
            
            # Check community-led monetization
            if "Comment" in analysis.monetization.cta_pattern:
                signals["community_led_monetization_profiles"] += 1
        
        if educator_engagement:
            signals["avg_engagement_educator"] = sum(educator_engagement) / len(educator_engagement)
        
        # Recommendations based on signals
        if signals["educator_profiles"] > 0:
            signals["recommendations"].append(
                "Educator positioning works in Turkish market — credibility + autonomy = proven 2.0-2.43x multiplier"
            )
        
        if signals["community_led_monetization_profiles"] > 0:
            signals["recommendations"].append(
                "Community engagement CTAs ('Comment X for') drive lead generation — high conversion model"
            )
        
        if signals["behind_scenes_heavy_profiles"] > 0:
            signals["recommendations"].append(
                "Behind-the-scenes content outperforms feature dumps — transparency wins"
            )
        
        return signals
    
    def generate_jarvis_strategic_playbook(self) -> Dict[str, Any]:
        """
        Jarvis'e özel action playbook'u generate et
        """
        
        top_themes = self.calculate_top_content_themes(5)
        monetization_models = self.calculate_monetization_rankings()
        benchmarks = self.calculate_growth_benchmarks()
        turkish_signals = self.identify_turkish_market_signals()
        
        playbook = {
            "title": "Jarvis Instagram Strategic Playbook",
            "generated_date": datetime.now().isoformat(),
            
            "content_strategy": {
                "top_5_themes": top_themes,
                "recommendation": f"Focus on {top_themes[0]['theme']} (avg {top_themes[0]['avg_engagement']:.1f}% engagement)",
                "content_calendar": {
                    "weekly_breakdown": {
                        "monday": "Top performing theme",
                        "wednesday": "Educational",
                        "friday": "Behind-the-scenes",
                        "saturday": "Community CTA (lead magnet)"
                    }
                }
            },
            
            "monetization_strategy": {
                "best_performing_models": monetization_models[:3],
                "recommended_model": monetization_models[0]["model"],
                "implementation": {
                    "phase_1_cta": "Comment X for [lead magnet]",
                    "phase_2_conversion": "DM → Personal consultation",
                    "phase_3_product": f"₺{monetization_models[0].get('estimated_price', '5000')}/month service"
                }
            },
            
            "growth_targets": {
                "market_benchmarks": benchmarks,
                "monthly_target_followers": benchmarks.get("avg_weekly_growth_percent", 5) * 4.33,
                "engagement_target": benchmarks.get("avg_engagement_rate", 2.0),
                "posting_frequency_optimal": benchmarks.get("avg_posting_frequency", 3.5)
            },
            
            "turkish_market_insights": turkish_signals,
            
            "next_steps": [
                "1. Implement content calendar (50% top theme + 30% educational + 20% behind-scenes)",
                "2. Setup community lead magnet CTA pipeline (Instagram → Telegram → Sales)",
                "3. Launch first case study carousel (highest engagement monetization model)",
                "4. Track metrics weekly vs benchmarks"
            ]
        }
        
        return playbook
    
    def generate_aggregate_report(self) -> AggregateInsights:
        """
        Final report'u Ekrem'e sunuma hazır format'ta generate et
        """
        
        top_themes = self.calculate_top_content_themes(5)
        monetization_models = self.calculate_monetization_rankings()
        benchmarks = self.calculate_growth_benchmarks()
        turkish_signals = self.identify_turkish_market_signals()
        playbook = self.generate_jarvis_strategic_playbook()
        
        # Rank profiles by composite score
        profile_rankings = []
        for analysis in self.analyses:
            composite_score = (
                (analysis.engagement.engagement_rate * 0.5) +
                (analysis.growth.growth_rate_percent_per_week * 0.3) +
                (1.0 if analysis.monetization.monetization_clarity == "Explicit" else 0.5) * 0.2
            )
            
            profile_rankings.append({
                "handle": analysis.handle,
                "composite_score": composite_score,
                "engagement_rate": f"{analysis.engagement.engagement_rate:.1f}%",
                "weekly_growth": f"{analysis.growth.growth_rate_percent_per_week:.1f}%",
                "monetization_model": analysis.monetization.primary_model,
                "top_theme": analysis.top_performing_theme,
                "follower_count": analysis.growth.follower_count
            })
        
        profile_rankings.sort(key=lambda x: x["composite_score"], reverse=True)
        
        return AggregateInsights(
            analyzed_profiles=len(self.analyses),
            analysis_date=datetime.now().isoformat(),
            top_5_content_themes=top_themes,
            monetization_models_ranking=monetization_models,
            growth_benchmarks=benchmarks,
            turkish_market_specific=turkish_signals,
            jarvis_strategic_playbook=playbook,
            profile_rankings=profile_rankings
        )
    
    @staticmethod
    def _median(values: List[float]) -> float:
        """Calculate median"""
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        if n % 2 == 0:
            return (sorted_vals[n//2 - 1] + sorted_vals[n//2]) / 2
        return sorted_vals[n//2]


# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

class InstagramProfileAnalysisOrchestrator:
    """
    End-to-end workflow:
    1. Ekrem: Profile list'i gönder
    2. Codex: Parallel scrape + analyze
    3. Claude (Me): Strategic synthesis + playbook
    """
    
    def __init__(self, codex_base_url: str = "http://localhost:9090"):
        self.scraper = CodexProfileScraper(codex_base_url)
        self.aggregator = ProfileAnalysisAggregator()
    
    async def analyze_profiles_from_list(
        self,
        instagram_handles: List[str],
        output_path: Path = Path("outputs/profile_analysis")
    ) -> AggregateInsights:
        """
        Full workflow: Ekrem'in verdiği profile list'i analiz et, rapor'u çık
        
        Args:
            instagram_handles: ["leadgenman", "alexlindai", "ohmo.ai", ...]
            output_path: Rapor'u nereye save edecek
        
        Returns:
            AggregateInsights (ready for Ekrem presentation)
        """
        
        logger.info(f"Starting analysis for {len(instagram_handles)} profiles...")
        
        # Step 1: Send to Codex for parallel processing
        logger.info("Sending profiles to Codex for parallel analysis...")
        results = await self.scraper.analyze_profiles_parallel(
            instagram_handles,
            max_concurrent=5
        )
        
        # Step 2: Parse results and aggregate
        logger.info("Aggregating results...")
        for result in results:
            if result:
                try:
                    self.aggregator.add_analysis(result)
                except Exception as e:
                    logger.error(f"Failed to add analysis: {e}")
        
        # Step 3: Generate insights
        logger.info("Generating strategic insights...")
        insights = self.aggregator.generate_aggregate_report()
        
        # Step 4: Save report
        output_path.mkdir(parents=True, exist_ok=True)
        
        report_file = output_path / f"profile_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(asdict(insights), f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Report saved to {report_file}")
        
        return insights


# ============================================================================
# BRIDGE.PY INTEGRATION
# ============================================================================

async def profile_analysis_handler(
    handles_list: List[str],
) -> Dict[str, Any]:
    """
    Bridge.py endpoint: /instagram/analyze-profiles
    
    Request:
    {
      "handles": ["leadgenman", "alexlindai", "ohmo.ai", ...]
    }
    
    Response:
    {
      "status": "completed",
      "profiles_analyzed": 50,
      "top_content_themes": [...],
      "monetization_models": [...],
      "jarvis_playbook": {...},
      "profile_rankings": [...]
    }
    """
    
    orchestrator = InstagramProfileAnalysisOrchestrator()
    
    try:
        insights = await orchestrator.analyze_profiles_from_list(handles_list)
        
        return {
            "status": "completed",
            "profiles_analyzed": insights.analyzed_profiles,
            "analysis_date": insights.analysis_date,
            "top_content_themes": insights.top_5_content_themes,
            "monetization_models": insights.monetization_models_ranking,
            "growth_benchmarks": insights.growth_benchmarks,
            "turkish_market_signals": insights.turkish_market_specific,
            "jarvis_strategic_playbook": insights.jarvis_strategic_playbook,
            "profile_rankings": insights.profile_rankings
        }
    
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return {
            "status": "error",
            "error_message": str(e)
        }


if __name__ == "__main__":
    # Test
    asyncio.run(profile_analysis_handler([
        "leadgenman",
        "alexlindai",
        "ohmo.ai",
        "tenfoldmarc"
    ]))
