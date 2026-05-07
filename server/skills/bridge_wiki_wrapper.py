"""Bridge helpers for exporting batch scrape CSV rows into leads-wiki."""

from __future__ import annotations

import asyncio
import csv
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


LEAD_CSV_FIELDS = [
    "number",
    "ig_user_id",
    "avatar",
    "profile",
    "username",
    "full_name",
    "followed_by_you",
    "is_verified",
    "followers_count",
    "following_count",
    "posts_count",
    "email",
    "phone",
    "city",
    "biography",
    "address_street",
    "is_private",
    "is_business",
    "external_url",
    "platform",
]


def _load_wiki_components():
    try:
        from server.skills.leads_wiki_ingest import LeadsWikiIngester
        from server.skills.leads_wiki_summarizer import generate_hot_summary

        return LeadsWikiIngester, generate_hot_summary
    except Exception:
        skills_dir = Path(__file__).resolve().parent
        if str(skills_dir) not in sys.path:
            sys.path.insert(0, str(skills_dir))
        from leads_wiki_ingest import LeadsWikiIngester  # type: ignore
        from leads_wiki_summarizer import generate_hot_summary  # type: ignore

        return LeadsWikiIngester, generate_hot_summary


def _load_batch_scrape_runner():
    try:
        from server.skills.batch_profile_scraper_codex import batch_scrape_handler

        return batch_scrape_handler
    except Exception:
        from batch_profile_scraper_codex import batch_scrape_handler  # type: ignore

        return batch_scrape_handler


def _slugify_username(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^https?://", "", text)
    text = re.sub(r"[^a-z0-9_]+", "_", text)
    return text.strip("_") or "profil"


def _read_csv_headers(csv_file: Path) -> set[str]:
    with csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        headers = next(reader, [])
    return {str(header or "").strip().lower() for header in headers if str(header or "").strip()}


def _is_pre_enriched_lead_csv(csv_file: Path) -> bool:
    headers = _read_csv_headers(csv_file)
    return "username" in headers and (
        "biography" in headers or "followers_count" in headers or "full_name" in headers
    )


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _profile_to_lead_row(profile: dict[str, Any], index: int) -> dict[str, Any]:
    platform = str(profile.get("platform") or "instagram").strip().lower() or "instagram"
    username = str(
        profile.get("handle")
        or profile.get("channel_name")
        or profile.get("channel_id")
        or profile.get("full_name")
        or profile.get("profile_url")
        or profile.get("channel_url")
        or ""
    ).strip()
    if platform == "youtube":
        username = _slugify_username(username)

    full_name = str(profile.get("full_name") or profile.get("channel_name") or username).strip()
    biography = str(profile.get("bio") or profile.get("description") or "").strip()
    followers_count = _safe_int(
        profile.get("followers_count")
        or profile.get("subscribers_count")
        or profile.get("total_views")
    )
    profile_url = str(profile.get("profile_url") or profile.get("channel_url") or "").strip()
    external_url = str(profile.get("website_url") or "").strip()
    is_business = any(
        bool(profile.get(key))
        for key in (
            "is_business_account",
            "has_affiliate_links",
            "has_shopping_feature",
            "has_sponsored_posts",
            "is_partner_program_eligible",
            "has_super_chat_enabled",
        )
    )

    return {
        "number": str(index).zfill(6),
        "ig_user_id": str(profile.get("channel_id") or "").strip(),
        "avatar": str(profile.get("profile_pic_url") or "").strip(),
        "profile": profile_url,
        "username": username or f"profil_{index:06d}",
        "full_name": full_name,
        "followed_by_you": "False",
        "is_verified": str(bool(profile.get("is_verified"))),
        "followers_count": str(followers_count),
        "following_count": str(_safe_int(profile.get("following_count"))),
        "posts_count": str(
            _safe_int(profile.get("posts_count") or profile.get("total_videos"))
        ),
        "email": "",
        "phone": "",
        "city": "",
        "biography": biography,
        "address_street": "",
        "is_private": "False",
        "is_business": str(is_business),
        "external_url": external_url,
        "platform": platform,
    }


def _write_normalized_lead_csv(
    profiles: list[dict[str, Any]],
    wiki_root: Path,
) -> Path:
    raw_dir = wiki_root / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    normalized_csv = raw_dir / f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_wiki.csv"

    with normalized_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=LEAD_CSV_FIELDS)
        writer.writeheader()
        for index, profile in enumerate(profiles, start=1):
            writer.writerow(_profile_to_lead_row(profile, index))

    return normalized_csv


