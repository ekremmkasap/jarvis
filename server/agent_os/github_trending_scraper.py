"""
GitHub Trending Scraper
Güncel teknolojileri ve geliştiricileri takip eder
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class GitHubTrendingScraper:
    """
    GitHub trending repos ve developers scraper
    """

    def __init__(self, cache_dir: str = "server/knowledge_base/github_trending"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.base_url = "https://github.com/trending"

    def scrape_trending_repos(
        self,
        language: str = "",
        since: str = "daily"
    ) -> List[Dict[str, Any]]:
        """
        Trending repositories çek

        Args:
            language: Programlama dili filtresi (python, javascript, etc.)
            since: daily, weekly, monthly
        """
        url = f"{self.base_url}/{language}?since={since}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            repos = []
            articles = soup.find_all('article', class_='Box-row')

            for article in articles:
                repo_info = self._parse_repo_article(article)
                if repo_info:
                    repos.append(repo_info)

            # Cache
            self._cache_results("repos", language, since, repos)

            print(f"[GitHubTrending] Found {len(repos)} trending repos")
            return repos

        except Exception as e:
            print(f"[GitHubTrending] Error scraping repos: {e}")
            return []

    def scrape_trending_developers(self, since: str = "daily") -> List[Dict[str, Any]]:
        """
        Trending developers çek
        """
        url = f"{self.base_url}/developers?since={since}"

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            developers = []
            articles = soup.find_all('article', class_='Box-row')

            for article in articles:
                dev_info = self._parse_developer_article(article)
                if dev_info:
                    developers.append(dev_info)

            # Cache
            self._cache_results("developers", "", since, developers)

            print(f"[GitHubTrending] Found {len(developers)} trending developers")
            return developers

        except Exception as e:
            print(f"[GitHubTrending] Error scraping developers: {e}")
            return []

    def _parse_repo_article(self, article) -> Dict[str, Any]:
        """Parse repository article"""
        try:
            # Repo name and link
            h2 = article.find('h2', class_='h3')
            if not h2:
                return None

            link = h2.find('a')
            if not link:
                return None

            repo_name = link.get('href', '').strip('/')
            repo_url = f"https://github.com{link.get('href', '')}"

            # Description
            desc_p = article.find('p', class_='col-9')
            description = desc_p.text.strip() if desc_p else ""

            # Language
            lang_span = article.find('span', itemprop='programmingLanguage')
            language = lang_span.text.strip() if lang_span else "Unknown"

            # Stars today
            stars_span = article.find('span', class_='d-inline-block float-sm-right')
            stars_today = stars_span.text.strip() if stars_span else "0"

            # Total stars
            total_stars_link = article.find('a', href=lambda x: x and '/stargazers' in x)
            total_stars = total_stars_link.text.strip() if total_stars_link else "0"

            return {
                "name": repo_name,
                "url": repo_url,
                "description": description,
                "language": language,
                "stars_today": stars_today,
                "total_stars": total_stars,
                "scraped_at": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"[GitHubTrending] Error parsing repo: {e}")
            return None

    def _parse_developer_article(self, article) -> Dict[str, Any]:
        """Parse developer article"""
        try:
            # Username
            h1 = article.find('h1', class_='h3')
            if not h1:
                return None

            link = h1.find('a')
            if not link:
                return None

            username = link.text.strip()
            profile_url = f"https://github.com{link.get('href', '')}"

            # Popular repo
            repo_article = article.find('article', class_='d-flex')
            popular_repo = None

            if repo_article:
                repo_link = repo_article.find('a')
                if repo_link:
                    popular_repo = {
                        "name": repo_link.text.strip(),
                        "url": f"https://github.com{repo_link.get('href', '')}"
                    }

            return {
                "username": username,
                "profile_url": profile_url,
                "popular_repo": popular_repo,
                "scraped_at": datetime.now().isoformat()
            }

        except Exception as e:
            print(f"[GitHubTrending] Error parsing developer: {e}")
            return None

    def _cache_results(self, type_: str, language: str, since: str, data: List[Dict]):
        """Cache sonuçları kaydet"""
        filename = f"{type_}_{language or 'all'}_{since}_{int(time.time())}.json"
        cache_file = self.cache_dir / filename

        with open(cache_file, 'w', encoding='utf-8') as f:
            json.dump({
                "type": type_,
                "language": language,
                "since": since,
                "count": len(data),
                "scraped_at": datetime.now().isoformat(),
                "data": data
            }, f, indent=2, ensure_ascii=False)

        print(f"[GitHubTrending] Cached: {cache_file}")

    def get_daily_digest(self) -> Dict[str, Any]:
        """
        Günlük özet: trending repos + developers
        """
        print("\n[GitHubTrending] Fetching daily digest...")

        # Top repos (Python)
        python_repos = self.scrape_trending_repos("python", "daily")
        time.sleep(2)  # Rate limiting

        # Top repos (JavaScript)
        js_repos = self.scrape_trending_repos("javascript", "daily")
        time.sleep(2)

        # Top developers
        developers = self.scrape_trending_developers("daily")

        digest = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "python_repos": python_repos[:5],
            "javascript_repos": js_repos[:5],
            "developers": developers[:5]
        }

        # Save digest
        digest_file = self.cache_dir / f"daily_digest_{datetime.now().strftime('%Y%m%d')}.json"
        with open(digest_file, 'w', encoding='utf-8') as f:
            json.dump(digest, f, indent=2, ensure_ascii=False)

        print(f"[GitHubTrending] Daily digest saved: {digest_file}")

        return digest


# ============================================
# CLI TEST
# ============================================
if __name__ == "__main__":
    import sys

    if not HAS_DEPS:
        print("Error: beautifulsoup4 required")
        print("Install: pip install beautifulsoup4")
        sys.exit(1)

    scraper = GitHubTrendingScraper()

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "repos":
            language = sys.argv[2] if len(sys.argv) > 2 else ""
            repos = scraper.scrape_trending_repos(language, "daily")
            print(json.dumps(repos[:5], indent=2, ensure_ascii=False))

        elif command == "developers":
            devs = scraper.scrape_trending_developers("daily")
            print(json.dumps(devs[:5], indent=2, ensure_ascii=False))

        elif command == "digest":
            digest = scraper.get_daily_digest()
            print(json.dumps(digest, indent=2, ensure_ascii=False))

        else:
            print("Usage:")
            print("  python github_trending_scraper.py repos [language]")
            print("  python github_trending_scraper.py developers")
            print("  python github_trending_scraper.py digest")

    else:
        digest = scraper.get_daily_digest()
