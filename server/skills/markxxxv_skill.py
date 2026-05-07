"""
Mark-XXXV integration skill for Jarvis bridge.

Supported modes:
- auto   : try in-process module mode first, then HTTP if configured
- http   : send the request to a Mark-XXXV compatible HTTP endpoint
- module : import Mark-XXXV directly inside this process
"""

from __future__ import annotations

import importlib
import io
import json
import os
import subprocess
import sys
import threading
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_REPO_PATH = ROOT_DIR / "external-repos" / "Mark-XXXV"
DEFAULT_HTTP_PATH = "/command"
DEFAULT_TIMEOUT_SECONDS = 30
_RESPONSE_KEYS = ("result", "response", "reply", "message", "output", "text")
_SECRET_ENV_NAMES = (
    "MARKXXXV_API_KEY",
    "MARKXXXV_GEMINI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_API_KEY",
)


def _resolve_path(raw_path: str, default: Path | None = None) -> Path | None:
    value = (raw_path or "").strip()
    if not value:
        return default

    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = ROOT_DIR / candidate
    return candidate.resolve()


def _get_timeout_seconds() -> int:
    raw_value = os.environ.get("MARKXXXV_TIMEOUT_SECONDS", "").strip()
    if not raw_value:
        return DEFAULT_TIMEOUT_SECONDS

    try:
        return max(5, int(raw_value))
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS


def _get_config() -> dict[str, Any]:
    mode = os.environ.get("MARKXXXV_MODE", "auto").strip().lower() or "auto"
    if mode not in {"auto", "http", "module"}:
        mode = "auto"

    return {
        "mode": mode,
        "base_url": os.environ.get("MARKXXXV_BASE_URL", "").strip(),
        "http_path": os.environ.get("MARKXXXV_HTTP_PATH", DEFAULT_HTTP_PATH).strip() or DEFAULT_HTTP_PATH,
        "api_key": os.environ.get("MARKXXXV_API_KEY", "").strip(),
        "repo_path": _resolve_path(os.environ.get("MARKXXXV_REPO_PATH", ""), DEFAULT_REPO_PATH),
        "timeout_seconds": _get_timeout_seconds(),
    }


def _redact_sensitive_text(value: Any) -> str:
    text = str(value or "")
    for env_name in _SECRET_ENV_NAMES:
        secret = os.environ.get(env_name, "").strip()
        if secret:
            text = text.replace(secret, "***")
    return text


def _friendly_error(prefix: str, error: Exception | str) -> str:
    return f"{prefix}: {_redact_sensitive_text(error)}"


def _extract_response_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload.strip()

    if isinstance(payload, dict):
        for key in _RESPONSE_KEYS:
            value = payload.get(key)
            if value:
                return str(value).strip()
        return json.dumps(payload, ensure_ascii=False)

    if isinstance(payload, list):
        return "\n".join(str(item) for item in payload if item is not None).strip()

    return str(payload).strip()


def _build_http_url(base_url: str, http_path: str) -> str:
    base = base_url.rstrip("/")
    suffix = http_path if http_path.startswith("/") else f"/{http_path}"
    return f"{base}{suffix}"


def _run_http_mode(query: str, user_id: str, config: dict[str, Any]) -> str:
    if not config["base_url"]:
        raise ValueError("MARKXXXV_BASE_URL tanimli degil.")

    payload = json.dumps(
        {
            "goal": query,
            "command": query,
            "query": query,
            "user_id": user_id,
        }
    ).encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if config["api_key"]:
        headers["Authorization"] = f"Bearer {config['api_key']}"

    request = Request(
        _build_http_url(str(config["base_url"]), str(config["http_path"])),
        data=payload,
        headers=headers,
        method="POST",
    )

    try:
        with urlopen(request, timeout=int(config["timeout_seconds"])) as response:
            raw_text = response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        error_body = ""
        try:
            error_body = exc.read().decode("utf-8", errors="replace").strip()
        except Exception:
            error_body = ""
        detail = error_body or str(exc)
        raise RuntimeError(_friendly_error("Mark-XXXV HTTP hatasi", detail)) from exc
    except URLError as exc:
        raise RuntimeError(_friendly_error("Mark-XXXV servisine ulasilamadi", exc)) from exc

    try:
        payload_data = json.loads(raw_text)
    except json.JSONDecodeError:
        return raw_text.strip() or "Mark-XXXV bos yanit verdi."

    response_text = _extract_response_text(payload_data)
    return response_text or "Mark-XXXV bos yanit verdi."


def _ensure_markxxxv_repo(repo_path: Path | None) -> Path:
    if repo_path is None:
        raise FileNotFoundError("MARKXXXV_REPO_PATH tanimsiz.")
    if repo_path.exists():
        return repo_path

    repo_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        subprocess.run(
            [
                "git",
                "clone",
                "https://github.com/FatihMakes/Mark-XXXV",
                str(repo_path),
            ],
            check=True,
            capture_output=True,
            text=True,
            cwd=str(ROOT_DIR),
            timeout=180,
        )
    except Exception as exc:
        raise FileNotFoundError(f"Mark-XXXV repo klonlanamadi: {exc}") from exc

    if not repo_path.exists():
        raise FileNotFoundError(f"Mark-XXXV repo yolu bulunamadi: {repo_path}")
    return repo_path


