"""
GitHub Repository Analyzer
Trending/popular repo'ları analiz eder ve best practice'leri çıkarır
"""
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False


class GitHubRepoAnalyzer:
    """
    GitHub repo'larını analiz eder ve pattern'leri çıkarır
    """

    def __init__(self, output_dir: str = "server/agent_workspace/staging"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.github_api = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "JARVIS-Night-Runner"
        }

    def analyze_repo(self, repo_url: str) -> Dict[str, Any]:
        """
        Single repo analysis

        Returns:
            {
                "name": "repo/name",
                "description": "...",
                "language": "Python",
                "stars": 1000,
                "topics": ["ai", "automation"],
                "readme_summary": "...",
                "key_files": [...],
                "patterns_found": [...]
            }
        """
        # Extract owner/repo from URL
        parts = repo_url.rstrip('/').split('/')
        if len(parts) >= 2:
            owner = parts[-2]
            repo = parts[-1]
        else:
            return {"error": "Invalid URL"}

        print(f"[RepoAnalyzer] Analyzing {owner}/{repo}...")

        try:
            # Get repo info
            repo_info = self._fetch_repo_info(owner, repo)

            # Get README
            readme = self._fetch_readme(owner, repo)

            # Get key files
            key_files = self._scan_key_files(owner, repo)

            # Extract patterns
            patterns = self._extract_patterns(repo_info, readme, key_files)

            analysis = {
                "name": f"{owner}/{repo}",
                "url": repo_url,
                "description": repo_info.get("description", ""),
                "language": repo_info.get("language", "Unknown"),
                "stars": repo_info.get("stargazers_count", 0),
                "topics": repo_info.get("topics", []),
                "readme_summary": readme[:500] if readme else "",
                "key_files": key_files,
                "patterns_found": patterns,
                "analyzed_at": datetime.now().isoformat()
            }

            print(f"[RepoAnalyzer] ✓ {owner}/{repo} - {len(patterns)} patterns found")

            return analysis

        except Exception as e:
            print(f"[RepoAnalyzer] ✗ {owner}/{repo} - {e}")
            return {
                "name": f"{owner}/{repo}",
                "error": str(e),
                "analyzed_at": datetime.now().isoformat()
            }

    def analyze_batch(self, repo_urls: List[str]) -> Dict[str, Any]:
        """
        Batch analysis of multiple repos
        """
        print(f"\n[RepoAnalyzer] Starting batch analysis of {len(repo_urls)} repos...")

        results = []
        patterns_summary = {}

        for i, url in enumerate(repo_urls):
            print(f"\n[{i+1}/{len(repo_urls)}] {url}")

            analysis = self.analyze_repo(url)
            results.append(analysis)

            # Aggregate patterns
            for pattern in analysis.get("patterns_found", []):
                pattern_type = pattern.get("type", "unknown")
                if pattern_type not in patterns_summary:
                    patterns_summary[pattern_type] = []
                patterns_summary[pattern_type].append({
                    "repo": analysis["name"],
                    "description": pattern.get("description", "")
                })

            # Rate limiting
            time.sleep(2)

        # Generate report
        report = {
            "session": {
                "total_repos": len(repo_urls),
                "successful": len([r for r in results if "error" not in r]),
                "failed": len([r for r in results if "error" in r]),
                "timestamp": datetime.now().isoformat()
            },
            "results": results,
            "patterns_summary": patterns_summary,
            "top_languages": self._aggregate_languages(results),
            "top_topics": self._aggregate_topics(results)
        }

        # Save report
        self._save_report(report)

        print(f"\n[RepoAnalyzer] ✓ Batch analysis complete!")
        print(f"  Successful: {report['session']['successful']}")
        print(f"  Failed: {report['session']['failed']}")
        print(f"  Patterns found: {len(patterns_summary)} types")

        return report

    def _fetch_repo_info(self, owner: str, repo: str) -> Dict:
        """Fetch repo metadata from GitHub API"""
        url = f"{self.github_api}/repos/{owner}/{repo}"
        response = requests.get(url, headers=self.headers, timeout=10)
        response.raise_for_status()
        return response.json()

    def _fetch_readme(self, owner: str, repo: str) -> str:
        """Fetch README content"""
        try:
            url = f"{self.github_api}/repos/{owner}/{repo}/readme"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            readme_data = response.json()
            content_url = readme_data.get("download_url")

            if content_url:
                content_response = requests.get(content_url, timeout=10)
                return content_response.text

        except:
            pass

        return ""

    def _scan_key_files(self, owner: str, repo: str) -> List[str]:
        """Scan for key files (package.json, setup.py, etc.)"""
        key_files = []
        important_files = [
            "package.json",
            "setup.py",
            "pyproject.toml",
            "Cargo.toml",
            "go.mod",
            "docker-compose.yml",
            "Dockerfile"
        ]

        try:
            url = f"{self.github_api}/repos/{owner}/{repo}/contents"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()

            files = response.json()

            for file in files:
                if file["name"] in important_files:
                    key_files.append(file["name"])

        except:
            pass

        return key_files

    def _extract_patterns(self, repo_info: Dict, readme: str, key_files: List[str]) -> List[Dict]:
        """Extract architectural patterns from repo"""
        patterns = []

        # Pattern 1: MCP/Protocol
        if "mcp" in repo_info.get("name", "").lower() or "protocol" in readme.lower():
            patterns.append({
                "type": "mcp_protocol",
                "description": "Uses MCP (Model Context Protocol) pattern",
                "confidence": "high"
            })

        # Pattern 2: Skills/Agents
        if "skill" in repo_info.get("name", "").lower() or "agent" in readme.lower():
            patterns.append({
                "type": "skill_architecture",
                "description": "Implements skill/agent pattern",
                "confidence": "high"
            })

        # Pattern 3: CLI
        if "cli" in repo_info.get("name", "").lower() or "package.json" in key_files:
            patterns.append({
                "type": "cli_framework",
                "description": "Command-line interface framework",
                "confidence": "medium"
            })

        # Pattern 4: Orchestration
        if any(word in readme.lower() for word in ["orchestrat", "workflow", "pipeline"]):
            patterns.append({
                "type": "orchestration",
                "description": "Workflow/task orchestration system",
                "confidence": "medium"
            })

        # Pattern 5: Multi-source research
        if any(word in readme.lower() for word in ["reddit", "youtube", "twitter", "research"]):
            patterns.append({
                "type": "multi_source_research",
                "description": "Multi-source data aggregation",
                "confidence": "high"
            })

        # Pattern 6: Bridge/Connector
        if "bridge" in repo_info.get("name", "").lower() or "connect" in repo_info.get("name", "").lower():
            patterns.append({
                "type": "bridge_pattern",
                "description": "Bridge/connector pattern for integration",
                "confidence": "high"
            })

        return patterns

    def _aggregate_languages(self, results: List[Dict]) -> Dict[str, int]:
        """Aggregate programming languages"""
        languages = {}
        for result in results:
            if "error" in result:
                continue
            lang = result.get("language", "Unknown")
            languages[lang] = languages.get(lang, 0) + 1
        return dict(sorted(languages.items(), key=lambda x: x[1], reverse=True))

    def _aggregate_topics(self, results: List[Dict]) -> List[str]:
        """Aggregate topics"""
        topic_counts = {}
        for result in results:
            if "error" in result:
                continue
            for topic in result.get("topics", []):
                topic_counts[topic] = topic_counts.get(topic, 0) + 1

        return [t for t, _ in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[:10]]

    def _save_report(self, report: Dict):
        """Save analysis report"""
        # JSON report
        json_path = self.output_dir / f"repo_analysis_{int(time.time())}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        # Markdown summary
        md_path = self.output_dir / f"repo_analysis_{int(time.time())}.md"
        md_content = self._generate_markdown_report(report)
        md_path.write_text(md_content, encoding='utf-8')

        print(f"[RepoAnalyzer] Reports saved:")
        print(f"  - {json_path}")
        print(f"  - {md_path}")

    def _generate_markdown_report(self, report: Dict) -> str:
        """Generate markdown report"""
        md = f"""# GitHub Repository Analysis Report
**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

## Summary
- **Total Repos:** {report['session']['total_repos']}
- **Successful:** {report['session']['successful']}
- **Failed:** {report['session']['failed']}

## Top Languages
"""

        for lang, count in report['top_languages'].items():
            md += f"- **{lang}**: {count} repos\n"

        md += "\n## Top Topics\n"
        for topic in report['top_topics']:
            md += f"- {topic}\n"

        md += "\n## Patterns Found\n"
        for pattern_type, examples in report['patterns_summary'].items():
            md += f"\n### {pattern_type}\n"
            md += f"Found in {len(examples)} repos:\n"
            for ex in examples[:3]:  # Show top 3
                md += f"- **{ex['repo']}**: {ex['description']}\n"

        md += "\n## Individual Repo Analysis\n"
        for result in report['results'][:10]:  # Show top 10
            if "error" in result:
                continue

            md += f"\n### {result['name']}\n"
            md += f"- **Stars:** {result['stars']}\n"
            md += f"- **Language:** {result['language']}\n"
            md += f"- **Description:** {result['description']}\n"

            if result['patterns_found']:
                md += "- **Patterns:**\n"
                for p in result['patterns_found']:
                    md += f"  - {p['type']}: {p['description']}\n"

        md += "\n---\n*Generated by JARVIS Night Runner*\n"

        return md


# ============================================
# CLI TEST
# ============================================
if __name__ == "__main__":
    import sys

    if not HAS_DEPS:
        print("Error: requests and beautifulsoup4 required")
        print("Install: pip install requests beautifulsoup4")
        sys.exit(1)

    analyzer = GitHubRepoAnalyzer()

    if len(sys.argv) > 1 and sys.argv[1] == "batch":
        # Load from queue file
        queue_file = "server/agent_os/repo_analysis_queue.json"
        with open(queue_file, 'r') as f:
            queue = json.load(f)

        urls = [r["url"] for r in queue["repos_to_analyze"]]
        report = analyzer.analyze_batch(urls)

        print(f"\n✓ Analysis complete!")
        print(f"  Check: server/agent_workspace/staging/")

    elif len(sys.argv) > 1:
        # Single repo analysis
        url = sys.argv[1]
        result = analyzer.analyze_repo(url)
        print(json.dumps(result, indent=2, ensure_ascii=False))

    else:
        print("Usage:")
        print("  python github_repo_analyzer.py <repo_url>")
        print("  python github_repo_analyzer.py batch")
