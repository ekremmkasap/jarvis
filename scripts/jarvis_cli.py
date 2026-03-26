from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from env_utils import load_env_files


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send a text task to the local Jarvis bridge.")
    parser.add_argument("message", nargs="+", help="Message to send to the running backend")
    parser.add_argument("--url", default="", help="Override backend URL")
    return parser.parse_args()


def resolve_backend_url(explicit: str) -> str:
    load_env_files(ROOT / ".env", ROOT / "server" / ".env")
    if explicit:
        return explicit.rstrip("/")
    return os.environ.get("JARVIS_BACKEND_URL", "http://127.0.0.1:8081").rstrip("/")


def send_message(base_url: str, text: str) -> dict:
    body = json.dumps({"message": text}).encode("utf-8")
    request = Request(
        f"{base_url}/api/chat",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def main() -> int:
    args = parse_args()
    base_url = resolve_backend_url(args.url)
    text = " ".join(args.message).strip()
    payload = send_message(base_url, text)
    print(payload.get("response", ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