def _run_batch_scrape(
    csv_file: Path,
    batch_scrape_runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    runner = batch_scrape_runner or _load_batch_scrape_runner()
    result = runner(csv_path=str(csv_file))
    if asyncio.iscoroutine(result):
        result = asyncio.run(result)
    if not isinstance(result, dict):
        raise TypeError("Batch scraper dict sonuc dondurmeli")
    return result


def batch_scrape_to_wiki_result(
    csv_path: str | Path,
    wiki_output_dir: str | Path = "leads-wiki",
    batch_scrape_runner: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Process a batch CSV into markdown pages and return bridge-friendly stats."""

    csv_file = Path(csv_path)
    wiki_root = Path(wiki_output_dir)
    if not csv_file.exists():
        return {
            "status": "error",
            "ok": False,
            "error": f"CSV bulunamadi: {csv_file}",
            "csv_path": str(csv_file),
            "output_path": str(wiki_root / "wiki"),
        }

    LeadsWikiIngester, generate_hot_summary = _load_wiki_components()
    source_mode = "lead_csv"
    normalized_csv_path = csv_file
    batch_result: dict[str, Any] = {}

    if not _is_pre_enriched_lead_csv(csv_file):
        try:
            batch_result = _run_batch_scrape(csv_file, batch_scrape_runner=batch_scrape_runner)
        except Exception as exc:  # noqa: BLE001
            return {
                "status": "error",
                "ok": False,
                "error": f"Batch scrape calismadi: {exc}",
                "csv_path": str(csv_file),
                "output_path": str(wiki_root / "wiki"),
            }

        profiles = batch_result.get("profiles")
        if not isinstance(profiles, list) or not profiles:
            return {
                "status": "error",
                "ok": False,
                "error": "Batch scrape profil verisi uretmedi",
                "csv_path": str(csv_file),
                "batch_output_path": str(batch_result.get('output_path') or ""),
                "output_path": str(wiki_root / "wiki"),
            }

        normalized_csv_path = _write_normalized_lead_csv(profiles, wiki_root)
        source_mode = "handles_csv"

    ingester = LeadsWikiIngester(wiki_root=str(wiki_root))
    ingester.load_csv(str(normalized_csv_path))
    ingester.ingest_all()

    wiki_path = wiki_root / "wiki"
    lead_count = generate_hot_summary(str(wiki_path))

    return {
        "status": "completed",
        "ok": True,
        "wiki": True,
        "csv_path": str(csv_file),
        "source_mode": source_mode,
        "normalized_csv_path": str(normalized_csv_path),
        "lead_count": lead_count,
        "output_path": str(wiki_path),
        "summary_path": str(wiki_path / "hot.md"),
        "batch_output_path": str(batch_result.get("output_path") or ""),
        "batch_report_path": str(batch_result.get("report_path") or ""),
        "message": f"Wiki updated: {lead_count} leads in {wiki_path}",
    }


def batch_scrape_to_wiki(csv_path, wiki_output_dir="leads-wiki"):
    """
    Backward-compatible tuple API for direct script and legacy bridge usage.

    Usage from bridge:
        /batch-scrape --output wiki hesaplar.csv
    """

    try:
        result = batch_scrape_to_wiki_result(csv_path, wiki_output_dir)
        if result.get("ok") is False:
            return False, "ERROR: " + str(result.get("error") or "unknown error")
        return True, "OK " + str(result.get("message") or "Wiki updated")
    except Exception as exc:  # noqa: BLE001
        return False, "ERROR: " + str(exc)


def batch_scrape_with_wiki_option(csv_path, output_type="json", wiki_dir="leads-wiki"):
    """Extended batch scraper handler that supports ``--output wiki``."""

    if output_type == "wiki":
        return batch_scrape_to_wiki_result(csv_path, wiki_dir)

    try:
        from server.skills.batch_profile_scraper_codex import batch_scrape_handler
    except Exception:
        from batch_profile_scraper_codex import batch_scrape_handler  # type: ignore

    result = batch_scrape_handler(csv_path=str(csv_path))
    if asyncio.iscoroutine(result):
        return asyncio.run(result)
    return result


if __name__ == "__main__":
    csv = sys.argv[1] if len(sys.argv) > 1 else "leads-wiki/raw/test_batch.csv"
    success, msg = batch_scrape_to_wiki(csv)
    print(msg)
