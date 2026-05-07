"""
Ekrem's Instagram Following List Analyzer — AI-Purpose Detection

Exports Ekrem'in takip ettiği hesapları, AI amaçlı olanları identify ediyor.
Sonra Codex'e gönderip advanced strategic analysis yapıyor.
"""

import asyncio
import json
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

class EkremFollowingAnalyzer:
    """
    Ekrem @ekremmkasap'ın takip ettiği hesapları analyze et.
    AI-purpose detection + strategic clustering.
    """
    
    def __init__(self, instagram_username: str = "ekremmkasap"):
        self.username = instagram_username
        self.following_list = []
        self.ai_focused = []
        self.non_ai = []
        self.analysis_date = datetime.now().isoformat()
    
    async def export_following_list(self) -> list:
        """
        Step 1: Ekrem'in takip ettiği 200 hesabı export et
        
        Method 1: instaloader (requires login)
        Method 2: Instagram Graph API (requires business account)
        Method 3: Manual export (UI copy-paste)
        
        Return: List of handles with metadata
        """
        
        logger.info(f"Exporting following list for @{self.username}...")
        
        try:
            import instaloader
            
            # Login required
            session = instaloader.Instaloader()
            # session.login(username, password)  # Ekrem provides
            
            # Get profile
            profile = instaloader.Profile.from_username(session, self.username)
            
            # Get following
            following_handles = []
            for following_profile in profile.get_followers():
                following_handles.append({
                    "handle": following_profile.username,
                    "full_name": following_profile.full_name,
                    "bio": following_profile.biography,
                    "followers": following_profile.followers,
                    "follower_count": following_profile.follower_count,
                    "is_verified": following_profile.is_verified,
                })
            
            self.following_list = following_handles[:200]  # Last 200
            logger.info(f"✓ Exported {len(self.following_list)} following accounts")
            
            return self.following_list
        
        except ImportError:
            logger.error("instaloader not installed. Install: pip install instaloader")
            return None
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return None
    
    async def detect_ai_purpose(self, account: dict) -> dict:
        """
        Bir hesabı AI-amaçlı olup olmadığını detect et
        
        Signals:
        - Bio keywords: AI, Claude, automation, code, developer, startup
        - Handle keywords: ai, code, dev, automation, gpt, claude
        - Content hints: (requires scraping bios + recent posts)
        """
        
        bio = account.get('bio', '').lower()
        handle = account.get('handle', '').lower()
        full_name = account.get('full_name', '').lower()
        
        ai_keywords = [
            'ai', 'artificial intelligence', 'claude', 'gpt', 'llm',
            'automation', 'code', 'developer', 'dev', 'startup',
            'python', 'javascript', 'ml', 'machine learning', 'deep learning',
            'neural', 'model', 'api', 'github', 'opensource', 'saas',
            'product', 'tech', 'ai-powered', 'codex', 'agent'
        ]
        
        score = 0
        matched_keywords = []
        
        # Score bio
        for keyword in ai_keywords:
            if keyword in bio:
                score += 3
                matched_keywords.append(f"bio:{keyword}")
        
        # Score handle
        for keyword in ai_keywords:
            if keyword in handle:
                score += 2
                matched_keywords.append(f"handle:{keyword}")
        
        # Score full_name
        for keyword in ai_keywords:
            if keyword in full_name:
                score += 1
                matched_keywords.append(f"name:{keyword}")
        
        # Determine category
        if score >= 5:
            category = "AI-focused"
        elif score >= 2:
            category = "AI-adjacent"
        else:
            category = "Non-AI"
        
        return {
            "handle": account.get('handle'),
            "full_name": account.get('full_name'),
            "bio": account.get('bio'),
            "followers": account.get('follower_count', 0),
            "verified": account.get('is_verified', False),
            "ai_score": score,
            "category": category,
            "matched_keywords": matched_keywords,
            "metadata": account
        }
    
    async def analyze_following_list(self) -> dict:
        """
        Full analysis: categorize 200 accounts
        """
        
        logger.info("Analyzing following list for AI-purpose...")
        
        self.ai_focused = []
        self.non_ai = []
        
        for account in self.following_list:
            analysis = await self.detect_ai_purpose(account)
            
            if analysis['category'] == "AI-focused":
                self.ai_focused.append(analysis)
            else:
                self.non_ai.append(analysis)
        
        # Sort by AI score
        self.ai_focused.sort(key=lambda x: x['ai_score'], reverse=True)
        
        logger.info(f"✓ Analysis complete: {len(self.ai_focused)} AI-focused, {len(self.non_ai)} non-AI")
        
        return {
            "total_following": len(self.following_list),
            "ai_focused_count": len(self.ai_focused),
            "ai_percentage": f"{(len(self.ai_focused) / len(self.following_list) * 100):.1f}%",
            "ai_focused": self.ai_focused[:50],  # Top 50 for report
            "non_ai_sample": self.non_ai[:10],  # Sample of non-AI
        }
    
    async def generate_strategic_clusters(self) -> dict:
        """
        Group AI accounts into strategic clusters
        
        Clusters:
        - Educators (tutorials, guides, tips)
        - Builders (projects, tools, products)
        - Researchers (papers, analysis, trends)
        - Entrepreneurs (startups, scale, growth)
        - Influencers (news, announcements, trending)
        """
        
        clusters = {
            "educators": {"keywords": ["tutorial", "learn", "guide", "course", "tips"], "accounts": []},
            "builders": {"keywords": ["build", "product", "tool", "code", "dev"], "accounts": []},
            "researchers": {"keywords": ["research", "paper", "analysis", "science", "data"], "accounts": []},
            "entrepreneurs": {"keywords": ["startup", "founder", "scale", "growth", "business"], "accounts": []},
            "influencers": {"keywords": ["news", "trending", "ai", "announce", "breaking"], "accounts": []},
        }
        
        for account in self.ai_focused:
            bio = account['bio'].lower()
            matched = False
            
            for cluster_name, cluster_data in clusters.items():
                for keyword in cluster_data['keywords']:
                    if keyword in bio or keyword in account['handle'].lower():
                        cluster_data['accounts'].append(account)
                        matched = True
                        break
                if matched:
                    break
            
            # Default cluster if no match
            if not matched:
                clusters["influencers"]['accounts'].append(account)
        
        return clusters
    
    async def generate_report(self) -> dict:
        """
        Final report: Ekrem'in takip ettiği AI accounts'ın strategik analiz'i
        """
        
        clusters = await self.generate_strategic_clusters()
        
        report = {
            "analyzed_date": self.analysis_date,
            "username": self.username,
            "total_following": len(self.following_list),
            
            "summary": {
                "ai_focused_count": len(self.ai_focused),
                "ai_percentage": f"{(len(self.ai_focused) / len(self.following_list) * 100):.1f}%",
                "top_topic": self._get_top_topic(),
            },
            
            "top_20_ai_accounts": [
                {
                    "rank": i+1,
                    "handle": acc['handle'],
                    "followers": f"{acc['followers']:,}" if acc['followers'] else 'N/A',
                    "ai_score": acc['ai_score'],
                    "keywords": ', '.join([k.split(':')[1] for k in acc['matched_keywords'][:3]])
                }
                for i, acc in enumerate(self.ai_focused[:20])
            ],
            
            "clusters": {
                name: {
                    "count": len(cluster_data['accounts']),
                    "top_accounts": [
                        {"handle": acc['handle'], "followers": acc['followers']}
                        for acc in cluster_data['accounts'][:5]
                    ]
                }
                for name, cluster_data in clusters.items()
            },
            
            "insights": [
                f"Ekrem é seguindo {len(self.ai_focused)} AI-focused accounts ({(len(self.ai_focused) / len(self.following_list) * 100):.0f}%)",
                f"Top cluster: {max(clusters, key=lambda x: len(clusters[x]['accounts']))} ({max([len(c['accounts']) for c in clusters.values()])} accounts)",
                "Ekrem'in strategy: Mix of educators, builders, researchers ve entrepreneurs",
                f"Average followers (AI accounts): {sum(a['followers'] for a in self.ai_focused) // len(self.ai_focused):,}" if self.ai_focused else "N/A",
            ],
            
            "recommendations_for_jarvis": [
                f"Model content after top 10 AI educators: {', '.join([a['handle'] for a in self.ai_focused[:5] if 'educator' in a.get('category', '')])}",
                f"Monetization insight: {clusters['entrepreneurs']['count']} entrepreneurs = market demand signal",
                f"Collaboration candidates: {clusters['builders']['count']} builders + {clusters['researchers']['count']} researchers",
            ]
        }
        
        return report
    
    def _get_top_topic(self) -> str:
        """Find most common AI keyword"""
        keyword_count = {}
        for account in self.ai_focused:
            for keyword in account['matched_keywords']:
                kw = keyword.split(':')[1]
                keyword_count[kw] = keyword_count.get(kw, 0) + 1
        
        if keyword_count:
            return max(keyword_count, key=keyword_count.get)
        return "General AI"


