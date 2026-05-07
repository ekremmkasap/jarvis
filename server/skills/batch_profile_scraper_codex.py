from __future__ import annotations

import asyncio
import csv
import json
import logging
import re
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Iterable, Sequence

try:
    from server.services.universal_profile_scraper import UniversalProfileScraper
except Exception:
    from services.universal_profile_scraper import UniversalProfileScraper  # type: ignore


logger = logging.getLogger(__name__)

DEFAULT_OUTPUT_ROOT = Path("outputs/batch_scrapes")
DEFAULT_MAX_CONCURRENT = 5
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_MAX_RETRIES = 2


def _slugify_filename(value: str) -> str:
    text = str(value or "").strip().lower()
    text = re.sub(r"^https?://", "", text)
    text = text.replace("@", "")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_") or "profil"


def _now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _safe_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _mean(values: Sequence[float]) -> float:
    clean_values = [float(item) for item in values if item is not None]
    if not clean_values:
        return 0.0
    return sum(clean_values) / len(clean_values)


def _detect_platform(target: str, platform: str | None = None) -> str:
    explicit = str(platform or "").strip().lower()
    if explicit in {"instagram", "youtube"}:
        return explicit

    clean_target = str(target or "").strip().lower()
    if "youtube" in clean_target or "youtu.be" in clean_target:
        return "youtube"
    return "instagram"


def _extract_identity(profile: dict[str, Any]) -> str:
    for key in ("handle", "channel_name", "channel_id", "full_name", "profile_url"):
        value = str(profile.get(key) or "").strip()
        if value:
            return value
    return "profil"


def _audience_size(profile: dict[str, Any]) -> int:
    for key in ("followers_count", "subscribers_count", "total_views"):
        value = _safe_int(profile.get(key))
        if value > 0:
            return value
    return 0


def _growth_percent(profile: dict[str, Any]) -> float:
    for key in ("follower_growth_percent_monthly", "subscriber_growth_percent_monthly"):
        value = _safe_float(profile.get(key))
        if value:
            return value
    return 0.0


def _engagement_rate(profile: dict[str, Any]) -> float:
    return round(_safe_float(profile.get("avg_engagement_rate")), 4)


def _profile_target_payload(
    target: str,
    platform: str | None = None,
) -> dict[str, str]:
    clean_target = str(target or "").strip()
    if not clean_target:
        raise ValueError("target is required")
    return {
        "target": clean_target,
        "platform": _detect_platform(clean_target, platform),
    }


def load_batch_targets_from_csv(csv_path: str | Path) -> list[dict[str, str]]:
    path = Path(csv_path).expanduser()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        rows: list[dict[str, str]] = []
        for row in reader:
            payload = row if isinstance(row, dict) else {}
            raw_target = ""
            for key in ("hesap", "handle", "account", "url", "target"):
                value = str(payload.get(key) or "").strip()
                if value:
                    raw_target = value
                    break
            if not raw_target:
                continue
            rows.append(
                _profile_target_payload(
                    raw_target,
                    str(payload.get("platform") or "").strip() or None,
                )
            )
    return rows


def normalize_batch_targets(
    targets: Iterable[str | dict[str, Any]] | None,
) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for item in targets or []:
        if isinstance(item, dict):
            raw_target = str(
                item.get("target")
                or item.get("handle")
                or item.get("hesap")
                or item.get("url")
                or item.get("account")
                or ""
            ).strip()
            raw_platform = str(item.get("platform") or "").strip() or None
        else:
            raw_target = str(item or "").strip()
            raw_platform = None
        if not raw_target:
            continue
        normalized.append(_profile_target_payload(raw_target, raw_platform))
    return normalized


