from __future__ import annotations


def report_to_telegram(text: str) -> dict:
    return {
        "ok": False,
        "error": "not_implemented",
        "text": str(text or ""),
    }


def report_to_obsidian(finding: dict) -> dict:
    return {
        "ok": False,
        "error": "not_implemented",
        "finding": dict(finding or {}),
    }


def report_finding(finding: dict) -> dict:
    return {
        "ok": False,
        "error": "not_implemented",
        "finding": dict(finding or {}),
    }
