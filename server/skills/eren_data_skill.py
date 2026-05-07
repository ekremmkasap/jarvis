from __future__ import annotations

import csv
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

try:
    from server.skills.obsidian_sync_skill import get_obsidian_vault_dir
except ImportError:
    from obsidian_sync_skill import get_obsidian_vault_dir


ROOT_DIR = Path(__file__).resolve().parents[2]
LOG_PATH = ROOT_DIR / "server" / "logs" / "eren_analysis.jsonl"
THRESHOLDS_PATH = ROOT_DIR / "server" / "config" / "eren_kpi_thresholds.yaml"
REPORTS_DIR = Path("personas/eren/reports")


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "").strip().lower())
    ascii_text = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-") or "rapor"


def _normalize_key(value: str) -> str:
    return _slugify(value).replace("-", "_")


def _coerce_number(value: Any) -> float | None:
    text = str(value or "").strip()
    if not text:
        return None
    normalized = text.replace("%", "").replace(" ", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def _log_event(action: str, payload: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": datetime.utcnow().isoformat(),
        "persona": "eren",
        "action": action,
        "payload": payload,
    }
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=True) + "\n")


def _resolve_vault_dir(vault_dir: str | Path | None = None) -> Path:
    candidate = Path(vault_dir).expanduser() if vault_dir is not None else get_obsidian_vault_dir()
    if candidate is None:
        raise FileNotFoundError("Obsidian vault path is not configured")
    resolved = candidate.expanduser().resolve(strict=False)
    if not resolved.exists() or not resolved.is_dir():
        raise FileNotFoundError(f"Obsidian vault path is not available: {resolved}")
    return resolved


