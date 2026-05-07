"""
Playwright-backed browser automation skill for Jarvis.

The skill keeps a visible Chromium session per user so multi-step browser
commands can continue on the same page across turns.
"""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

try:
    from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
    from playwright.sync_api import sync_playwright
except ImportError:
    PlaywrightTimeoutError = RuntimeError  # type: ignore[assignment]
    sync_playwright = None


ROOT_DIR = Path(__file__).resolve().parents[2]
BROWSER_DATA_DIR = ROOT_DIR / "server" / "data" / "browser"
_BROWSER_SESSIONS: dict[str, "BrowserSession"] = {}
_BROWSER_LOCK = threading.RLock()
_DEFAULT_TIMEOUT_MS = 15000

_SITE_ALIASES = {
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "notion": "https://www.notion.so",
    "x": "https://x.com",
    "twitter": "https://x.com",
}

_SEARCH_SELECTORS = [
    "input[type='search']",
    "input[name='search_query']",
    "input[placeholder*='Ara' i]",
    "input[placeholder*='Search' i]",
    "textarea[name='search_query']",
    "textarea",
]

_TEXT_INPUT_SELECTORS = [
    "input:focus",
    "textarea:focus",
    "[contenteditable='true']:focus",
    "input[type='text']",
    "input[type='search']",
    "textarea",
    "[contenteditable='true']",
]


def _normalize_text(value: str) -> str:
    return (
        value.replace("ı", "i")
        .replace("İ", "I")
        .replace("ğ", "g")
        .replace("Ğ", "G")
        .replace("ş", "s")
        .replace("Ş", "S")
        .replace("ç", "c")
        .replace("Ç", "C")
        .replace("ö", "o")
        .replace("Ö", "O")
        .replace("ü", "u")
        .replace("Ü", "U")
    )


def _sanitize_user_id(user_id: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(user_id or "default")).strip("_")
    return cleaned or "default"


def _ensure_playwright_available() -> None:
    if sync_playwright is None:
        raise RuntimeError(
            "Playwright kurulu degil. `pip install playwright` ve `playwright install chromium` calistirin."
        )


def _looks_like_selector(target: str) -> bool:
    stripped = target.strip()
    return stripped.startswith(("#", ".", "[", "//", "text=", "xpath="))


def _resolve_url(raw_target: str) -> str:
    target = raw_target.strip()
    lowered = _normalize_text(target).lower()
    if lowered in _SITE_ALIASES:
        return _SITE_ALIASES[lowered]
    if re.match(r"^[a-z]+://", target, flags=re.IGNORECASE):
        return target
    if "." in target and " " not in target:
        return f"https://{target}"
    return f"https://www.google.com/search?q={target.replace(' ', '+')}"


@dataclass
class ParsedCommand:
    action: str
    value: str = ""


class BrowserSession:
    def __init__(self, user_id: str) -> None:
        self.user_id = _sanitize_user_id(user_id)
        self.session_dir = BROWSER_DATA_DIR / self.user_id
        self.session_dir.mkdir(parents=True, exist_ok=True)
        self._playwright = None
        self._browser = None
        self._context = None
        self._page = None

    def _ensure_page(self):
        _ensure_playwright_available()
        if self._page is not None and not self._page.is_closed():
            return self._page

        if self._playwright is None:
            self._playwright = sync_playwright().start()

        if self._browser is None:
            self._browser = self._playwright.chromium.launch(
                headless=False,
                args=["--start-maximized"],
            )

        if self._context is None:
            self._context = self._browser.new_context(viewport={"width": 1440, "height": 900})

        self._page = self._context.new_page()
        self._page.set_default_timeout(_DEFAULT_TIMEOUT_MS)
        return self._page

    def _first_success(self, operations: list[Callable[[], str]]) -> str:
        last_error = None
        for operation in operations:
            try:
                return operation()
            except Exception as exc:
                last_error = exc
        if last_error is None:
            raise RuntimeError("Uygun browser islemi bulunamadi.")
        raise last_error

    def open_url(self, raw_target: str) -> str:
        page = self._ensure_page()
        url = _resolve_url(raw_target)
        try:
            page.goto(url, wait_until="domcontentloaded")
        except PlaywrightTimeoutError:
            return f"Sayfa acildi ancak yukleme zaman asimina girdi: {url}"
        return f"Tarayici acildi: {page.url}"

    def search(self, query: str) -> str:
        page = self._ensure_page()
        if page.url == "about:blank":
            return self.open_url(f"google {query}")

        for selector in _SEARCH_SELECTORS:
            locator = page.locator(selector).first
            try:
                if locator.count() == 0:
                    continue
                locator.click()
                locator.fill(query)
                locator.press("Enter")
                return f"Arama yapildi: {query}"
            except Exception:
                continue

        page.goto(f"https://www.google.com/search?q={query.replace(' ', '+')}", wait_until="domcontentloaded")
        return f"Arama yapildi: {query}"

    def click(self, target: str) -> str:
        page = self._ensure_page()
        if _looks_like_selector(target):
            page.locator(target).first.click(timeout=_DEFAULT_TIMEOUT_MS)
            return f"Ogaya tiklandi: {target}"

        regex = re.compile(re.escape(target), re.IGNORECASE)
        operations = [
            lambda: self._click_locator(page.get_by_role("button", name=regex).first, target),
            lambda: self._click_locator(page.get_by_role("link", name=regex).first, target),
            lambda: self._click_locator(page.get_by_text(regex).first, target),
            lambda: self._click_locator(page.get_by_placeholder(regex).first, target),
        ]
        return self._first_success(operations)

    def _click_locator(self, locator, target: str) -> str:
        locator.click(timeout=_DEFAULT_TIMEOUT_MS)
        return f"Ogaya tiklandi: {target}"

    def type_text(self, text: str) -> str:
        page = self._ensure_page()
        for selector in _TEXT_INPUT_SELECTORS:
            locator = page.locator(selector).first
            try:
                if locator.count() == 0:
                    continue
                locator.click(timeout=2000)
                locator.fill(text)
                return "Metin yazildi."
            except Exception:
                continue

        raise RuntimeError("Yazilacak aktif bir alan bulunamadi.")

    def screenshot(self) -> str:
        page = self._ensure_page()
        screenshot_path = self.session_dir / f"screenshot-{int(time.time())}.png"
        page.screenshot(path=str(screenshot_path), full_page=True)
        return f"Ekran goruntusu kaydedildi: {screenshot_path}"

    def close(self) -> str:
        if self._page is not None:
            try:
                self._page.close()
            except Exception:
                pass
            self._page = None
        if self._context is not None:
            try:
                self._context.close()
            except Exception:
                pass
            self._context = None
        if self._browser is not None:
            try:
                self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright is not None:
            try:
                self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
        return "Tarayici oturumu kapatildi."


