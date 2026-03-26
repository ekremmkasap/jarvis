from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Mapping

import requests


@dataclass
class OllamaLLMClient:
    url: str
    model: str
    api_key: str = ''
    timeout_seconds: int = 90
    enabled: bool = True

    def available(self) -> bool:
        return self.enabled and bool(self.model)

    def generate(self, prompt: str, system: str | None = None) -> str | None:
        if not self.available():
            return None

        body: dict[str, Any] = {
            'model': self.model,
            'prompt': prompt,
            'stream': False,
        }
        if system:
            body['system'] = system

        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'

        try:
            response = requests.post(
                f"{self.url.rstrip('/')}/api/generate",
                json=body,
                headers=headers,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException:
            return None

        payload = response.json()
        return payload.get('response', '').strip() or None


def build_llm_client(config: Mapping[str, Any] | None = None) -> OllamaLLMClient:
    config = dict(config or {})
    return OllamaLLMClient(
        url=os.environ.get('OLLAMA_URL', 'http://127.0.0.1:11434'),
        model=os.environ.get('AUTOMATION_MODEL', config.get('model', '')),
        api_key=os.environ.get('OLLAMA_API_KEY', ''),
        timeout_seconds=int(config.get('timeout_seconds', 90)),
        enabled=os.environ.get('AUTOMATION_DISABLE_LLM', '0') != '1',
    )
