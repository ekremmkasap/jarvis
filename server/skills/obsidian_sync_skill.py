from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
import unicodedata
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
WIKI_DIR = ROOT_DIR / "wiki"
REPO_OBSIDIAN_CONFIG_DIR = ROOT_DIR / ".obsidian"
ENV_FILE = ROOT_DIR / ".env"
DEFAULT_SYNC_INTERVAL_SECONDS = 30.0
DEFAULT_OBSIDIAN_EXECUTABLES = (
    Path.home() / "AppData" / "Local" / "Programs" / "Obsidian" / "Obsidian.exe",
    Path.home() / "AppData" / "Local" / "Obsidian" / "Obsidian.exe",
    Path("C:/Program Files/Obsidian/Obsidian.exe"),
)
DEFAULT_OBSIDIAN_TEMPLATE_FILES = (
    "app.json",
    "appearance.json",
    "core-plugins.json",
    "workspace.json",
)

LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(logging.NullHandler())


@dataclass(frozen=True)
class FileSnapshot:
    mtime_ns: int
    size: int


_ENV_CACHE: dict[str, str] | None = None
_ENV_CACHE_MTIME_NS: int | None = None
_SYNC_LOCK = threading.Lock()
_SYNC_WAKE_EVENT = threading.Event()
_SYNC_THREAD: threading.Thread | None = None
_SYNC_INITIALIZED = False
_LAST_WIKI_STATE: dict[Path, FileSnapshot] = {}
_LAST_VAULT_STATE: dict[Path, FileSnapshot] = {}


def _normalize_text(value: str) -> str:
    return unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")


def _slugify(title: str) -> str:
    normalized = _normalize_text(title).lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized or "not"


def _title_for_slug(slug: str) -> str:
    return slug.replace("-", " ").strip().title() or slug


def _page_path(slug: str) -> Path:
    return WIKI_DIR / f"{slug}.md"


def _wiki_pages() -> list[Path]:
    if not WIKI_DIR.exists():
        return []
    return sorted(path for path in WIKI_DIR.glob("*.md") if path.is_file())


def _parse_env_file() -> dict[str, str]:
    global _ENV_CACHE, _ENV_CACHE_MTIME_NS

    try:
        mtime_ns = ENV_FILE.stat().st_mtime_ns
    except OSError:
        _ENV_CACHE = {}
        _ENV_CACHE_MTIME_NS = None
        return {}

    if _ENV_CACHE is not None and _ENV_CACHE_MTIME_NS == mtime_ns:
        return _ENV_CACHE

    parsed: dict[str, str] = {}
    try:
        for raw_line in ENV_FILE.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip("\"'")
            if key:
                parsed[key] = value
    except OSError:
        parsed = {}

    _ENV_CACHE = parsed
    _ENV_CACHE_MTIME_NS = mtime_ns
    return parsed


def _env_value(*names: str, default: str = "") -> str:
    for name in names:
        value = os.environ.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()

    env_values = _parse_env_file()
    for name in names:
        value = env_values.get(name)
        if value is not None and str(value).strip():
            return str(value).strip()

    return default


def get_obsidian_api_token() -> str:
    return _env_value("OBSIDIAN_API_TOKEN", "OBSIDIAN_TOKEN", "OBSIDIAN_API_KEY")


def get_obsidian_vault_dir() -> Path | None:
    raw = _env_value("OBSIDIAN_VAULT_PATH", "OBSIDIAN_VAULT_DIR", "OBSIDIAN_PATH")
    if not raw:
        return None
    return Path(raw).expanduser()


def get_default_obsidian_vault_dir() -> Path:
    return WIKI_DIR