def _parse_browser_command(args: str) -> ParsedCommand:
    raw = (args or "").strip()
    if not raw:
        raise ValueError(
            "Kullanim: /tarayici [ac|ara|tikla|yaz|ekran goruntusu|kapat] [hedef]"
        )

    lowered = _normalize_text(raw).lower()
    if lowered in {"kapat", "close"}:
        return ParsedCommand("close")
    if lowered in {"ekran goruntusu", "ekran goruntusu al", "screenshot"}:
        return ParsedCommand("screenshot")

    patterns = [
        (r"^(ac|aç)\s+(.+)$", "open"),
        (r"^(.+?)\s+(ac|aç)$", "open"),
        (r"^(ara)\s*:?\s*(.+)$", "search"),
        (r"^(tikla|tıkla|click)\s*:?\s*(.+)$", "click"),
        (r"^(yaz|type)\s*:?\s*(.+)$", "type"),
    ]
    for pattern, action in patterns:
        match = re.match(pattern, raw, flags=re.IGNORECASE)
        if match:
            value = next((group for group in match.groups()[::-1] if group and group.lower() not in {"ac", "aç", "ara", "tikla", "tıkla", "click", "yaz", "type"}), "")
            return ParsedCommand(action, value.strip())

    if raw.startswith(("http://", "https://")) or "." in raw:
        return ParsedCommand("open", raw)

    return ParsedCommand("search", raw)


def _get_or_create_session(user_id: str) -> BrowserSession:
    key = _sanitize_user_id(user_id)
    with _BROWSER_LOCK:
        session = _BROWSER_SESSIONS.get(key)
        if session is None:
            session = BrowserSession(key)
            _BROWSER_SESSIONS[key] = session
        return session


def _drop_session(user_id: str) -> None:
    with _BROWSER_LOCK:
        _BROWSER_SESSIONS.pop(_sanitize_user_id(user_id), None)


def handle_browser(args: str, user_id: str = "") -> str:
    try:
        parsed = _parse_browser_command(args)
    except ValueError as exc:
        return str(exc)

    session = _get_or_create_session(user_id)
    try:
        if parsed.action == "open":
            return session.open_url(parsed.value)
        if parsed.action == "search":
            return session.search(parsed.value)
        if parsed.action == "click":
            return session.click(parsed.value)
        if parsed.action == "type":
            return session.type_text(parsed.value)
        if parsed.action == "screenshot":
            return session.screenshot()
        if parsed.action == "close":
            result = session.close()
            _drop_session(user_id)
            return result
        return "Tarayici komutu anlasilamadi."
    except RuntimeError as exc:
        if parsed.action == "close":
            _drop_session(user_id)
        return f"Tarayici hatasi: {exc}"
    except Exception as exc:
        return f"Tarayici hatasi: {exc}"
