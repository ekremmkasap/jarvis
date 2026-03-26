from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from env_utils import get_int_env, load_env_files


def _get_bool_env(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class RuntimeConfig:
    telegram_token: str
    authorized_chat_id: int
    ollama_url: str
    web_port: int
    request_timeout: int
    log_file: str
    memory_file: str
    runtime_label: str
    platform_label: str
    enable_telegram: bool
    donor_root: Path | None
    data_dir: Path

    def as_dict(self) -> dict[str, object]:
        return {
            "telegram_token": self.telegram_token,
            "authorized_chat_id": self.authorized_chat_id,
            "ollama_url": self.ollama_url,
            "web_port": self.web_port,
            "request_timeout": self.request_timeout,
            "log_file": self.log_file,
            "memory_file": self.memory_file,
            "runtime_label": self.runtime_label,
            "platform_label": self.platform_label,
            "enable_telegram": self.enable_telegram,
        }


def load_runtime_config(root_dir: Path, base_dir: Path) -> RuntimeConfig:
    load_env_files(root_dir / ".env", base_dir / ".env")
    try:
        from dotenv import load_dotenv

        load_dotenv(root_dir / ".env")
        load_dotenv(base_dir / ".env")
    except ImportError:
        pass

    data_dir = base_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    log_file = os.environ.get("JARVIS_LOG_FILE", str(data_dir / "jarvis.log"))
    memory_file = os.environ.get("JARVIS_MEMORY_FILE", str(data_dir / "memory.json"))
    Path(log_file).parent.mkdir(parents=True, exist_ok=True)
    Path(memory_file).parent.mkdir(parents=True, exist_ok=True)

    telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    enable_telegram = _get_bool_env(
        "JARVIS_ENABLE_TELEGRAM",
        default=bool(telegram_token),
    )

    donor_root_raw = os.environ.get("JARVIS_DONOR_ROOT", r"C:\pinokio\api\ekrem\app")
    donor_root = Path(donor_root_raw) if donor_root_raw else None

    return RuntimeConfig(
        telegram_token=telegram_token,
        authorized_chat_id=get_int_env("TELEGRAM_CHAT_ID", 0),
        ollama_url=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"),
        web_port=get_int_env("JARVIS_WEB_PORT", 8081),
        request_timeout=get_int_env("JARVIS_REQUEST_TIMEOUT", 300),
        log_file=log_file,
        memory_file=memory_file,
        runtime_label=os.environ.get("JARVIS_RUNTIME_LABEL", "Standalone Service"),
        platform_label=os.environ.get("JARVIS_PLATFORM_LABEL", "Windows/Standalone"),
        enable_telegram=enable_telegram,
        donor_root=donor_root,
        data_dir=data_dir,
    )


def validate_runtime_config(config: RuntimeConfig) -> None:
    errors: list[str] = []

    if config.web_port <= 0:
        errors.append("JARVIS_WEB_PORT must be a positive integer.")

    if config.enable_telegram:
        if not config.telegram_token:
            errors.append("TELEGRAM_BOT_TOKEN is required when JARVIS_ENABLE_TELEGRAM=1.")
        if not config.authorized_chat_id:
            errors.append("TELEGRAM_CHAT_ID is required when JARVIS_ENABLE_TELEGRAM=1.")

    if errors:
        joined = "\n- ".join(errors)
        raise RuntimeError(f"Runtime config validation failed:\n- {joined}")