def analyze_engagement(profiles: Sequence[dict[str, Any]]) -> dict[str, Any]:
    per_platform: dict[str, list[float]] = {}
    growth_patterns: dict[str, list[float]] = {}
    top_candidates: list[dict[str, Any]] = []

    for profile in profiles:
        platform = str(profile.get("platform") or "instagram").strip().lower()
        rate = _engagement_rate(profile)
        per_platform.setdefault(platform, []).append(rate)
        growth_patterns.setdefault(platform, []).append(_growth_percent(profile))
        top_candidates.append(
            {
                "hesap": _extract_identity(profile),
                "platform": platform,
                "etkilesim": rate,
                "takipci": _audience_size(profile),
            }
        )

    benchmarks = {
        platform: {
            "min": round(min(values), 4) if values else 0.0,
            "max": round(max(values), 4) if values else 0.0,
            "median": round(float(median(values)), 4) if values else 0.0,
            "avg": round(_mean(values), 4),
        }
        for platform, values in per_platform.items()
    }

    top_performers = sorted(
        top_candidates,
        key=lambda item: (float(item.get("etkilesim") or 0), int(item.get("takipci") or 0)),
        reverse=True,
    )[:5]

    return {
        "instagram_avg_engagement": round(_mean(per_platform.get("instagram", [])), 4),
        "youtube_avg_engagement": round(_mean(per_platform.get("youtube", [])), 4),
        "platform_benchmarks": benchmarks,
        "top_performers": top_performers,
        "growth_patterns": {
            platform: {
                "avg_growth_percent": round(_mean(values), 4),
                "max_growth_percent": round(max(values), 4) if values else 0.0,
            }
            for platform, values in growth_patterns.items()
        },
    }


def estimate_monetization(profiles: Sequence[dict[str, Any]]) -> dict[str, Any]:
    estimates: list[dict[str, Any]] = []
    total_min = 0.0
    total_max = 0.0

    for profile in profiles:
        platform = str(profile.get("platform") or "instagram").strip().lower()
        audience = max(_audience_size(profile), 1)
        engagement = max(_engagement_rate(profile), 0.2)
        baseline = audience * (0.012 if platform == "youtube" else 0.01)
        multiplier = 1.0

        if profile.get("has_affiliate_links"):
            multiplier *= 1.25
        if profile.get("has_shopping_feature"):
            multiplier *= 1.15
        if profile.get("has_sponsored_posts") or profile.get("has_super_chat_enabled"):
            multiplier *= 1.3
        if profile.get("is_partner_program_eligible"):
            multiplier *= 1.2

        multiplier *= 1 + min(engagement, 10.0) / 25
        estimated_mid = baseline * multiplier
        estimated_min = round(estimated_mid * 0.8, 2)
        estimated_max = round(estimated_mid * 1.6, 2)
        total_min += estimated_min
        total_max += estimated_max

        estimates.append(
            {
                "hesap": _extract_identity(profile),
                "platform": platform,
                "takipci": audience,
                "etkilesim": round(engagement, 4),
                "tahmini_aylik_gelir_min": estimated_min,
                "tahmini_aylik_gelir_max": estimated_max,
                "tahmini_aylik_gelir": f"TRY {estimated_min:.0f}-{estimated_max:.0f}",
            }
        )

    return {
        "profiles": estimates,
        "estimated_total_revenue_min": round(total_min, 2),
        "estimated_total_revenue_max": round(total_max, 2),
        "estimated_total_revenue": f"TRY {total_min:.0f}-{total_max:.0f}",
    }


def generate_summary_report(
    profiles: Sequence[dict[str, Any]],
    analysis: dict[str, Any],
    monetization: dict[str, Any],
    *,
    errors: Sequence[dict[str, Any]] | None = None,
    output_dir: str | Path | None = None,
) -> dict[str, Any]:
    platform_distribution: dict[str, int] = {}
    total_audience = 0
    all_engagement = []

    revenue_lookup = {
        str(item.get("hesap") or ""): item
        for item in monetization.get("profiles", [])
        if isinstance(item, dict)
    }

    for profile in profiles:
        platform = str(profile.get("platform") or "instagram").strip().lower()
        platform_distribution[platform] = platform_distribution.get(platform, 0) + 1
        total_audience += _audience_size(profile)
        all_engagement.append(_engagement_rate(profile))

    top_entries: list[dict[str, Any]] = []
    for index, performer in enumerate(analysis.get("top_performers", []), start=1):
        identity = str(performer.get("hesap") or "")
        revenue_item = revenue_lookup.get(identity, {})
        top_entries.append(
            {
                "sira": index,
                "hesap": identity,
                "platform": performer.get("platform"),
                "etkilesim": performer.get("etkilesim"),
                "gelir": revenue_item.get("tahmini_aylik_gelir"),
            }
        )

    summary = {
        "tarih": datetime.now().strftime("%Y-%m-%d"),
        "status": "completed",
        "ok": True,
        "toplam_profil": len(profiles) + len(errors or []),
        "basarili": len(profiles),
        "basarisiz": len(errors or []),
        "toplam_takipci": total_audience,
        "ortalama_etkilesim": round(_mean(all_engagement), 4),
        "tahmini_toplam_gelir": monetization.get("estimated_total_revenue"),
        "platform_dagilimi": platform_distribution,
        "en_iyi_10": top_entries[:10],
    }
    if output_dir is not None:
        summary["output_path"] = str(output_dir)

    summary["total"] = summary["toplam_profil"]
    summary["successful"] = summary["basarili"]
    summary["failed"] = summary["basarisiz"]
    return summary


