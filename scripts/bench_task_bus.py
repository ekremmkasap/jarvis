#!/usr/bin/env python3
"""
Benchmark: task_bus.py sanitization pipeline speed
Measures _sanitize_value on realistic nested payloads.
Outputs: p50_ms: <value>
DO NOT MODIFY after experiment starts — this is the fixed evaluator.
"""

import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "server" / "skills"))

try:
    from task_bus import _sanitize_value
except ImportError as e:
    print(f"Import error: {e}", file=sys.stderr)
    sys.exit(1)

# Realistic Jarvis task payloads
PAYLOADS = [
    # Normal task
    {
        "from_agent": "backend",
        "to_agent": "voice",
        "task_type": "speak",
        "payload": {"text": "Jarvis burada, nasıl yardımcı olabilirim?", "lang": "tr"},
    },
    # Sensitive fields (should be redacted)
    {
        "from_agent": "security",
        "to_agent": "backend",
        "task_type": "auth",
        "payload": {
            "token": "eyJhbGciOiJIUzI1NiJ9.secret",
            "password": "hunter2",
            "session": "abc123",
            "data": {"user": "ekrem", "cookie": "session=xyz"},
        },
    },
    # Nested list payload
    {
        "from_agent": "swarm",
        "to_agent": "backend",
        "task_type": "batch",
        "payload": {
            "tasks": [
                {"id": i, "cmd": f"/komut-{i}", "args": {"key": f"val-{i}"}}
                for i in range(10)
            ]
        },
    },
    # Large text payload
    {
        "from_agent": "video",
        "to_agent": "backend",
        "task_type": "report",
        "payload": {
            "summary": "A" * 300,
            "tags": ["ai", "jarvis", "video", "analysis"],
            "score": 87,
        },
    },
]

ROUNDS = 500
times = []

for _ in range(ROUNDS):
    for payload in PAYLOADS:
        t0 = time.perf_counter()
        _sanitize_value(payload)
        t1 = time.perf_counter()
        times.append((t1 - t0) * 1000)

times.sort()
p50 = statistics.median(times)
p95 = times[int(len(times) * 0.95)]
p99 = times[int(len(times) * 0.99)]
total_ops = len(times)

print(f"p50_ms: {p50:.4f}")
print(f"p95_ms: {p95:.4f}")
print(f"p99_ms: {p99:.4f}")
print(f"total_ops: {total_ops}")