def _ensure_markxxxv_api_key(repo_path: Path) -> None:
    key = (
        os.environ.get("MARKXXXV_GEMINI_API_KEY", "").strip()
        or os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_API_KEY", "").strip()
    )
    if not key:
        return

    config_dir = repo_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "api_keys.json"
    payload = {"gemini_api_key": key}

    try:
        if config_path.exists():
            current = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(current, dict) and current.get("gemini_api_key"):
                return
    except Exception:
        pass

    config_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _module_belongs_to_repo(module: Any, repo_path: Path) -> bool:
    repo_root = repo_path.resolve()
    candidate_paths: list[Path] = []

    module_file = getattr(module, "__file__", None)
    if module_file:
        try:
            candidate_paths.append(Path(module_file).resolve())
        except Exception:
            pass

    module_path = getattr(module, "__path__", None)
    if module_path:
        for item in list(module_path):
            try:
                candidate_paths.append(Path(item).resolve())
            except Exception:
                continue

    for candidate in candidate_paths:
        if candidate == repo_root or repo_root in candidate.parents:
            return True
    return False


def _purge_markxxxv_modules(repo_path: Path) -> None:
    for module_name, module in list(sys.modules.items()):
        if not (
            module_name == "agent"
            or module_name.startswith("agent.")
            or module_name == "actions"
            or module_name.startswith("actions.")
            or module_name == "memory"
            or module_name.startswith("memory.")
        ):
            continue

        if module is None or _module_belongs_to_repo(module, repo_path):
            sys.modules.pop(module_name, None)


def _invoke_markxxxv_executor(repo_path: Path, query: str) -> str:
    if str(repo_path) not in sys.path:
        sys.path.insert(0, str(repo_path))

    importlib.invalidate_caches()
    _purge_markxxxv_modules(repo_path)

    executor_module = importlib.import_module("agent.executor")
    executor_cls = getattr(executor_module, "AgentExecutor", None)
    if executor_cls is None:
        raise ImportError("agent.executor.AgentExecutor bulunamadi.")

    executor = executor_cls()
    if hasattr(executor, "run") and callable(executor.run):
        result = executor.run(query)
    elif hasattr(executor, "execute") and callable(executor.execute):
        result = executor.execute(query)
    else:
        raise ImportError("AgentExecutor run/execute metodu sunmuyor.")

    return _extract_response_text(result)


def _run_module_mode(query: str, config: dict[str, Any]) -> str:
    repo_path = _ensure_markxxxv_repo(config["repo_path"])
    _ensure_markxxxv_api_key(repo_path)

    result_box: dict[str, Any] = {}
    done = threading.Event()

    def _worker() -> None:
        stdout_buffer = io.StringIO()
        stderr_buffer = io.StringIO()
        try:
            with redirect_stdout(stdout_buffer), redirect_stderr(stderr_buffer):
                result_box["result"] = _invoke_markxxxv_executor(repo_path, query)
        except Exception as exc:
            result_box["error"] = exc
            result_box["stderr"] = stderr_buffer.getvalue()
        finally:
            result_box["stdout"] = stdout_buffer.getvalue()
            done.set()

    worker = threading.Thread(target=_worker, daemon=True, name="markxxxv-executor")
    worker.start()

    if not done.wait(timeout=int(config["timeout_seconds"])):
        raise TimeoutError(f"Mark-XXXV {config['timeout_seconds']} saniye icinde yanit vermedi.")

    if "error" in result_box:
        raise result_box["error"]

    response_text = _extract_response_text(result_box.get("result"))
    if not response_text:
        return "Mark-XXXV bos yanit verdi."
    return response_text


def _try_http_fallback(query: str, user_id: str, config: dict[str, Any], original_error: Exception) -> str:
    if not config["base_url"]:
        raise original_error
    return _run_http_mode(query, user_id, config)


def markxxxv_status() -> str:
    config = _get_config()
    repo_path = config["repo_path"]
    repo_status = "hazir" if repo_path and repo_path.exists() else "yok"
    http_status = config["base_url"] or "tanimli degil"
    api_key_status = "var" if config["api_key"] else "yok"

    return (
        "*Mark-XXXV Durumu*\n\n"
        f"- Mod: `{config['mode']}`\n"
        f"- Repo: `{repo_status}`\n"
        f"- Repo yolu: `{repo_path}`\n"
        f"- HTTP URL: `{http_status}`\n"
        f"- API key: `{api_key_status}`\n"
        f"- Timeout: `{config['timeout_seconds']} sn`"
    )


def handle_markxxxv(args: str, user_id: str = "") -> str:
    query = (args or "").strip()
    if not query:
        return "Kullanim: /markxxxv [gorev]"

    if query.lower() in {"status", "durum", "help", "yardim"}:
        return markxxxv_status()

    config = _get_config()
    mode = str(config["mode"])

    try:
        if mode == "http":
            return _run_http_mode(query, user_id, config)

        if mode == "module":
            try:
                return _run_module_mode(query, config)
            except (ImportError, ModuleNotFoundError) as exc:
                return _try_http_fallback(query, user_id, config, exc)

        try:
            return _run_module_mode(query, config)
        except (ImportError, ModuleNotFoundError) as exc:
            return _try_http_fallback(query, user_id, config, exc)
        except FileNotFoundError as exc:
            return _try_http_fallback(query, user_id, config, exc)
    except FileNotFoundError as exc:
        return _friendly_error("Mark-XXXV kurulumu eksik", exc)
    except TimeoutError as exc:
        return _friendly_error("Mark-XXXV zaman asimi", exc)
    except ModuleNotFoundError as exc:
        return _friendly_error("Mark-XXXV bagimliligi eksik", exc)
    except Exception as exc:
        return _friendly_error("Mark-XXXV hatasi", exc)


if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]).strip() or "status"
    print(handle_markxxxv(prompt))