class BatchProfileScraper:
    def __init__(
        self,
        *,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT,
        timeout: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_MAX_RETRIES,
        request_spacing_seconds: float = 0.0,
        output_root: str | Path = DEFAULT_OUTPUT_ROOT,
        scraper: Any | None = None,
    ) -> None:
        self.max_concurrent = min(
            DEFAULT_MAX_CONCURRENT,
            max(1, int(max_concurrent or DEFAULT_MAX_CONCURRENT)),
        )
        self.timeout = max(1, int(timeout or DEFAULT_TIMEOUT_SECONDS))
        self.max_retries = max(0, int(max_retries or DEFAULT_MAX_RETRIES))
        self.request_spacing_seconds = max(0.0, float(request_spacing_seconds or 0.0))
        self.output_root = Path(output_root).expanduser()
        self.scraper = scraper or UniversalProfileScraper()

    async def _scrape_target(
        self,
        payload: dict[str, str],
        semaphore: asyncio.Semaphore,
    ) -> dict[str, Any]:
        target = payload["target"]
        platform = payload["platform"]

        async with semaphore:
            last_error = "unknown_error"
            for attempt in range(self.max_retries + 1):
                try:
                    result = await asyncio.wait_for(
                        self.scraper.scrape(target, platform=platform),
                        timeout=self.timeout,
                    )
                    if not isinstance(result, dict) or not result:
                        raise RuntimeError("bos_sonuc")
                    result["platform"] = platform
                    result["source_target"] = target
                    result["scraped_at"] = datetime.now().isoformat()
                    return {
                        "ok": True,
                        "target": target,
                        "platform": platform,
                        "attempts": attempt + 1,
                        "profile": result,
                    }
                except Exception as exc:  # noqa: BLE001
                    last_error = str(exc)
                    if attempt < self.max_retries:
                        await asyncio.sleep(min(2**attempt, 4))
                finally:
                    if self.request_spacing_seconds > 0:
                        await asyncio.sleep(self.request_spacing_seconds)

        return {
            "ok": False,
            "target": target,
            "platform": platform,
            "attempts": self.max_retries + 1,
            "error": last_error,
        }

    def _build_output_dir(self) -> Path:
        batch_dir = self.output_root / f"{_now_stamp()}_profiller"
        batch_dir.mkdir(parents=True, exist_ok=True)
        return batch_dir

    def _write_profile_files(
        self,
        profiles: Sequence[dict[str, Any]],
        batch_dir: Path,
    ) -> list[str]:
        saved_files: list[str] = []
        for profile in profiles:
            identity = _slugify_filename(_extract_identity(profile))
            file_path = batch_dir / f"{identity}.json"
            file_path.write_text(
                json.dumps(profile, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            saved_files.append(str(file_path))
        return saved_files

    def _write_report_files(
        self,
        batch_dir: Path,
        *,
        analysis: dict[str, Any],
        monetization: dict[str, Any],
        summary: dict[str, Any],
        errors: Sequence[dict[str, Any]],
    ) -> dict[str, str]:
        analysis_path = batch_dir / "engagement_analizi.json"
        analysis_path.write_text(
            json.dumps(analysis, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        monetization_path = batch_dir / "monetization_tahminleri.json"
        monetization_path.write_text(
            json.dumps(monetization, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        summary_path = batch_dir / "ozet_rapor.json"
        summary_path.write_text(
            json.dumps(summary, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        error_path = batch_dir / "hata_log.json"
        error_path.write_text(
            json.dumps(list(errors), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "analysis_path": str(analysis_path),
            "monetization_path": str(monetization_path),
            "summary_path": str(summary_path),
            "error_log_path": str(error_path),
        }

    async def scrape_batch(
        self,
        accounts: Iterable[str | dict[str, Any]] | None,
    ) -> dict[str, Any]:
        targets = normalize_batch_targets(accounts)
        if not targets:
            return {
                "status": "error",
                "ok": False,
                "error": "hesap_listesi_bos",
            }

        semaphore = asyncio.Semaphore(self.max_concurrent)
        results = await asyncio.gather(
            *(self._scrape_target(payload, semaphore) for payload in targets)
        )

        profiles = [item["profile"] for item in results if item.get("ok") is True]
        errors = [
            {
                "target": item.get("target"),
                "platform": item.get("platform"),
                "attempts": item.get("attempts"),
                "error": item.get("error"),
            }
            for item in results
            if item.get("ok") is not True
        ]

        analysis = analyze_engagement(profiles)
        monetization = estimate_monetization(profiles)
        batch_dir = self._build_output_dir()
        saved_files = self._write_profile_files(profiles, batch_dir)
        summary = generate_summary_report(
            profiles,
            analysis,
            monetization,
            errors=errors,
            output_dir=batch_dir,
        )
        report_paths = self._write_report_files(
            batch_dir,
            analysis=analysis,
            monetization=monetization,
            summary=summary,
            errors=errors,
        )

        return {
            "status": "completed",
            "ok": True,
            "toplam": len(targets),
            "basarili": len(profiles),
            "basarisiz": len(errors),
            "profiles": profiles,
            "errors": errors,
            "analysis": analysis,
            "monetization": monetization,
            "summary": summary,
            "output_path": str(batch_dir),
            "report_path": report_paths["summary_path"],
            "saved_files": saved_files,
            **report_paths,
        }

    async def batch_scrape_from_csv(self, csv_path: str | Path) -> dict[str, Any]:
        targets = load_batch_targets_from_csv(csv_path)
        result = await self.scrape_batch(targets)
        if isinstance(result, dict):
            result["csv_path"] = str(csv_path)
        return result

    async def scrape_from_csv(self, csv_path: str | Path) -> dict[str, Any]:
        return await self.batch_scrape_from_csv(csv_path)

    async def scrape_accounts(
        self,
        accounts: Iterable[str | dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return await self.scrape_batch(accounts)

    async def batch_scrape_accounts(
        self,
        accounts: Iterable[str | dict[str, Any]] | None,
    ) -> dict[str, Any]:
        return await self.scrape_batch(accounts)


async def batch_scrape_handler(
    csv_path: str | None = None,
    handles: Iterable[str | dict[str, Any]] | None = None,
    accounts: Iterable[str | dict[str, Any]] | None = None,
    profiles: Iterable[str | dict[str, Any]] | None = None,
    targets: Iterable[str | dict[str, Any]] | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    scraper = BatchProfileScraper(
        max_concurrent=int(kwargs.get("max_concurrent") or DEFAULT_MAX_CONCURRENT),
        timeout=int(kwargs.get("timeout") or DEFAULT_TIMEOUT_SECONDS),
        max_retries=int(kwargs.get("max_retries") or DEFAULT_MAX_RETRIES),
        request_spacing_seconds=float(kwargs.get("request_spacing_seconds") or 0.0),
        output_root=kwargs.get("output_root") or DEFAULT_OUTPUT_ROOT,
        scraper=kwargs.get("scraper"),
    )

    if csv_path:
        return await scraper.batch_scrape_from_csv(csv_path)

    items = accounts or handles or profiles or targets or []
    return await scraper.scrape_batch(items)


def run_batch_scrape_sync(**kwargs: Any) -> dict[str, Any]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        pass
    else:
        raise RuntimeError("run_batch_scrape_sync aktif event loop icinde kullanilamaz")
    return asyncio.run(batch_scrape_handler(**kwargs))


handle_batch_scrape = batch_scrape_handler
run_batch_scrape = batch_scrape_handler


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
