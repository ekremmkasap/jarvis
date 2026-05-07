from __future__ import annotations

import os
import shlex
from dataclasses import dataclass
from pathlib import Path

import paramiko

from env_utils import get_int_env, load_env_files


ROOT = Path(__file__).resolve().parent
load_env_files(ROOT / ".env", ROOT / "server" / ".env")


@dataclass(frozen=True)
class RemoteConfig:
    host: str
    user: str
    password: str
    sudo_password: str
    base_dir: str
    bridge_path: str
    service_name: str
    state_dir: str
    startup_log: str
    jarvis_log: str
    bridge_port: int
    printify_local_token_path: Path
    shopify_client_id: str
    shopify_client_secret: str
    shopify_shop: str
    shopify_redirect_uri: str
    shopify_scopes: str


def load_remote_config() -> RemoteConfig:
    host = os.environ.get("JARVIS_REMOTE_HOST", "").strip()
    user = os.environ.get("JARVIS_REMOTE_USER", "").strip()
    password = os.environ.get("JARVIS_REMOTE_PASSWORD", "").strip()
    sudo_password = os.environ.get("JARVIS_REMOTE_SUDO_PASSWORD", password).strip()
    base_dir = os.environ.get("JARVIS_REMOTE_BASE", "/opt/jarvis").strip() or "/opt/jarvis"
    bridge_path = os.environ.get(
        "JARVIS_REMOTE_BRIDGE_PATH",
        f"{base_dir}/openclaw/bridge.py",
    ).strip()
    service_name = os.environ.get("JARVIS_REMOTE_SERVICE", "jarvis.service").strip() or "jarvis.service"
    state_dir = os.environ.get("JARVIS_REMOTE_STATE_DIR", f"/home/{user}/.jarvis").strip()
    startup_log = os.environ.get("JARVIS_REMOTE_STARTUP_LOG", f"{state_dir}/startup.log").strip()
    jarvis_log = os.environ.get("JARVIS_REMOTE_LOG", f"{state_dir}/jarvis.log").strip()
    printify_local_token_path = Path(
        os.environ.get(
            "PRINTIFY_LOCAL_TOKEN_PATH",
            str(ROOT / "printify_token.txt.txt"),
        )
    )
    return RemoteConfig(
        host=host,
        user=user,
        password=password,
        sudo_password=sudo_password,
        base_dir=base_dir,
        bridge_path=bridge_path,
        service_name=service_name,
        state_dir=state_dir,
        startup_log=startup_log,
        jarvis_log=jarvis_log,
        bridge_port=get_int_env("JARVIS_REMOTE_BRIDGE_PORT", 8080),
        printify_local_token_path=printify_local_token_path,
        shopify_client_id=os.environ.get("SHOPIFY_APP_CLIENT_ID", "").strip(),
        shopify_client_secret=os.environ.get("SHOPIFY_APP_CLIENT_SECRET", "").strip(),
        shopify_shop=os.environ.get("SHOPIFY_APP_SHOP", "").strip(),
        shopify_redirect_uri=os.environ.get("SHOPIFY_APP_REDIRECT_URI", "").strip(),
        shopify_scopes=os.environ.get(
            "SHOPIFY_APP_SCOPES",
            "read_products,read_inventory,read_orders,read_price_rules",
        ).strip(),
    )


def require_remote_config(config: RemoteConfig | None = None) -> RemoteConfig:
    config = config or load_remote_config()
    missing: list[str] = []
    if not config.host:
        missing.append("JARVIS_REMOTE_HOST")
    if not config.user:
        missing.append("JARVIS_REMOTE_USER")
    if not config.password:
        missing.append("JARVIS_REMOTE_PASSWORD")
    if missing:
        raise RuntimeError(
            "Missing remote config: " + ", ".join(missing) + ". Fill them in .env first."
        )
    return config


def build_ssh_client(
    config: RemoteConfig | None = None,
    timeout: int = 10,
) -> paramiko.SSHClient:
    config = require_remote_config(config)
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=config.host,
        username=config.user,
        password=config.password,
        timeout=timeout,
    )
    return client


def build_transport(config: RemoteConfig | None = None) -> paramiko.Transport:
    config = require_remote_config(config)
    transport = paramiko.Transport((config.host, 22))
    transport.connect(username=config.user, password=config.password)
    return transport


def sudo_wrap(command: str, config: RemoteConfig | None = None) -> str:
    config = require_remote_config(config)
    return f"echo {shlex.quote(config.sudo_password)} | sudo -S {command}"
