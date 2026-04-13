"""
Jarvis External Agent Framework Skill
CrewAI ve OpenHands framework'lerini subprocess ile calistirir
config/external_agents.yml'den konfigurasyon okur
"""
import shutil
import subprocess
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

AGENTS_CONFIG_PATH = Path("config/external_agents.yml")


def load_agent_configs() -> list:
    """config/external_agents.yml'den agent tanimlarini yukler."""
    try:
        import yaml
        cfg = yaml.safe_load(AGENTS_CONFIG_PATH.read_text(encoding="utf-8"))
        return cfg.get("agents", [])
    except ImportError:
        # yaml not available, try basic parse
        logger.warning("PyYAML yuklu degil, agent configs bos donuyor")
        return []
    except Exception as e:
        logger.warning(f"Agent config yuklenemedi: {e}")
        return []


def _get_agent_config(agent_name: str) -> Optional[dict]:
    for cfg in load_agent_configs():
        if cfg.get("name") == agent_name:
            return cfg
    return None


def check_framework_installed(agent_name: str) -> dict:
    """
    Framework'un CLI'inin yuklu olup olmadigini kontrol eder.
    shutil.which() kullanir - real subprocess degil.
    """
    cfg = _get_agent_config(agent_name)
    if not cfg:
        return {"installed": False, "message": f"{agent_name} konfigurasyonda bulunamadi"}
    install_check = cfg.get("install_check", agent_name)
    found = shutil.which(install_check)
    if found:
        return {"installed": True, "message": f"{agent_name} kurulu: {found}"}
    repo_path = Path(cfg.get("repo_path", ""))
    if repo_path.exists():
        return {
            "installed": True,
            "message": f"{agent_name} repo bulundu: {repo_path}",
            "via": "repo"
        }
    return {
        "installed": False,
        "message": (
            f"{agent_name} kurulu degil. Kurulum: "
            f"pip install {install_check}"
        )
    }


def run_agent_task(agent_name: str, task: str, timeout_seconds: int = 60) -> dict:
    """
    Framework'u subprocess ile calistirir.
    Kurulu degilse Turkce kurulum mesaji doner.
    Hicbir exception disariya sipmaz.
    """
    check = check_framework_installed(agent_name)
    if not check.get("installed"):
        return {"ok": False, "output": check["message"], "error": None}

    cfg = _get_agent_config(agent_name)
    if not cfg:
        return {"ok": False, "output": f"{agent_name} konfigurasyonu bulunamadi", "error": None}

    cmd = list(cfg.get("entry_command", [])) + [task]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        output = (result.stdout or result.stderr or "Cikti yok")[:800]
        return {"ok": result.returncode == 0, "output": output, "error": None}
    except subprocess.TimeoutExpired:
        return {"ok": False, "output": f"Zaman asimi ({timeout_seconds}s) — gorev cok uzun surdu", "error": "timeout"}
    except FileNotFoundError:
        return {"ok": False, "output": f"{agent_name} calistiirilamadi — PATH'e ekli mi?", "error": "not_found"}
    except Exception as e:
        logger.error(f"run_agent_task hatasi ({agent_name}): {e}")
        return {"ok": False, "output": str(e)[:200], "error": str(type(e).__name__)}


def get_agent_status(agent_name: str) -> dict:
    """Framework kurulum + repo durumu."""
    cfg = _get_agent_config(agent_name)
    if not cfg:
        return {"name": agent_name, "installed": False, "repo_path_exists": False,
                "bridge_command": f"/{agent_name}", "error": "konfigurasyon yok"}
    check = check_framework_installed(agent_name)
    repo_exists = Path(cfg.get("repo_path", "")).exists()
    return {
        "name": agent_name,
        "installed": check["installed"],
        "repo_path_exists": repo_exists,
        "repo_path": cfg.get("repo_path"),
        "bridge_command": cfg.get("bridge_command"),
        "message": check["message"],
    }
