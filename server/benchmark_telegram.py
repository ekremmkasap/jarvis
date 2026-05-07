#!/usr/bin/env python3
"""
Benchmark Telegram message throughput.
Measures: commands_per_sec in the main message loop.
"""

import asyncio
import time
import json
import sys
from pathlib import Path

# Mock Telegram message set
MOCK_MESSAGES = [
    {"text": "!youtube https://youtu.be/dQw4w9WgXcQ", "chat_id": 123, "message_id": 1},
    {"text": "!channel-analyzer @linustech", "chat_id": 123, "message_id": 2},
    {"text": "!help", "chat_id": 123, "message_id": 3},
    {"text": "!status", "chat_id": 123, "message_id": 4},
    {"text": "!joke", "chat_id": 123, "message_id": 5},
    {"text": "!weather istanbul", "chat_id": 123, "message_id": 6},
    {"text": "!translate hello to spanish", "chat_id": 123, "message_id": 7},
    {"text": "!code python fibonacci", "chat_id": 123, "message_id": 8},
    {"text": "!search AI news", "chat_id": 123, "message_id": 9},
    {"text": "!remind 5m check email", "chat_id": 123, "message_id": 10},
]

async def benchmark_loop():
    """
    Simulate processing MOCK_MESSAGES in the main loop.
    Count how many can be processed per second.
    """
    messages_processed = 0
    total_runtime = 0

    # Repeat message set 10x to get meaningful throughput number
    all_messages = MOCK_MESSAGES * 10

    start_time = time.time()

    for msg in all_messages:
        # Simulate message processing: parse, validate, route
        # This is roughly what bridge.py does in handle_message()

        text = msg.get("text", "").strip()

        # Security check: reject shell commands
        if text.startswith(("$", "!", "//", "#!")):
            # Rejected by validation - still counts as processed
            messages_processed += 1
            continue

        # Route command
        if text.startswith("!youtube"):
            # Would call youtube_skill - here we just note it
            pass
        elif text.startswith("!channel-analyzer"):
            # Would call channel_analyzer_skill
            pass
        elif text.startswith("!"):
            # Generic skill dispatch
            pass
        else:
            # General message - would hit LLM
            pass

        messages_processed += 1

        # Tiny async yield to be realistic (skill calls would be async)
        await asyncio.sleep(0.001)

    total_runtime = time.time() - start_time
    throughput = messages_processed / total_runtime if total_runtime > 0 else 0

    print(f"messages_processed: {messages_processed}")
    print(f"total_seconds: {total_runtime:.3f}")
    print(f"commands_per_sec: {throughput:.2f}")

    return throughput

def main():
    try:
        throughput = asyncio.run(benchmark_loop())
        sys.exit(0)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
