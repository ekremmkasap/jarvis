from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(r"C:\Users\sergen\Desktop\jarvis-mission-control")
PRIMARY_REPO_DIR = ROOT_DIR / "external-repos" / "claw-code"
FALLBACK_REPO_DIR = ROOT_DIR / "external-repos" / "claw-code-old"


def _resolve_repo_dir() -> tuple[Path, bool]:
    if PRIMARY_REPO_DIR.exists():
        return PRIMARY_REPO_DIR, False
    if FALLBACK_REPO_DIR.exists():
        return FALLBACK_REPO_DIR, True
    return PRIMARY_REPO_DIR, False


def run_claw_code(args: str = "") -> str:
    repo_dir, using_fallback = _resolve_repo_dir()
    repo_ok = repo_dir.exists()
    readme_path = repo_dir / "README.md"
    has_readme = readme_path.exists()

    readme_snippet = ""
    if has_readme:
        try:
            readme_snippet = readme_path.read_text(encoding="utf-8", errors="ignore")[:400]
            readme_snippet = readme_snippet.encode("ascii", "ignore").decode("ascii")
        except Exception:
            readme_snippet = ""

    repo_label = str(repo_dir.relative_to(ROOT_DIR)).replace("\\", "/") if repo_ok else "external-repos/claw-code"

    lines = [
        "**Claw-Code**",
        "",
        f"Repo: {'OK' if repo_ok else 'MISSING'} `{repo_label}`",
    ]

    if using_fallback:
        lines += [
            "Durum: Ana `external-repos/claw-code` dizini yok; yerel yedek `claw-code-old` kullaniliyor.",
            "Not: Upstream repo su an kapali/disabled gorunuyor.",
        ]

    lines += [
        "",
        "**Ozellik:**",
        "- Claude/Claw tarzı terminal coding-agent referansi",
        "- Jarvis `/coder` ve execution core tasarimi icin referans kaynak",
    ]

    if args.strip():
        lines += [
            "",
            f"İstek: `{args.strip()}`",
        ]

    if readme_snippet:
        lines += [
            "",
            "**README Ozet:**",
            f"```text\n{readme_snippet[:300]}\n```",
        ]

    lines += [
        "",
        "**Jarvis Entegrasyonu:**",
        "Bu repo calisan runtime degil; referans kaynak olarak tutuluyor.",
        "Aktif agent yolu artik OpenClaw-first ve cloud model routing uzerinden gidiyor.",
    ]

    return "\n".join(lines)
