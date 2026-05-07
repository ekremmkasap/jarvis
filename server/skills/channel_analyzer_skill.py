"""
YouTube Channel Analyzer Skill
Digital Academy Türkiye (ve diğer kanallar) için detaylı video analizi
"""

import os
from googleapiclient.discovery import build
from datetime import datetime, timedelta

API_KEY = os.environ.get("YOUTUBE_API_KEY", "")


def analyze_channel(channel_handle: str, days: int = 90) -> dict:
    """YouTube kanalını analiz et: video sayısı, tema, istatistikler"""
    if not API_KEY:
        return {"error": "YOUTUBE_API_KEY not set"}

    try:
        youtube = build('youtube', 'v3', developerKey=API_KEY)

        # Channel ID'yi bul
        search_request = youtube.search().list(
            q=channel_handle,
            type="channel",
            part="snippet",
            maxResults=1
        )
        search_response = search_request.execute()

        if not search_response.get('items'):
            return {"error": "Channel not found"}

        channel_id = search_response['items'][0]['id']['channelId']
        channel_title = search_response['items'][0]['snippet']['title']

        # Tarihi aralığı hesapla
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)

        # Video listesi çek
        videos_request = youtube.search().list(
            channelId=channel_id,
            type="video",
            part="snippet",
            maxResults=50,
            order="date",
            publishedAfter=start_date.isoformat() + "Z",
            publishedBefore=end_date.isoformat() + "Z"
        )
        videos_response = videos_request.execute()

        videos = []
        themes = {
            'Claude Code': 0,
            'AI Agents': 0,
            'Video/Visual AI': 0,
            'Automation': 0,
            'Business': 0,
            'Other': 0
        }

        for item in videos_response.get('items', []):
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            published = item['snippet']['publishedAt'][:10]

            # Tema sınıflandırması
            title_lower = title.lower()
            if 'claude code' in title_lower or 'codex' in title_lower:
                theme = 'Claude Code'
            elif 'ajan' in title_lower or 'agent' in title_lower:
                theme = 'AI Agents'
            elif 'veo' in title_lower or 'kling' in title_lower or 'sora' in title_lower or 'video' in title_lower:
                theme = 'Video/Visual AI'
            elif 'otomasyon' in title_lower:
                theme = 'Automation'
            elif 'sirketi' in title_lower or 'musteri' in title_lower or 'para' in title_lower:
                theme = 'Business'
            else:
                theme = 'Other'

            themes[theme] += 1
            videos.append({
                'id': video_id,
                'title': title,
                'published': published,
                'theme': theme
            })

        return {
            "channel_id": channel_id,
            "channel_title": channel_title,
            "total_videos": len(videos),
            "date_range": f"{start_date.date()} to {end_date.date()}",
            "themes": themes,
            "videos": videos,
        }

    except Exception as e:
        return {"error": str(e)}


def format_channel_report(result: dict) -> str:
    """Channel analiz raporunu format et"""
    if "error" in result:
        return f"Channel analiz hatasi: {result['error']}"

    nl = chr(10)
    output = []

    output.append(f"KANAL: {result['channel_title']}")
    output.append(f"Zaman Araligi: {result['date_range']}")
    output.append(f"Toplam Video: {result['total_videos']}")
    output.append("")

    output.append("TEMA DAGITIMI:")
    for theme, count in result['themes'].items():
        if count > 0:
            pct = (count / result['total_videos']) * 100
            output.append(f"  {theme}: {count} ({pct:.1f}%)")

    output.append("")
    output.append("EN SON VIDEOLAR:")
    for v in result['videos'][:5]:
        output.append(f"  - [{v['published']}] {v['title'][:60]}")

    return nl.join(output)


def call_skill(args: str = "") -> str:
    """Bridge komut handler"""
    if not args.strip():
        return "Kullanim: /channel-analiz @kanalAdi"

    channel = args.strip()
    result = analyze_channel(channel, days=90)
    return format_channel_report(result)