def _load_thresholds() -> dict[str, Any]:
    if not THRESHOLDS_PATH.exists():
        return {"kpis": {}}
    payload = yaml.safe_load(THRESHOLDS_PATH.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {"kpis": {}}


def analyze_csv(file_path: str, max_rows: int = 1000) -> dict[str, Any]:
    target_text = str(file_path or "").strip()
    if not target_text:
        result = {"ok": False, "error": "file_path_required", "message": "Dosya yolu gerekli."}
        _log_event("analyze_csv", result)
        return result

    target = Path(target_text)
    if not target.exists() or not target.is_file():
        result = {"ok": False, "error": "file_not_found", "message": f"CSV dosyasi bulunamadi: {target}"}
        _log_event("analyze_csv", result)
        return result

    try:
        with target.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ValueError("CSV baslik satiri bulunamadi")

            columns = [str(name or "").strip() for name in reader.fieldnames]
            trackers: dict[str, dict[str, Any]] = {
                column: {
                    "blank": 0,
                    "non_blank": 0,
                    "numeric": [],
                    "text": [],
                    "is_numeric": True,
                }
                for column in columns
            }
            rows = 0
            preview: list[dict[str, Any]] = []

            for row in reader:
                if rows >= max_rows:
                    break
                rows += 1
                clean_row: dict[str, Any] = {}
                for column in columns:
                    raw_value = row.get(column, "")
                    clean_value = "" if raw_value is None else str(raw_value).strip()
                    clean_row[column] = clean_value
                    if not clean_value:
                        trackers[column]["blank"] += 1
                        continue

                    trackers[column]["non_blank"] += 1
                    trackers[column]["text"].append(clean_value)
                    numeric_value = _coerce_number(clean_value)
                    if numeric_value is None:
                        trackers[column]["is_numeric"] = False
                    else:
                        trackers[column]["numeric"].append(numeric_value)
                if len(preview) < 5:
                    preview.append(clean_row)

        stats: dict[str, dict[str, Any]] = {}
        for column, tracker in trackers.items():
            blank_rate = round((tracker["blank"] / rows), 4) if rows else 0.0
            if tracker["non_blank"] and tracker["is_numeric"]:
                numbers = tracker["numeric"]
                stats[column] = {
                    "type": "numeric",
                    "min": min(numbers),
                    "max": max(numbers),
                    "avg": round(sum(numbers) / len(numbers), 2),
                    "blank_rate": blank_rate,
                }
            else:
                stats[column] = {
                    "type": "text",
                    "unique_count": len(set(tracker["text"])),
                    "blank_rate": blank_rate,
                }

        result = {
            "ok": True,
            "rows": rows,
            "columns": columns,
            "stats": stats,
            "preview": preview,
        }
        _log_event("analyze_csv", {"file_path": str(target), "rows": rows, "columns": columns})
        return result
    except Exception as exc:
        result = {"ok": False, "error": str(exc), "message": f"CSV analizi basarisiz: {exc}"}
        _log_event("analyze_csv", {"file_path": str(target), "error": str(exc)})
        return result


def _evaluate_kpi(value: float, config: dict[str, Any]) -> str:
    direction = str(config.get("direction") or "higher").strip().lower()
    if direction == "lower":
        critical = config.get("critical_above")
        warning = config.get("warning_above")
        if critical is not None and value >= float(critical):
            return "kritik"
        if warning is not None and value >= float(warning):
            return "dikkat"
        return "hedefin ustunde"

    critical = config.get("critical_below")
    warning = config.get("warning_below")
    if critical is not None and value <= float(critical):
        return "kritik"
    if warning is not None and value <= float(warning):
        return "dikkat"
    return "hedefin ustunde"


def _format_kpi_value(value: float, config: dict[str, Any]) -> str:
    fmt = str(config.get("format") or "").strip().lower()
    unit = str(config.get("unit") or "").strip()
    if fmt == "percent":
        rendered = f"{value * 100:.1f}%"
    elif value.is_integer():
        rendered = str(int(value))
    else:
        rendered = f"{value:.2f}"
    return f"{rendered} {unit}".strip()


def kpi_summary(data: dict[str, Any] | str) -> dict[str, Any]:
    try:
        payload = json.loads(data) if isinstance(data, str) else data
    except json.JSONDecodeError:
        result = {
            "ok": False,
            "error": "invalid_json",
            "message": 'Gecersiz KPI JSON. Ornek: {"gelir":15000,"musteri":23}',
        }
        _log_event("kpi_summary", result)
        return result

    if not isinstance(payload, dict) or not payload:
        result = {
            "ok": False,
            "error": "payload_required",
            "message": "KPI verisi bos veya gecersiz.",
        }
        _log_event("kpi_summary", result)
        return result

    thresholds = _load_thresholds().get("kpis", {})
    lines = ["*Eren KPI Ozeti*", ""]
    evaluated: dict[str, dict[str, Any]] = {}

    for raw_key, raw_value in payload.items():
        normalized_key = _normalize_key(str(raw_key))
        config = thresholds.get(normalized_key, {})
        numeric_value = _coerce_number(raw_value)
        if numeric_value is None:
            status = "veri gecersiz"
            rendered_value = str(raw_value)
        else:
            status = _evaluate_kpi(numeric_value, config)
            rendered_value = _format_kpi_value(numeric_value, config)

        label = str(config.get("label") or raw_key)
        lines.append(f"- {label}: {rendered_value} -> {status}")
        evaluated[normalized_key] = {"label": label, "value": rendered_value, "status": status}

    result = {"ok": True, "summary": "\n".join(lines), "evaluated": evaluated}
    _log_event("kpi_summary", {"keys": list(evaluated.keys())})
    return result


def quick_report(file_path: str, *, vault_dir: str | Path | None = None) -> dict[str, Any]:
    analysis = analyze_csv(file_path)
    if analysis.get("ok") is False:
        return analysis

    stats = analysis["stats"]
    summary_lines = [
        f"Dosya: {Path(file_path).name}",
        f"Satir: {analysis['rows']}",
        f"Kolonlar: {', '.join(analysis['columns'])}",
        "",
        "One cikan alanlar:",
    ]
    for column in analysis["columns"]:
        column_stats = stats.get(column, {})
        if column_stats.get("type") == "numeric":
            summary_lines.append(
                f"- {column}: min={column_stats['min']} max={column_stats['max']} avg={column_stats['avg']} blank={column_stats['blank_rate']:.0%}"
            )
        else:
            summary_lines.append(
                f"- {column}: unique={column_stats['unique_count']} blank={column_stats['blank_rate']:.0%}"
            )
    summary = "\n".join(summary_lines)

    note_body = "\n".join(
        [
            f"# {Path(file_path).name}",
            "",
            summary,
            "",
            "## Preview",
            *[f"- {row}" for row in analysis["preview"]],
            "",
        ]
    )

    try:
        vault_root = _resolve_vault_dir(vault_dir)
        target_dir = (vault_root / REPORTS_DIR).resolve(strict=False)
        target_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y-%m-%d")
        file_slug = _slugify(Path(file_path).stem)
        note_path = (target_dir / f"{stamp}_{file_slug}.md").resolve(strict=False)
        if vault_root not in note_path.parents and note_path != vault_root:
            raise ValueError("Target path escapes vault root")
        note_path.write_text(note_body, encoding="utf-8")
        saved_to = note_path.relative_to(vault_root).as_posix()
        result = {"ok": True, "summary": summary, "saved_to": saved_to}
        _log_event("quick_report", {"file_path": file_path, "saved_to": saved_to})
        return result
    except Exception as exc:
        result = {
            "ok": False,
            "summary": summary,
            "error": str(exc),
            "message": "Obsidian raporu kaydedilemedi.",
        }
        _log_event("quick_report", {"file_path": file_path, "error": str(exc)})
        return result


__all__ = ["analyze_csv", "kpi_summary", "quick_report"]
