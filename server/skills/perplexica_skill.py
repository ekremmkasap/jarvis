#!/usr/bin/env python3
"""
PERPLEXICA SKILL - AI Destekli Web Arama
DuckDuckGo arama + sayfa icerik cekme + Ollama ozet
Perplexica'nin yaptigi seyi Docker/Node.js olmadan Python ile yapar.
Kullanim: /ara [sorgu]
"""
import json
import re
import sys
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.parse import quote_plus, urlencode
from urllib.error import URLError
from html.parser import HTMLParser

# ── HTML Temizleyici ─────────────────────────────────────────────────

class _TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []
        self._skip = False
        self._skip_tags = {'script', 'style', 'nav', 'footer', 'header', 'aside'}

    def handle_starttag(self, tag, attrs):
        if tag in self._skip_tags:
            self._skip = True

    def handle_endtag(self, tag):
        if tag in self._skip_tags:
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            text = data.strip()
            if len(text) > 20:
                self.text_parts.append(text)

    def get_text(self):
        return ' '.join(self.text_parts)


def _fetch_page(url: str, timeout: int = 6) -> str:
    """Bir URL'den metin icerik cek."""
    try:
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml',
            'Accept-Language': 'tr-TR,tr;q=0.9,en;q=0.8',
        })
        with urlopen(req, timeout=timeout) as resp:
            raw = resp.read(50000)  # Max 50KB
            charset = 'utf-8'
            ct = resp.headers.get('Content-Type', '')
            if 'charset=' in ct:
                charset = ct.split('charset=')[-1].strip().split(';')[0]
            html = raw.decode(charset, errors='ignore')
        parser = _TextExtractor()
        parser.feed(html)
        text = parser.get_text()
        # Ilk 2000 karakter yeterli
        return text[:2000]
    except Exception:
        return ''


def _duckduckgo_search(query: str, max_results: int = 5) -> list:
    """DuckDuckGo HTML arama - sonuclari parse et."""
    results = []
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}&kl=tr-tr"
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept-Language': 'tr-TR,tr;q=0.9',
        })
        with urlopen(req, timeout=10) as resp:
            html = resp.read(100000).decode('utf-8', errors='ignore')

        # Sonuclari regex ile cek
        # DDG HTML: <a class="result__a" href="...">title</a> + snippet
        links = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>([^<]+)</a>', html)
        snippets = re.findall(r'class="result__snippet"[^>]*>([^<]+(?:<[^>]+>[^<]*</[^>]+>)*[^<]*)</[^>]+>', html)

        # Alternatif pattern
        if not links:
            links = re.findall(r'href="(https?://[^"]+)"[^>]*class="result__url"', html)

        # DDG redirect linklerini temizle
        clean_links = []
        for href, *rest in (links if links else []):
            if href.startswith('http') and 'duckduckgo' not in href:
                title = rest[0] if rest else href
                clean_links.append({'url': href, 'title': title.strip()})
            elif 'uddg=' in href:
                import urllib.parse
                parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                real = parsed.get('uddg', [None])[0]
                if real:
                    title = rest[0] if rest else real
                    clean_links.append({'url': real, 'title': title.strip()})

        # Snippetlari temizle
        clean_snippets = []
        for s in snippets:
            text = re.sub(r'<[^>]+>', '', s).strip()
            if text:
                clean_snippets.append(text)

        # Birlestir
        for i, link in enumerate(clean_links[:max_results]):
            link['snippet'] = clean_snippets[i] if i < len(clean_snippets) else ''
            results.append(link)

    except Exception as e:
        pass

    return results


# ── ANA SINIF ────────────────────────────────────────────────────────

class PerplexicaSkill:
    """
    Perplexica benzeri AI arama:
    1. DuckDuckGo ile sonuclar al
    2. Ust 3 sayfanin icerigini cek
    3. Ollama ile kapsamli ozet uret
    4. Kaynaklarla birlikte don
    """

    def __init__(self, call_ollama_fn):
        self.call_ollama = call_ollama_fn

    def search(self, query: str) -> str:
        query = query.strip()
        if not query:
            return '*Kullanim:* `/ara [sorgu]`\n*Ornek:* `/ara Istanbul konut fiyatlari 2025`'

        # ADIM 1: Arama
        results = _duckduckgo_search(query, max_results=5)

        if not results:
            return f'Arama sonucu bulunamadi: {query}\nDDG erisim sorunu olabilir.'

        # ADIM 2: Ust 3 sayfadan icerik cek
        contents = []
        for r in results[:3]:
            snippet = r.get('snippet', '')
            page_text = ''
            if r.get('url'):
                page_text = _fetch_page(r['url'])
            combined = (snippet + ' ' + page_text)[:800]
            if combined.strip():
                contents.append({
                    'title': r.get('title', r['url']),
                    'url': r['url'],
                    'content': combined
                })

        # ADIM 3: Ollama ile ozet
        context_parts = []
        for i, c in enumerate(contents, 1):
            context_parts.append(f"[Kaynak {i}] {c['title']}\n{c['content']}")
        context = '\n\n'.join(context_parts)

        prompt = (
            f"Soru: {query}\n\n"
            f"Kaynaklar:\n{context[:2500]}\n\n"
            "Yukardaki kaynaklara dayanarak soruyu kapsamli yanıtla.\n"
            "- Onemli bilgileri vurgula\n"
            "- Tarih, fiyat, istatistik varsa yaz\n"
            "- Kisa paragraflar kullan\n"
            "- Turkce yaz"
        )

        ai_answer = self.call_ollama(
            'llama3.2:latest',
            [{'role': 'user', 'content': prompt}],
            'Sen bir arastirmaci ve bilgi sentezleyicisin. Kaynaklara sadik kal, uydurma. Sadece Turkce.',
            max_tokens=350, num_ctx=1024
        )

        # ADIM 4: Formatlı cikti
        sources_text = ''
        for i, c in enumerate(contents[:3], 1):
            url = c['url']
            title = c['title'][:50] if c['title'] else url[:50]
            sources_text += f'\n[{i}] [{title}]({url})'

        return (
            f'*Arama:* `{query}`\n\n'
            f'{ai_answer}\n\n'
            f'*Kaynaklar:*{sources_text}'
        )
