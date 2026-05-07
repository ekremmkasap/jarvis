from __future__ import annotations

from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
REPO_DIR = ROOT_DIR / "external-repos" / "crewAI"
CREWAI_VERSION = "0.28.8"
GENAI_DEPENDENCY = "langchain-google-genai>=0.0.9"
INSTALL_COMMAND = f'pip install "crewai=={CREWAI_VERSION}" "{GENAI_DEPENDENCY}"'


def _normalize_args(args: str = "") -> str:
    return str(args or "").strip().lower()


def _relative_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT_DIR).as_posix()
    except ValueError:
        return str(path)


def run_crewai(args: str = "") -> str:
    repo_ok = REPO_DIR.exists()

    try:
        import crewai  # type: ignore
    except ImportError:
        installed = False
        version = "kurulu degil"
    else:
        installed = True
        version = str(getattr(crewai, "__version__", "kurulu")).strip() or "kurulu"

    normalized = _normalize_args(args)
    lines = [
        "CrewAI durum",
        "",
        f"Repo: {'OK' if repo_ok else 'MISSING'} `{_relative_path(REPO_DIR)}`",
        f"Pip paket: {'OK v' + version if installed else 'MISSING'}",
        "Python: 3.11 uyumlu",
        f"Ek bagimlilik: `{GENAI_DEPENDENCY}`",
        "",
        "Kurulum:",
        f"`{INSTALL_COMMAND}`",
    ]

    if normalized not in {"", "durum", "status"}:
        lines.extend(
            [
                "",
                f"Istek: `{str(args).strip()}`",
                "Not: Bu komut su an durum ve kurulum ozeti dondurur.",
            ]
        )

    return "\n".join(lines)
