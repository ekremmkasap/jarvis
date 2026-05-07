"""
Universal Social Media Profile Scraper Skill

Verilen handle/URL'den tüm profile datası çekiyor:
- Instagram: followers, posts, engagement, bios, links
- YouTube: subscribers, videos, views, playlists
- Output: JSON (Codex analysis'e ready)
"""

import asyncio
import json
import logging
import os
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import re

logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class InstagramPost:
    """Single Instagram post data"""
    post_id: str
    caption: str
    timestamp: str
    likes: int
    comments: int
    shares: int
    engagement_rate: float
    image_url: Optional[str] = None
    video_url: Optional[str] = None


@dataclass
class InstagramProfileData:
    """Complete Instagram profile extraction"""
    handle: str
    profile_url: str
    full_name: str
    bio: str
    followers_count: int
    following_count: int
    posts_count: int
    is_verified: bool
    is_business_account: bool
    profile_pic_url: str
    
    # Engagement metrics (required)
    avg_engagement_rate: float
    avg_likes_per_post: float
    avg_comments_per_post: float
    total_engagement_last_30_days: int
    
    # Optional fields (with defaults)
    website_url: Optional[str] = None
    recent_posts: List[InstagramPost] = field(default_factory=list)
    hashtags_used: Dict[str, int] = field(default_factory=dict)  # hashtag: count
    content_themes: List[str] = field(default_factory=list)
    posting_frequency_per_week: float = 0.0
    follower_growth_percent_monthly: float = 0.0
    audience_demographics: Dict[str, float] = field(default_factory=dict)
    has_shopping_feature: bool = False
    has_affiliate_links: bool = False
    has_sponsored_posts: bool = False
    estimated_monthly_revenue_range: Optional[str] = None
    
    extraction_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class YouTubeVideo:
    """Single YouTube video"""
    video_id: str
    title: str
    upload_date: str
    views: int
    likes: int
    comments: int
    duration_seconds: int
    engagement_rate: float


@dataclass
class YouTubeChannelData:
    """Complete YouTube channel extraction"""
    channel_id: str
    channel_url: str
    channel_name: str
    description: str
    subscribers_count: int
    total_videos: int
    total_views: int
    is_verified: bool
    profile_pic_url: str
    banner_url: Optional[str] = None
    
    # Engagement metrics
    avg_views_per_video: float = 0.0
    avg_engagement_rate: float = 0.0
    avg_upload_frequency_per_week: float = 0.0
    
    # Content analysis
    recent_videos: List[YouTubeVideo] = field(default_factory=list)
    playlist_count: int = 0
    video_categories: Dict[str, int] = field(default_factory=dict)  # category: count
    
    # Audience analysis
    subscriber_growth_percent_monthly: float = 0.0
    estimated_audience_location: Dict[str, float] = field(default_factory=dict)
    
    # Monetization signals
    is_partner_program_eligible: bool = False
    has_super_chat_enabled: bool = False
    estimated_monthly_revenue_range: Optional[str] = None
    
    extraction_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# INSTAGRAM SCRAPER
# ============================================================================

