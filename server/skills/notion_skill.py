"""
Jarvis Notion Skill - Notion API entegrasyonu
Komutlar: /notion liste | /notion ara [sorgu] | /notion ekle [başlık] | [içerik]
"""
import os
import json
from datetime import datetime, timezone

NOTION_API_KEY = os.environ.get("NOTION_API_KEY", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "")
NOTION_API_BASE = "https://api.notion.com/v1"

KURULUM_TALIMATI = """
Notion henüz bağlı değil. Kurulum:
1. https://www.notion.so/my-integrations adresine git
2. "New integration" oluştur, token'ı kopyala
3. .env dosyasına ekle:
   NOTION_API_KEY=secret_xxxxx
   NOTION_DATABASE_ID=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
4. Notion'da ilgili database'i integration ile paylaş
""".strip()


def _headers():
    return {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }


def _get_pages(query: str = "", limit: int = 5) -> list:
    try:
        import requests
    except ImportError:
        return []

    if query:
        url = f"{NOTION_API_BASE}/search"
        payload = {"query": query, "filter": {"value": "page", "property": "object"}, "page_size": limit}
        r = requests.post(url, headers=_headers(), json=payload, timeout=10)
    else:
        url = f"{NOTION_API_BASE}/databases/{NOTION_DATABASE_ID}/query"
        payload = {"page_size": limit, "sorts": [{"timestamp": "last_edited_time", "direction": "descending"}]}
        r = requests.post(url, headers=_headers(), json=payload, timeout=10)

    if r.status_code != 200:
        return []
    return r.json().get("results", [])


def _page_title(page: dict) -> str:
    props = page.get("properties", {})
    for val in props.values():
        if val.get("type") == "title":
            texts = val.get("title", [])
            if texts:
                return texts[0].get("plain_text", "Başlıksız")
    return page.get("url", "Başlıksız")


def _create_page(title: str, content: str = "") -> dict:
    try:
        import requests
    except ImportError:
        return {}

    children = []
    if content:
        children.append({
            "object": "block",
            "type": "paragraph",
            "paragraph": {"rich_text": [{"type": "text", "text": {"content": content[:2000]}}]}
        })

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "title": {"title": [{"type": "text", "text": {"content": title}}]}
        },
        "children": children
    }
    r = requests.post(f"{NOTION_API_BASE}/pages", headers=_headers(), json=payload, timeout=10)
    if r.status_code == 200:
        return r.json()
    return {}


def handle_notion(args: str, user_id: str = "") -> str:
    if not NOTION_API_KEY or not NOTION_DATABASE_ID:
        return KURULUM_TALIMATI

    try:
        import requests
    except ImportError:
        return "requests kütüphanesi eksik. pip install requests"

    args = (args or "").strip()
    parts = args.split(" ", 1)
    subcommand = parts[0].lower() if parts else "liste"
    rest = parts[1] if len(parts) > 1 else ""

    if subcommand == "liste" or not subcommand:
        pages = _get_pages(limit=5)
        if not pages:
            return "Notion'da sayfa bulunamadı veya bağlantı hatası."
        lines = ["📋 *Son Notion Sayfaları:*"]
        for i, p in enumerate(pages, 1):
            title = _page_title(p)
            url = p.get("url", "")
            lines.append(f"{i}. [{title}]({url})")
        return "\n".join(lines)

    elif subcommand == "ara":
        if not rest:
            return "Kullanım: /notion ara [sorgu]"
        pages = _get_pages(query=rest, limit=5)
        if not pages:
            return f"'{rest}' için sonuç bulunamadı."
        lines = [f"🔍 *'{rest}' Arama Sonuçları:*"]
        for i, p in enumerate(pages, 1):
            title = _page_title(p)
            url = p.get("url", "")
            lines.append(f"{i}. [{title}]({url})")
        return "\n".join(lines)

    elif subcommand == "ekle":
        if not rest:
            return "Kullanım: /notion ekle [başlık] | [içerik]"
        if "|" in rest:
            title, content = rest.split("|", 1)
            title = title.strip()
            content = content.strip()
        else:
            title = rest.strip()
            content = ""
        page = _create_page(title, content)
        if page:
            url = page.get("url", "")
            return f"✅ Sayfa oluşturuldu: [{title}]({url})"
        return "Sayfa oluşturulamadı. Notion API hatası."

    else:
        return "Komutlar: /notion liste | /notion ara [sorgu] | /notion ekle [başlık] | [içerik]"
