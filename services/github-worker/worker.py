from __future__ import annotations

"""
Jarvis GitHub Worker
Polls GitHub events and dispatches tasks to orchestrator.
"""

import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

log = logging.getLogger("github.worker")

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
GITHUB_API = os.getenv("GITHUB_API_URL", "https://api.github.com")
ORCHESTRATOR_URL = os.getenv("ORCHESTRATOR_URL", "http://127.0.0.1:8091")
POLL_INTERVAL = int(os.getenv("GITHUB_POLL_INTERVAL", "60"))
WATCHED_REPOS = [r.strip() for r in os.getenv("JARVIS_WATCHED_REPOS", "").split(",") if r.strip()]


def gh_request(path: str, method: str = "GET", body: dict = None) -> Any:
    url = f"{GITHUB_API}{path}"
    data = json.dumps(body).encode() if body else None
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
    }
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        log.error("GitHub API error %d: %s", e.code, e.read().decode()[:200])
        return None
    except Exception as e:
        log.error("GitHub request failed: %s", e)
        return None


def send_task(goal: str, agent: str, context: dict = None):
    payload = json.dumps({
        "goal": goal,
        "agent": agent,
        "context": context or {},
        "dry_run": False,
    }).encode()
    req = Request(
        f"{ORCHESTRATOR_URL}/task",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            log.info("Task created: %s", result.get("task_id"))
            return result
    except Exception as e:
        log.error("Failed to create task: %s", e)
        return {}


class GitHubWorker:
    def __init__(self):
        self._seen_prs: set[str] = set()
        self._seen_issues: set[str] = set()
        self._seen_ci: set[str] = set()

    def process_prs(self, repo: str):
        data = gh_request(f"/repos/{repo}/pulls?state=open&per_page=10")
        if not isinstance(data, list):
            return
        for pr in data:
            key = f"{repo}:pr:{pr['number']}"
            if key in self._seen_prs:
                continue
            self._seen_prs.add(key)
            log.info("[%s] New PR #%d: %s", repo, pr["number"], pr["title"])
            send_task(
                goal=f"Review PR #{pr['number']}: {pr['title']}\nRepo: {repo}\nURL: {pr['html_url']}",
                agent="reviewer",
                context={"repo": repo, "pr_number": pr["number"], "event": "pull_request"},
            )

    def process_issues(self, repo: str):
        data = gh_request(f"/repos/{repo}/issues?state=open&per_page=10")
        if not isinstance(data, list):
            return
        for issue in data:
            if "pull_request" in issue:
                continue
            key = f"{repo}:issue:{issue['number']}"
            if key in self._seen_issues:
                continue
            self._seen_issues.add(key)
            log.info("[%s] New issue #%d: %s", repo, issue["number"], issue["title"])
            send_task(
                goal=f"Triage issue #{issue['number']}: {issue['title']}\nBody: {issue.get('body','')[:500]}",
                agent="planner",
                context={"repo": repo, "issue_number": issue["number"], "event": "issues"},
            )

    def process_ci_runs(self, repo: str):
        data = gh_request(f"/repos/{repo}/actions/runs?per_page=5")
        if not isinstance(data, dict):
            return
        for run in data.get("workflow_runs", []):
            if run.get("conclusion") != "failure":
                continue
            key = f"{repo}:ci:{run['id']}"
            if key in self._seen_ci:
                continue
            self._seen_ci.add(key)
            log.info("[%s] CI failure: %s", repo, run["name"])
            send_task(
                goal=f"Diagnose CI failure: {run['name']} on {run['head_branch']}\nURL: {run['html_url']}",
                agent="debug",
                context={"repo": repo, "run_id": run["id"], "event": "workflow_run"},
            )

    def run(self):
        if not GITHUB_TOKEN:
            log.warning("GITHUB_TOKEN not set — GitHub worker disabled")
            return
        if not WATCHED_REPOS:
            log.warning("JARVIS_WATCHED_REPOS not set — no repos to watch")
            return

        log.info("GitHub worker polling: %s every %ds", WATCHED_REPOS, POLL_INTERVAL)
        day_tick = 0

        while True:
            for repo in WATCHED_REPOS:
                try:
                    self.process_prs(repo)
                    self.process_issues(repo)
                    self.process_ci_runs(repo)
                except Exception as e:
                    log.exception("Error processing %s: %s", repo, e)

            day_tick += 1
            if day_tick * POLL_INTERVAL >= 86400:
                day_tick = 0
                for repo in WATCHED_REPOS:
                    send_task(
                        goal=f"Generate daily repository summary for {repo}",
                        agent="repo_analyst",
                        context={"repo": repo, "report_type": "daily_summary"},
                    )

            time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
    GitHubWorker().run()