class InstagramProfileScraper:
    """
    Instagram profile'ş complete data extraction
    
    Methods:
    1. instaloader (requires login, most complete)
    2. Instagram Graph API (requires business account)
    3. Web scraping (public data only, HTML parsing)
    """
    
    def __init__(self):
        self.method = None  # Will be determined based on available libraries
        # Try multiple env key names for flexibility
        self.username = (
            os.environ.get("INSTAGRAM_USERNAME")
            or os.environ.get("INSTAGRAM_USER")
            or ""
        ).strip()
        self.password = (
            os.environ.get("INSTAGRAM_PASSWORD")
            or os.environ.get("INSTAGRAM_PASS")
            or ""
        ).strip()
    
    async def scrape_profile(self, handle: str) -> Optional[InstagramProfileData]:
        """
        Main method: Scrape complete Instagram profile
        
        Input: handle (with or without @)
        Output: InstagramProfileData (JSON-serializable)
        """
        
        if handle.startswith('@'):
            handle = handle[1:]
        
        logger.info(f"Scraping Instagram profile: @{handle}")
        
        try:
            # Try instaloader first (most complete)
            return await self._scrape_with_instaloader(handle)
        except Exception as e:
            logger.warning(f"Instaloader failed: {e}, trying Graph API...")
            try:
                return await self._scrape_with_graph_api(handle)
            except Exception as e2:
                logger.error(f"All methods failed: {e2}")
                return None
    
    async def _scrape_with_instaloader(self, handle: str) -> Optional[InstagramProfileData]:
        """
        Most complete method (requires login)
        """
        try:
            import instaloader
            
            # Initialize loader (may need credentials)
            L = instaloader.Instaloader(quiet=True)
            if self.username and self.password:
                try:
                    L.login(self.username, self.password)
                except Exception as login_err:
                    logger.warning(f"Instagram login failed, falling back to public data: {login_err}")
                    # Continue without auth for public profiles
                    pass
            
            # Try to load profile
            profile = instaloader.Profile.from_username(L.context, handle)
            
            # Get recent posts
            posts_data = []
            for post in profile.get_posts():
                if len(posts_data) >= 30:  # Last 30 posts
                    break
                
                posts_data.append(InstagramPost(
                    post_id=post.shortcode,
                    caption=post.caption or "",
                    timestamp=post.date_utc.isoformat(),
                    likes=post.likes,
                    comments=post.comments,
                    shares=post.shares_count if hasattr(post, 'shares_count') else 0,
                    engagement_rate=((post.likes + post.comments) / (profile.followers + 1)) * 100,
                    image_url=post.url if not post.is_video else None,
                    video_url=post.url if post.is_video else None
                ))
            
            # Calculate metrics
            total_likes = sum(p.likes for p in posts_data)
            total_comments = sum(p.comments for p in posts_data)
            
            return InstagramProfileData(
                handle=profile.username,
                profile_url=f"https://instagram.com/{profile.username}",
                full_name=profile.full_name,
                bio=profile.biography,
                followers_count=profile.followers,
                following_count=profile.followees,
                posts_count=profile.mediacount,
                is_verified=profile.is_verified,
                is_business_account=profile.is_business_account,
                profile_pic_url=profile.profile_pic_url,
                website_url=profile.website,
                avg_engagement_rate=(total_likes + total_comments) / (len(posts_data) * (profile.followers + 1)) * 100 if posts_data else 0,
                avg_likes_per_post=total_likes / len(posts_data) if posts_data else 0,
                avg_comments_per_post=total_comments / len(posts_data) if posts_data else 0,
                total_engagement_last_30_days=total_likes + total_comments,
                recent_posts=posts_data,
                has_shopping_feature=profile.has_channel,
            )
        
        except ImportError:
            raise Exception("instaloader not installed: pip install instaloader")
        except Exception as e:
            raise e
    
    async def _scrape_with_graph_api(self, handle: str) -> Optional[InstagramProfileData]:
        """
        Graph API method (requires business account + access token)
        """
        logger.info(f"Graph API method not yet implemented for public profiles")
        # TODO: Implement Meta Graph API integration
        return None


# ============================================================================
# YOUTUBE SCRAPER
# ============================================================================

