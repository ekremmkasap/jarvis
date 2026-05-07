from __future__ import annotations

"""Compatibility wrapper for the canonical batch profile scraper.

Older prompts and docs may refer to ``server.skills.batch_profile_scraper``.
The maintained implementation lives in ``batch_profile_scraper_codex``.
"""

import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
SERVER_DIR = Path(__file__).resolve().parents[1]
for candidate in (ROOT_DIR, SERVER_DIR):
    candidate_text = str(candidate)
    if candidate_text not in sys.path:
        sys.path.insert(0, candidate_text)

try:
    from server.skills.batch_profile_scraper_codex import (
        BatchProfileScraper,
        analyze_engagement,
        batch_scrape_handler,
        estimate_monetization,
        generate_summary_report,
        handle_batch_scrape,
        load_batch_targets_from_csv,
        normalize_batch_targets,
        run_batch_scrape,
        run_batch_scrape_sync,
    )
except Exception:
    from batch_profile_scraper_codex import (  # type: ignore
        BatchProfileScraper,
        analyze_engagement,
        batch_scrape_handler,
        estimate_monetization,
        generate_summary_report,
        handle_batch_scrape,
        load_batch_targets_from_csv,
        normalize_batch_targets,
        run_batch_scrape,
        run_batch_scrape_sync,
    )


__all__ = [
    "BatchProfileScraper",
    "analyze_engagement",
    "batch_scrape_handler",
    "estimate_monetization",
    "generate_summary_report",
    "handle_batch_scrape",
    "load_batch_targets_from_csv",
    "normalize_batch_targets",
    "run_batch_scrape",
    "run_batch_scrape_sync",
]


def _main() -> int:
    if len(sys.argv) < 2:
        print("Kullanim: python server/skills/batch_profile_scraper.py <handles.csv>")
        return 2
    result = run_batch_scrape_sync(csv_path=sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
