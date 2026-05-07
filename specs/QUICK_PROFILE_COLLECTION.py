"""
Instagram Profile Collector — Quick Profile List Builder

Ekrem referans olarak verdiği profilleri organize et + 4-5 daha ekle.
Codex analysis için hazır hale getir.
"""

REFERENCE_PROFILES = {
    "tier_1_proven_models": [
        {
            "handle": "leadgenman",
            "verified": True,
            "category": "Claude Code Education",
            "followers_est": "22K",
            "engagement_est": "2.1%",
            "monetization": "education+lead-gen",
            "reference_count": 1
        },
        {
            "handle": "alexlindai",
            "verified": False,
            "category": "Ad Creative Automation",
            "followers_est": "5K+",
            "engagement_est": "1.2%",
            "monetization": "course+community",
            "reference_count": 1
        },
        {
            "handle": "ohmo.ai",
            "verified": True,
            "category": "AI Agency Stories",
            "followers_est": "10K+",
            "engagement_est": "2.0%",
            "monetization": "news-aggregation",
            "reference_count": 2
        },
        {
            "handle": "tenfoldmarc",
            "verified": True,
            "category": "Claude Code Skills",
            "followers_est": "22K (30-day)",
            "engagement_est": "1.8%",
            "monetization": "community+affiliate",
            "reference_count": 1
        },
    ],
    
    "tier_2_turkish_market": [
        {
            "handle": "akinyilmaz.ai",
            "verified": False,
            "category": "Turkish AI Educator",
            "followers_est": "TBD",
            "engagement_est": "TBD",
            "monetization": "TBD",
            "reference_count": 1,
            "notes": "Native Turkish speaker, market credibility"
        },
        {
            "handle": "esadcom",
            "verified": False,
            "category": "Turkish Entrepreneur/Autonomy",
            "followers_est": "1K+",
            "engagement_est": "1.0%",
            "monetization": "autonomy-narrative",
            "reference_count": 1,
            "notes": "Autonomy narrative = 2.0-2.43x engagement proven"
        },
    ],
    
    "tier_3_developer_focused": [
        {
            "handle": "github.awesome",
            "verified": False,
            "category": "GitHub Projects Aggregator",
            "followers_est": "TBD",
            "engagement_est": "TBD",
            "monetization": "TBD",
            "reference_count": 1,
            "notes": "Developer audience, GitHub integration"
        },
        {
            "handle": "codingknowledge",
            "verified": True,
            "category": "Programming Tips",
            "followers_est": "5K+",
            "engagement_est": "0.8%",
            "monetization": "education",
            "reference_count": 1
        },
        {
            "handle": "githubprojects",
            "verified": False,
            "category": "GitHub Trending",
            "followers_est": "10K+",
            "engagement_est": "1.5%",
            "monetization": "news",
            "reference_count": 1
        },
    ],
    
    "tier_4_international_reference": [
        {
            "handle": "mindwired.ai",
            "verified": False,
            "category": "AI News/Technical",
            "followers_est": "11K+",
            "engagement_est": "2.43%",
            "monetization": "education+news",
            "reference_count": 1,
            "notes": "Technical news focus, high engagement"
        },
        {
            "handle": "power.ai",
            "verified": False,
            "category": "GitHub Resources",
            "followers_est": "4K+",
            "engagement_est": "2.0%",
            "monetization": "resource-sharing",
            "reference_count": 1
        },
    ],
}

# Total: 12 profiles curated
TOTAL_PROFILES = sum(
    len(v) for k, v in REFERENCE_PROFILES.items()
)

PROFILE_HANDLES = [
    p["handle"]
    for tier in REFERENCE_PROFILES.values()
    for p in tier
]

print(f"""
📊 Instagram Profile Collection Ready

Total profiles: {TOTAL_PROFILES}
Tiers:
- Tier 1 (Proven models): 4 profiles
- Tier 2 (Turkish market): 2 profiles
- Tier 3 (Developer-focused): 3 profiles
- Tier 4 (International): 2 profiles

Handles for Codex analysis:
{', '.join([f'@{h}' for h in PROFILE_HANDLES])}

Ready to send to:
  /instagram analyze-profiles @leadgenman,@alexlindai,@ohmo.ai,...

Or use Codex directly:
  codex analyze --profiles="PROFILE_HANDLES" --output=strategic_playbook.json
""")

# Return for programmatic use
if __name__ == "__main__":
    import json
    
    output = {
        "total_profiles": TOTAL_PROFILES,
        "handles": PROFILE_HANDLES,
        "tiers": REFERENCE_PROFILES,
        "codex_command": f"/instagram analyze-profiles {','.join(PROFILE_HANDLES)}"
    }
    
    print(json.dumps(output, indent=2, ensure_ascii=False))