class YouTubeChannelScraper:
    """
    YouTube channel complete data extraction
    
    Methods:
    1. YouTube Data API (official, requires API key)
    2. pytube (for video data)
    3. Web scraping (public data)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("YOUTUBE_API_KEY", "").strip()
    
    async def scrape_channel(self, channel_url: str) -> Optional[YouTubeChannelData]:
        """
        Main method: Scrape complete YouTube channel
        
        Input: channel_url (https://youtube.com/c/ChannelName or @handle or UC...)
        Output: YouTubeChannelData (JSON-serializable)
        """
        
        logger.info(f"Scraping YouTube channel: {channel_url}")
        
        # Parse channel identifier
        channel_id = self._extract_channel_id(channel_url)
        
        if not channel_id:
            logger.error("Could not extract channel ID from URL")
            return None
        
        try:
            if self.api_key:
                return await self._scrape_with_youtube_api(channel_id)
            else:
                logger.info("API key not available, using web scraping")
                return await self._scrape_with_web(channel_url)
        except Exception as e:
            logger.error(f"YouTube scraping failed: {e}")
            return None
    
    def _extract_channel_id(self, url: str) -> Optional[str]:
        """Extract channel ID from various YouTube URL formats"""
        
        # Format 1: UC... (direct channel ID)
        if url.startswith("UC"):
            return url
        
        # Format 2: https://youtube.com/@handle
        match = re.search(r'youtube\.com/@([\w-]+)', url)
        if match:
            return match.group(1)  # Will need conversion
        
        # Format 3: https://youtube.com/c/ChannelName
        match = re.search(r'youtube\.com/c/([\w-]+)', url)
        if match:
            return match.group(1)
        
        # Format 4: https://youtube.com/channel/UC...
        match = re.search(r'channel/(UC[\w-]+)', url)
        if match:
            return match.group(1)
        
        return None
    
    async def _scrape_with_youtube_api(self, channel_id: str) -> Optional[YouTubeChannelData]:
        """
        YouTube Data API v3 method (requires API key)
        """
        try:
            from googleapiclient.discovery import build
            
            youtube = build('youtube', 'v3', developerKey=self.api_key)
            
            # Get channel info
            request = youtube.channels().list(
                part='statistics,snippet,brandingSettings',
                id=channel_id
            )
            response = request.execute()
            
            if not response['items']:
                logger.error(f"Channel not found: {channel_id}")
                return None
            
            channel = response['items'][0]
            stats = channel['statistics']
            snippet = channel['snippet']
            
            # Get recent videos
            videos_request = youtube.search().list(
                part='snippet',
                channelId=channel_id,
                maxResults=30,
                order='date',
                type='video'
            )
            videos_response = videos_request.execute()
            
            videos_data = []
            for video in videos_response.get('items', []):
                video_id = video['id']['videoId']
                
                # Get video stats
                stats_request = youtube.videos().list(
                    part='statistics,snippet',
                    id=video_id
                )
                stats_response = stats_request.execute()
                
                if stats_response['items']:
                    v_stats = stats_response['items'][0]['statistics']
                    v_snippet = stats_response['items'][0]['snippet']
                    
                    videos_data.append(YouTubeVideo(
                        video_id=video_id,
                        title=v_snippet['title'],
                        upload_date=v_snippet['publishedAt'],
                        views=int(v_stats.get('viewCount', 0)),
                        likes=int(v_stats.get('likeCount', 0)),
                        comments=int(v_stats.get('commentCount', 0)),
                        duration_seconds=0,  # Would need contentDetails
                        engagement_rate=0.0  # Calculate after collection
                    ))
            
            return YouTubeChannelData(
                channel_id=channel_id,
                channel_url=f"https://youtube.com/channel/{channel_id}",
                channel_name=snippet['title'],
                description=snippet['description'],
                subscribers_count=int(stats.get('subscriberCount', 0)),
                total_videos=int(stats.get('videoCount', 0)),
                total_views=int(stats.get('viewCount', 0)),
                is_verified=snippet.get('customUrl', '').startswith('@'),
                profile_pic_url=snippet['thumbnails']['default']['url'],
                recent_videos=videos_data,
            )
        
        except ImportError:
            raise Exception("google-api-client not installed: pip install google-api-python-client")
        except Exception as e:
            raise e
    
    async def _scrape_with_web(self, channel_url: str) -> Optional[YouTubeChannelData]:
        """
        Web scraping method (public data, requires parsing)
        """
        logger.info("Web scraping method not yet implemented")
        # TODO: Implement web scraping with BeautifulSoup/Selenium
        return None


# ============================================================================
# UNIFIED SCRAPER
# ============================================================================

class UniversalProfileScraper:
    """
    Unified interface for Instagram + YouTube scraping
    """
    
    def __init__(self):
        self.instagram = InstagramProfileScraper()
        self.youtube = YouTubeChannelScraper()
    
    async def scrape(self, url_or_handle: str, platform: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Auto-detect platform and scrape profile
        
        Input: URL or handle (@username, channel URL, etc.)
        Output: Platform-specific data (JSON)
        """
        
        # Auto-detect platform
        if not platform:
            if '@' in url_or_handle or 'instagram' in url_or_handle.lower():
                platform = 'instagram'
            elif 'youtube' in url_or_handle.lower() or 'youtu.be' in url_or_handle.lower():
                platform = 'youtube'
            else:
                logger.error("Could not auto-detect platform. Specify: instagram or youtube")
                return None
        
        if platform == 'instagram':
            data = await self.instagram.scrape_profile(url_or_handle)
            return asdict(data) if data else None
        
        elif platform == 'youtube':
            data = await self.youtube.scrape_channel(url_or_handle)
            return asdict(data) if data else None
        
        else:
            logger.error(f"Unknown platform: {platform}")
            return None


# ============================================================================
# BRIDGE INTEGRATION
# ============================================================================

async def scrape_profile_handler(
    url_or_handle: str,
    platform: Optional[str] = None,
    output_format: str = "json"
) -> Dict[str, Any]:
    """
    Bridge.py handler for profile scraping
    
    Request (Telegram):
    /scrape-profile @leadgenman
    /scrape-profile https://youtube.com/c/ChannelName
    
    Response: Complete profile data (JSON)
    """
    
    scraper = UniversalProfileScraper()
    
    try:
        data = await scraper.scrape(url_or_handle, platform)
        
        if not data:
            return {
                "status": "error",
                "error": f"Failed to scrape profile: {url_or_handle}"
            }
        
        # Save to file
        output_path = Path("outputs/profile_scrapes")
        output_path.mkdir(parents=True, exist_ok=True)
        
        filename = f"{data.get('handle') or data.get('channel_id')}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = output_path / filename
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"✓ Profile scraped and saved: {filepath}")
        
        return {
            "status": "completed",
            "platform": platform,
            "data_summary": {
                "handle": data.get('handle') or data.get('channel_name'),
                "followers": data.get('followers_count') or data.get('subscribers_count'),
                "posts": len(data.get('recent_posts') or data.get('recent_videos') or []),
                "engagement_rate": f"{data.get('avg_engagement_rate', 0):.2f}%",
            },
            "file_saved": str(filepath)
        }
    
    except Exception as e:
        logger.error(f"Scraping error: {e}")
        return {
            "status": "error",
            "error": str(e)
        }


if __name__ == "__main__":
    # Test
    asyncio.run(scrape_profile_handler("@leadgenman", "instagram"))
