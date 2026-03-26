"""
JARVIS Web Crawler Agent
Webten veri çeker: Google, Wikipedia, GitHub, Stack Overflow, Reddit, ArXiv
"""
import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import requests
from bs4 import BeautifulSoup


class WebCrawlerAgent:
    """
    Web'den bilgi toplayan otonom agent.
    Rate limiting, caching, error handling dahil.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.cache_dir = Path("server/knowledge_base/web_scraped")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Rate limiting (saniyede max request)
        self.rate_limits = {
            "google": 1,  # 1 request/second
            "wikipedia": 2,
            "github": 5,
            "stackoverflow": 2,
        }
        self.last_request_time = {}

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """Config yükle veya default kullan"""
        if config_path and Path(config_path).exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            "user_agent": "JARVIS-Bot/1.0 (Self-Learning AI Assistant)",
            "timeout": 10,
            "max_retries": 3,
        }

    def _respect_rate_limit(self, source: str):
        """Rate limit kontrolü"""
        limit = self.rate_limits.get(source, 1)
        if source in self.last_request_time:
            elapsed = time.time() - self.last_request_time[source]
            wait_time = (1.0 / limit) - elapsed
            if wait_time > 0:
                time.sleep(wait_time)
        self.last_request_time[source] = time.time()

    def _save_to_cache(self, source: str, query: str, data: Dict):
        """Cache'e kaydet"""
        source_dir = self.cache_dir / source
        source_dir.mkdir(exist_ok=True)

        filename = f"{query.replace(' ', '_')}_{int(time.time())}.json"
        filepath = source_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump({
                "query": query,
                "source": source,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }, f, ensure_ascii=False, indent=2)

        print(f"[WebCrawler] Cached: {source}/{filename}")
        return str(filepath)

    # ============================================
    # GOOGLE SEARCH
    # ============================================
    def search_google(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Google'da arama yap (DuckDuckGo HTML scraping kullanarak - API gerektirmez)
        """
        self._respect_rate_limit("google")

        try:
            # DuckDuckGo HTML search (Google API gerektirmez)
            url = "https://html.duckduckgo.com/html/"
            params = {"q": query}
            headers = {"User-Agent": self.config["user_agent"]}

            response = requests.get(url, params=params, headers=headers, timeout=self.config["timeout"])
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')
            results = []

            for result in soup.find_all('div', class_='result')[:num_results]:
                title_elem = result.find('a', class_='result__a')
                snippet_elem = result.find('a', class_='result__snippet')

                if title_elem:
                    results.append({
                        "title": title_elem.get_text(strip=True),
                        "url": title_elem.get('href', ''),
                        "snippet": snippet_elem.get_text(strip=True) if snippet_elem else ''
                    })

            # Cache'e kaydet
            self._save_to_cache("google", query, {"results": results})
            return results

        except Exception as e:
            print(f"[WebCrawler] Google search error: {e}")
            return []

    # ============================================
    # WIKIPEDIA
    # ============================================
    def search_wikipedia(self, query: str, lang: str = "en") -> Dict[str, Any]:
        """
        Wikipedia'dan bilgi çek
        """
        self._respect_rate_limit("wikipedia")

        try:
            # Wikipedia API
            url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{query.replace(' ', '_')}"
            headers = {"User-Agent": self.config["user_agent"]}

            response = requests.get(url, headers=headers, timeout=self.config["timeout"])
            response.raise_for_status()

            data = response.json()
            result = {
                "title": data.get("title", ""),
                "extract": data.get("extract", ""),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                "thumbnail": data.get("thumbnail", {}).get("source", ""),
            }

            # Cache'e kaydet
            self._save_to_cache("wikipedia", query, result)
            return result

        except Exception as e:
            print(f"[WebCrawler] Wikipedia error: {e}")
            return {}

    # ============================================
    # GITHUB
    # ============================================
    def search_github(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """
        GitHub'da repository ara
        """
        self._respect_rate_limit("github")

        try:
            url = "https://api.github.com/search/repositories"
            params = {"q": query, "sort": "stars", "order": "desc", "per_page": num_results}
            headers = {
                "User-Agent": self.config["user_agent"],
                "Accept": "application/vnd.github.v3+json"
            }

            response = requests.get(url, params=params, headers=headers, timeout=self.config["timeout"])
            response.raise_for_status()

            data = response.json()
            results = []

            for item in data.get("items", []):
                results.append({
                    "name": item.get("full_name", ""),
                    "description": item.get("description", ""),
                    "url": item.get("html_url", ""),
                    "stars": item.get("stargazers_count", 0),
                    "language": item.get("language", ""),
                })

            # Cache'e kaydet
            self._save_to_cache("github", query, {"results": results})
            return results

        except Exception as e:
            print(f"[WebCrawler] GitHub error: {e}")
            return []

    # ============================================
    # STACK OVERFLOW
    # ============================================
    def search_stackoverflow(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        """
        Stack Overflow'da soru ara
        """
        self._respect_rate_limit("stackoverflow")

        try:
            url = "https://api.stackexchange.com/2.3/search/advanced"
            params = {
                "q": query,
                "order": "desc",
                "sort": "relevance",
                "site": "stackoverflow",
                "pagesize": num_results
            }
            headers = {"User-Agent": self.config["user_agent"]}

            response = requests.get(url, params=params, headers=headers, timeout=self.config["timeout"])
            response.raise_for_status()

            data = response.json()
            results = []

            for item in data.get("items", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "score": item.get("score", 0),
                    "answer_count": item.get("answer_count", 0),
                    "is_answered": item.get("is_answered", False),
                })

            # Cache'e kaydet
            self._save_to_cache("stackoverflow", query, {"results": results})
            return results

        except Exception as e:
            print(f"[WebCrawler] Stack Overflow error: {e}")
            return []

    # ============================================
    # GENERIC WEB SCRAPER
    # ============================================
    def scrape_url(self, url: str) -> Dict[str, Any]:
        """
        Herhangi bir URL'den içerik çek
        """
        try:
            headers = {"User-Agent": self.config["user_agent"]}
            response = requests.get(url, headers=headers, timeout=self.config["timeout"])
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Meta data
            title = soup.find('title')
            description = soup.find('meta', attrs={'name': 'description'})

            # Main content (paragraphs)
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]

            result = {
                "url": url,
                "title": title.get_text(strip=True) if title else "",
                "description": description.get('content', '') if description else "",
                "content": "\n\n".join(paragraphs[:10]),  # İlk 10 paragraf
            }

            return result

        except Exception as e:
            print(f"[WebCrawler] Scrape error for {url}: {e}")
            return {}

    # ============================================
    # ORCHESTRATION
    # ============================================
    def learn_from_query(self, query: str) -> Dict[str, Any]:
        """
        Bir sorgu için tüm kaynaklardan bilgi topla
        """
        print(f"\n[WebCrawler] Learning from query: '{query}'")

        knowledge = {
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "sources": {}
        }

        # Google
        print("[WebCrawler] Searching Google...")
        knowledge["sources"]["google"] = self.search_google(query, num_results=3)

        # Wikipedia
        print("[WebCrawler] Searching Wikipedia...")
        knowledge["sources"]["wikipedia"] = self.search_wikipedia(query)

        # GitHub (eğer kod ile ilgiliyse)
        if any(keyword in query.lower() for keyword in ["code", "library", "framework", "python", "javascript"]):
            print("[WebCrawler] Searching GitHub...")
            knowledge["sources"]["github"] = self.search_github(query, num_results=3)

        # Stack Overflow (eğer teknik soruysa)
        if any(keyword in query.lower() for keyword in ["error", "how to", "fix", "bug", "issue"]):
            print("[WebCrawler] Searching Stack Overflow...")
            knowledge["sources"]["stackoverflow"] = self.search_stackoverflow(query, num_results=3)

        print(f"[WebCrawler] Learning complete! Collected data from {len(knowledge['sources'])} sources.")
        return knowledge


# ============================================
# CLI TEST
# ============================================
if __name__ == "__main__":
    import sys

    agent = WebCrawlerAgent()

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "Python async programming tutorial"

    print(f"Testing WebCrawlerAgent with query: '{query}'")
    results = agent.learn_from_query(query)

    print("\n" + "="*50)
    print("RESULTS:")
    print("="*50)
    print(json.dumps(results, indent=2, ensure_ascii=False))
