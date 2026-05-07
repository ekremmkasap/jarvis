from __future__ import annotations


def crawl_bugbounty_scope(program_url: str) -> dict:
    return {
        "ok": False,
        "error": "not_implemented",
        "program_url": str(program_url or "").strip(),
        "domains": [],
    }
