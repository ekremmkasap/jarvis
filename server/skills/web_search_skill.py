#!/usr/bin/env python3
"""
Web Search Skill - Jarvis
DuckDuckGo ile web arama (POST) ve URL scraping.
"""
import json
import urllib.request
import urllib.parse
import urllib.error
import re
import logging

log = logging.getLogger("web_search")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:115.0) Gecko/20100101 Firefox/115.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "tr-TR,tr;q=0.9,en;q=0.8",
}


def web_search(query: str, max_results: int = 5) -> str:
    """DuckDuckGo ile web aramasi. API key gerekmez."""
    lines = []

    # 1. Instant Answer API (ozet/direkt cevap)
    try:
        url = ("https://api.duckduckgo.com/?q="
               + urllib.parse.quote(query)
               + "&format=json&no_redirect=1&no_html=1&skip_disambig=1")
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        abstract = data.get("AbstractText", "").strip()
        answer = data.get("Answer", "").strip()
        if answer:
            lines.append("Direkt Cevap: " + answer)
        if abstract:
            lines.append("Ozet: " + abstract[:400])
    except Exception as e:
        log.warning("DDG instant hatasi: %s", e)

    # 2. Lite HTML arama (POST)
    try:
        post_data = urllib.parse.urlencode({"q": query}).encode()
        post_headers = dict(HEADERS)
        post_headers["Content-Type"] = "application/x-www-form-urlencoded"
        req2 = urllib.request.Request(
            "https://lite.duckduckgo.com/lite/",
            data=post_data,
            headers=post_headers
        )
        with urllib.request.urlopen(req2, timeout=15) as resp2:
            html = resp2.read().decode("utf-8", errors="replace")

        link_pattern = re.compile(
            r'href="(https?://[^"]{10,200})"[^>]*class=\'result-link\'>(.*?)</a>',
            re.DOTALL)
        snippet_pattern = re.compile(
            r"class='result-snippet'[^>]*>\s*(.*?)\s*</td>",
            re.DOTALL)

        links = link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        if links:
            lines.append("\nSonuclar:")
            for i, (href, title) in enumerate(links[:max_results], 1):
                title_clean = re.sub(r"<[^>]+>", "", title).strip()
                snippet_clean = ""
                if i - 1 < len(snippets):
                    raw_snip = snippets[i - 1]
                    snippet_clean = re.sub(r"<[^>]+>", "", raw_snip).strip()
                    snippet_clean = re.sub(r"&#x27;", "'", snippet_clean)
                    snippet_clean = re.sub(r"&amp;", "&", snippet_clean)
                    snippet_clean = snippet_clean[:150]
                lines.append(str(i) + ". " + title_clean)
                lines.append("   " + href)
                if snippet_clean:
                    lines.append("   " + snippet_clean)
        else:
            # Fallback: sadece linkleri topla
            hrefs = re.findall(r"href='(https?://[^']{10,200})'", html)
            hrefs = [h for h in hrefs if "duckduckgo" not in h][:max_results]
            if hrefs:
                lines.append("\nBulunan Linkler:")
                for i, h in enumerate(hrefs, 1):
                    lines.append(str(i) + ". " + h)
    except Exception as e:
        log.warning("DDG lite hatasi: %s", e)

    result = "\n".join(lines)
    return result if len(result) > 30 else "Sonuc bulunamadi: " + query


def scrape_url(url: str, max_chars: int = 3000) -> str:
    """Verilen URL'den temiz metin ceker."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        html = re.sub(r"<script[^>]*>.*?</script>", " ", html,
                      flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r"<style[^>]*>.*?</style>", " ", html,
                      flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", html)
        text = re.sub(r"\s+", " ", text).strip()

        if len(text) > max_chars:
            return text[:max_chars] + "..."
        return text
    except urllib.error.URLError as e:
        return "URL erisilemedi: " + str(e)
    except Exception as e:
        return "Scrape hatasi: " + str(e)


if __name__ == "__main__":
    print(web_search("Python asyncio nedir"))
    print("\n---\n")
    print(scrape_url("https://example.com")[:200])
