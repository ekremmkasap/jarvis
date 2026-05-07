#!/usr/bin/env python3
"""
Benchmark: model_router.py routing decision speed
Outputs: p50_ms: <value>
DO NOT MODIFY after experiment starts — this is the fixed evaluator.
"""

import statistics
import sys
import time
from pathlib import Path
from unittest.mock import patch

# Add server to path
sys.path.insert(0, str(Path(__file__).parent.parent / "server"))

try:
    from model_router import RouterSettings, ProviderConfig, Candidate
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    sys.exit(1)

# Minimal mock settings — no network calls
MOCK_SETTINGS = RouterSettings(
    enabled=True,
    default_provider="ollama",
    retry_attempts=2,
    backoff_seconds=0.1,
    providers={
        "ollama": ProviderConfig(
            name="ollama",
            kind="openai",
            base_url="http://localhost:11434/v1",
            api_key="",
            timeout=30,
        ),
        "openrouter": ProviderConfig(
            name="openrouter",
            kind="openai",
            base_url="https://openrouter.ai/api/v1",
            api_key="test-key",
            timeout=30,
        ),
    },
    chains={
        "chat": [
            Candidate(provider="ollama", model="llama3.2:latest", source="config"),
            Candidate(provider="openrouter", model="gpt-4o-mini", source="config"),
        ],
        "code": [
            Candidate(provider="ollama", model="qwen2.5-coder:7b", source="config"),
        ],
        "general": [
            Candidate(provider="ollama", model="llama3.2:latest", source="config"),
        ],
    },
)

ROUNDS = 1000
times = []

for _ in range(ROUNDS):
    t0 = time.perf_counter()
    # Simulate routing decision: pick chain + select candidate
    chain = MOCK_SETTINGS.chains.get("chat", [])
    _ = [c for c in chain if MOCK_SETTINGS.providers.get(c.provider)]
    t1 = time.perf_counter()
    times.append((t1 - t0) * 1000)  # ms

times.sort()
p50 = statistics.median(times)
p95 = times[int(len(times) * 0.95)]
p99 = times[int(len(times) * 0.99)]

print(f"p50_ms: {p50:.4f}")
print(f"p95_ms: {p95:.4f}")
print(f"p99_ms: {p99:.4f}")
print(f"rounds: {ROUNDS}")