# ============================================================================
# MANUAL INPUT: If instaloader doesn't work, use this
# ============================================================================

EKREM_FOLLOWING_MANUAL = """
Ekrem, eğer instaloader çalışmazsa, Instagram app'den şu adımları yap:
1. Profil → Following
2. Üst 50-100 hesabı copy-paste et
3. Aşağıdaki list'e yapıştır

handles = [
    # Paste Instagram handles here (one per line, @ ile başla)
    # @leadgenman
    # @alexlindai
    # @ohmo.ai
    # ...
]
"""

async def main():
    analyzer = EkremFollowingAnalyzer(instagram_username="ekremmkasap")
    
    # Step 1: Export (requires instaloader + login)
    following = await analyzer.export_following_list()
    
    if not following:
        print("❌ Instaloader export failed. Use manual method:")
        print(EKREM_FOLLOWING_MANUAL)
        return
    
    # Step 2: Analyze
    analysis = await analyzer.analyze_following_list()
    print(f"✓ AI-focused: {analysis['ai_focused_count']} ({analysis['ai_percentage']})")
    print(f"✓ Non-AI: {len(analyzer.non_ai)}")
    
    # Step 3: Report
    report = await analyzer.generate_report()
    
    # Save report
    output_path = Path("outputs/ekrem_following_analysis")
    output_path.mkdir(parents=True, exist_ok=True)
    
    report_file = output_path / f"ekrem_ai_following_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Report saved: {report_file}")
    print(json.dumps(report, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main())