def ensure_local_obsidian_vault(vault_dir: str | Path | None = None) -> Path:
    target = (
        Path(vault_dir).expanduser()
        if vault_dir is not None
        else get_default_obsidian_vault_dir()
    )
    target.mkdir(parents=True, exist_ok=True)

    config_dir = target / ".obsidian"
    config_dir.mkdir(parents=True, exist_ok=True)

    if REPO_OBSIDIAN_CONFIG_DIR.exists():
        for file_name in DEFAULT_OBSIDIAN_TEMPLATE_FILES:
            source = REPO_OBSIDIAN_CONFIG_DIR / file_name
            destination = config_dir / file_name
            if source.exists() and not destination.exists():
                try:
                    shutil.copy2(source, destination)
                except OSError as exc:
                    LOGGER.debug(
                        "Obsidian template copy skipped for %s: %s",
                        file_name,
                        exc,
                    )

    return target


def find_obsidian_executable() -> Path | None:
    configured = _env_value("OBSIDIAN_EXE", "OBSIDIAN_EXECUTABLE")
    if configured:
        candidate = Path(configured).expanduser()
        if candidate.exists():
            return candidate

    for candidate in DEFAULT_OBSIDIAN_EXECUTABLES:
        if candidate.exists():
            return candidate
    return None


