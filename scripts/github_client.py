from __future__ import annotations

import os
from io import BytesIO
from pathlib import Path
from typing import Any
from zipfile import ZipFile

import requests


class GitHubClient:
    def __init__(self, token: str = '', repository: str = '', api_url: str = 'https://api.github.com') -> None:
        self.token = token
        self.repository = repository
        self.api_url = api_url.rstrip('/')

    @property
    def enabled(self) -> bool:
        return bool(self.token and self.repository)

    def _headers(self) -> dict[str, str]:
        headers = {
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'jarvis-mission-control-automation',
        }
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'
        return headers

    def _request(self, method: str, endpoint: str, **kwargs: Any) -> requests.Response:
        if not self.enabled:
            raise RuntimeError('GitHub client is not configured')
        response = requests.request(
            method=method,
            url=f'{self.api_url}/repos/{self.repository}{endpoint}',
            headers=self._headers(),
            timeout=kwargs.pop('timeout', 30),
            **kwargs,
        )
        response.raise_for_status()
        return response

    def get_pull_request(self, number: int) -> dict[str, Any]:
        return self._request('GET', f'/pulls/{number}').json()

    def list_pull_request_files(self, number: int) -> list[dict[str, Any]]:
        return self._request('GET', f'/pulls/{number}/files').json()

    def get_issue(self, number: int) -> dict[str, Any]:
        return self._request('GET', f'/issues/{number}').json()

    def comment_issue(self, number: int, body: str) -> dict[str, Any]:
        return self._request('POST', f'/issues/{number}/comments', json={'body': body}).json()

    def add_labels(self, number: int, labels: list[str]) -> dict[str, Any]:
        return self._request('POST', f'/issues/{number}/labels', json={'labels': labels}).json()

    def add_assignees(self, number: int, assignees: list[str]) -> dict[str, Any]:
        return self._request('POST', f'/issues/{number}/assignees', json={'assignees': assignees}).json()

    def list_workflow_run_jobs(self, run_id: int) -> list[dict[str, Any]]:
        payload = self._request('GET', f'/actions/runs/{run_id}/jobs').json()
        return payload.get('jobs', [])

    def download_workflow_run_logs(self, run_id: int, max_bytes: int = 200000) -> str:
        response = self._request('GET', f'/actions/runs/{run_id}/logs', timeout=60)
        archive = ZipFile(BytesIO(response.content))
        chunks: list[str] = []
        for name in archive.namelist():
            with archive.open(name) as handle:
                text = handle.read().decode('utf-8', errors='replace')
            chunks.append(f'===== {name} =====\n{text}')
            if sum(len(chunk) for chunk in chunks) >= max_bytes:
                break
        return '\n\n'.join(chunks)[:max_bytes]

    @classmethod
    def from_env(cls) -> 'GitHubClient':
        return cls(
            token=os.environ.get('GITHUB_TOKEN', ''),
            repository=os.environ.get('GITHUB_REPOSITORY', ''),
            api_url=os.environ.get('GITHUB_API_URL', 'https://api.github.com'),
        )