def open_obsidian_vault(vault_dir: str | Path | None = None) -> str:
    vault_root = ensure_local_obsidian_vault(vault_dir)
    executable = find_obsidian_executable()
    if executable is None:
        return f"Obsidian uygulamasi bulunamadi. Vault hazir: {vault_root}"

    try:
        subprocess.Popen(
            [str(executable), str(vault_root)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return f"Obsidian aciliyor. Vault: {vault_root}"
    except OSError as exc:
        return f"Obsidian acilamadi: {exc}"


def get_obsidian_sync_interval() -> float:
    raw = _env_value(
        "OBSIDIAN_SYNC_INTERVAL",
        "OBSIDIAN_POLL_INTERVAL",
        default=str(DEFAULT_SYNC_INTERVAL_SECONDS),
    )
    try:
        interval = float(raw)
    except (TypeError, ValueError):
        LOGGER.debug("Invalid Obsidian sync interval %r, using default %s", raw, DEFAULT_SYNC_INTERVAL_SECONDS)
        return DEFAULT_SYNC_INTERVAL_SECONDS
    return max(5.0, interval)


def _replace_known_links(content: str, current_slug: str = "") -> str:
    updated = str(content or "").strip()
    for page in _wiki_pages():
        slug = page.stem
        if slug == current_slug:
            continue
        title = _title_for_slug(slug)
        patterns = {title, slug.replace("-", " ")}
        for pattern in patterns:
            pattern = pattern.strip()
            if not pattern or f"[[{slug}]]" in updated:
                continue
            updated = re.sub(
                rf"\b{re.escape(pattern)}\b",
                f"[[{slug}]]",
                updated,
                count=1,
                flags=re.IGNORECASE,
            )
    return updated


def _write_text_if_changed(path: Path, content: str) -> bool:
    existing = None
    try:
        if path.exists():
            existing = path.read_text(encoding="utf-8", errors="ignore")
    except OSError as exc:
        LOGGER.warning("Obsidian sync read failed for %s: %s", path, exc)

    if existing == content:
        return False

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return True
    except OSError as exc:
        LOGGER.warning("Obsidian sync write failed for %s: %s", path, exc)
        return False


def _refresh_index() -> None:
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    pages = [page for page in _wiki_pages() if page.stem != "index"]
    lines = [
        "# Jarvis Wiki Index",
        "",
        "Bu dosya [[wiki]] komutunun ana navigasyon kaynagidir.",
        "",
        "## Sayfalar",
    ]
    for page in pages:
        lines.append(f"- [[{page.stem}]]")
    _write_text_if_changed(WIKI_DIR / "index.md", "\n".join(lines).strip() + "\n")


def _scan_markdown_state(base_dir: Path) -> dict[Path, FileSnapshot]:
    if not base_dir.exists():
        return {}

    state: dict[Path, FileSnapshot] = {}
    for path in base_dir.rglob("*.md"):
        if not path.is_file():
            continue
        try:
            stat = path.stat()
        except OSError as exc:
            LOGGER.warning("Obsidian sync stat failed for %s: %s", path, exc)
            continue
        state[path.relative_to(base_dir)] = FileSnapshot(stat.st_mtime_ns, stat.st_size)
    return state


def _copy_markdown(source_root: Path, target_root: Path, relative_path: Path) -> bool:
    source = source_root / relative_path
    target = target_root / relative_path

    if not source.exists():
        return False

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        return True
    except OSError as exc:
        LOGGER.warning("Obsidian sync copy failed %s -> %s: %s", source, target, exc)
        return False


def _resolve_relative_change(
    relative_path: Path,
    wiki_state: dict[Path, FileSnapshot],
    vault_state: dict[Path, FileSnapshot],
) -> bool:
    wiki_snapshot = wiki_state.get(relative_path)
    vault_snapshot = vault_state.get(relative_path)
    last_wiki_snapshot = _LAST_WIKI_STATE.get(relative_path)
    last_vault_snapshot = _LAST_VAULT_STATE.get(relative_path)

    if wiki_snapshot == vault_snapshot:
        return False

    if wiki_snapshot and not vault_snapshot:
        if not _SYNC_INITIALIZED or last_wiki_snapshot != wiki_snapshot:
            vault_dir = get_obsidian_vault_dir()
            if vault_dir is not None:
                return _copy_markdown(WIKI_DIR, vault_dir, relative_path)
        return False

    if vault_snapshot and not wiki_snapshot:
        if not _SYNC_INITIALIZED or last_vault_snapshot != vault_snapshot:
            vault_dir = get_obsidian_vault_dir()
            if vault_dir is not None:
                return _copy_markdown(vault_dir, WIKI_DIR, relative_path)
        return False

    if not wiki_snapshot or not vault_snapshot:
        return False

    if wiki_snapshot.mtime_ns > vault_snapshot.mtime_ns:
        vault_dir = get_obsidian_vault_dir()
        if vault_dir is not None:
            return _copy_markdown(WIKI_DIR, vault_dir, relative_path)
        return False

    if vault_snapshot.mtime_ns > wiki_snapshot.mtime_ns:
        vault_dir = get_obsidian_vault_dir()
        if vault_dir is not None:
            return _copy_markdown(vault_dir, WIKI_DIR, relative_path)
        return False

    wiki_changed = last_wiki_snapshot != wiki_snapshot
    vault_changed = last_vault_snapshot != vault_snapshot

    if wiki_changed and not vault_changed:
        vault_dir = get_obsidian_vault_dir()
        if vault_dir is not None:
            return _copy_markdown(WIKI_DIR, vault_dir, relative_path)
        return False

    if vault_changed and not wiki_changed:
        vault_dir = get_obsidian_vault_dir()
        if vault_dir is not None:
            return _copy_markdown(vault_dir, WIKI_DIR, relative_path)
        return False

    vault_dir = get_obsidian_vault_dir()
    if vault_dir is not None:
        return _copy_markdown(WIKI_DIR, vault_dir, relative_path)
    return False


def _sync_obsidian_once() -> None:
    global _SYNC_INITIALIZED, _LAST_VAULT_STATE, _LAST_WIKI_STATE

    vault_dir = get_obsidian_vault_dir()
    if vault_dir is None:
        return

    vault_dir = vault_dir.expanduser()
    if not vault_dir.exists():
        LOGGER.debug("Obsidian vault path does not exist: %s", vault_dir)
        return

    if vault_dir.resolve(strict=False) == WIKI_DIR.resolve(strict=False):
        LOGGER.debug("Obsidian vault path matches wiki dir; sync skipped")
        return

    WIKI_DIR.mkdir(parents=True, exist_ok=True)

    wiki_state = _scan_markdown_state(WIKI_DIR)
    vault_state = _scan_markdown_state(vault_dir)

    changed_paths = set(wiki_state) | set(vault_state) | set(_LAST_WIKI_STATE) | set(_LAST_VAULT_STATE)
    changed_paths = {
        relative_path
        for relative_path in changed_paths
        if wiki_state.get(relative_path) != _LAST_WIKI_STATE.get(relative_path)
        or vault_state.get(relative_path) != _LAST_VAULT_STATE.get(relative_path)
        or not _SYNC_INITIALIZED
    }

    copied_any = False
    for relative_path in sorted(changed_paths):
        try:
            copied_any = _resolve_relative_change(relative_path, wiki_state, vault_state) or copied_any
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Obsidian sync failed for %s: %s", relative_path, exc)

    if copied_any:
        _refresh_index()
        wiki_state = _scan_markdown_state(WIKI_DIR)
        vault_state = _scan_markdown_state(vault_dir)

    _LAST_WIKI_STATE = wiki_state
    _LAST_VAULT_STATE = vault_state
    _SYNC_INITIALIZED = True


def _sync_loop() -> None:
    while True:
        try:
            _sync_obsidian_once()
        except Exception as exc:  # noqa: BLE001
            LOGGER.warning("Obsidian sync loop error: %s", exc)

        interval = get_obsidian_sync_interval()
        _SYNC_WAKE_EVENT.wait(interval)
        _SYNC_WAKE_EVENT.clear()


def ensure_sync_worker() -> bool:
    global _SYNC_THREAD

    vault_dir = get_obsidian_vault_dir()
    if vault_dir is None:
        return False

    with _SYNC_LOCK:
        if _SYNC_THREAD and _SYNC_THREAD.is_alive():
            return True

        _SYNC_THREAD = threading.Thread(
            target=_sync_loop,
            name="obsidian-sync-worker",
            daemon=True,
        )
        _SYNC_THREAD.start()
        return True


def trigger_sync() -> None:
    if ensure_sync_worker():
        _SYNC_WAKE_EVENT.set()


def create_page(title: str, content: str) -> str:
    clean_title = str(title or "").strip()
    clean_content = str(content or "").strip()
    if not clean_title or not clean_content:
        return "Kullanim: /wiki ekle [baslik] | [icerik]"

    ensure_sync_worker()
    WIKI_DIR.mkdir(parents=True, exist_ok=True)
    slug = _slugify(clean_title)
    path = _page_path(slug)
    linked_content = _replace_known_links(clean_content, current_slug=slug)
    body = f"# {clean_title}\n\n{linked_content}\n"
    path.write_text(body, encoding="utf-8")
    _refresh_index()
    trigger_sync()
    return f"Wiki sayfasi kaydedildi: `wiki/{path.name}`"


def search_page(query: str) -> Path | None:
    ensure_sync_worker()
    query_text = str(query or "").strip().lower()
    if not query_text:
        return WIKI_DIR / "index.md"
    slug_query = _slugify(query_text)
    exact = _page_path(slug_query)
    if exact.exists():
        return exact
    for page in _wiki_pages():
        page_key = page.stem.lower()
        title_key = _title_for_slug(page.stem).lower()
        if query_text in page_key or query_text in title_key:
            return page
    return None


def read_page(query: str) -> str:
    ensure_sync_worker()
    target = search_page(query)
    if target is None or not target.exists():
        return f"Wiki sayfasi bulunamadi: `{query}`"
    text = target.read_text(encoding="utf-8", errors="ignore").strip()
    return text[:3500]


def list_pages() -> str:
    ensure_sync_worker()
    pages = [page.stem for page in _wiki_pages()]
    if not pages:
        return "Wiki bos."
    lines = ["# Wiki Sayfalari", ""]
    for slug in pages:
        lines.append(f"- [[{slug}]]")
    return "\n".join(lines)


def run_wiki(args: str = "") -> str:
    ensure_sync_worker()
    raw = str(args or "").strip()
    if not raw:
        target = WIKI_DIR / "index.md"
        return target.read_text(encoding="utf-8", errors="ignore") if target.exists() else list_pages()

    lowered = raw.lower()
    if lowered.startswith("ekle "):
        payload = raw[5:].strip()
        if "|" not in payload:
            return "Kullanim: /wiki ekle [baslik] | [icerik]"
        title, content = payload.split("|", 1)
        return create_page(title.strip(), content.strip())

    return read_page(raw)


try:
    ensure_sync_worker()
except Exception as exc:  # noqa: BLE001
    LOGGER.warning("Obsidian sync worker bootstrap failed: %s", exc)
