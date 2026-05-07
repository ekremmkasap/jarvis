"""Tests for external_agent_skill."""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

MOCK_CONFIGS = [
    {
        "name": "crewai",
        "install_check": "crewai",
        "repo_path": "nonexistent/crewAI",
        "entry_command": ["python", "-m", "crewai", "run"],
        "bridge_command": "/crewai",
        "description": "CrewAI"
    },
    {
        "name": "openhands",
        "install_check": "openhands",
        "repo_path": "nonexistent/OpenHands",
        "entry_command": ["python", "-m", "openhands"],
        "bridge_command": "/openhands",
        "description": "OpenHands"
    }
]


@patch("server.skills.external_agent_skill.load_agent_configs", return_value=MOCK_CONFIGS)
@patch("server.skills.external_agent_skill.shutil.which")
def test_check_installed_found(mock_which, mock_configs):
    from server.skills.external_agent_skill import check_framework_installed
    mock_which.return_value = "/usr/bin/crewai"
    result = check_framework_installed("crewai")
    assert result["installed"] is True


@patch("server.skills.external_agent_skill.load_agent_configs", return_value=MOCK_CONFIGS)
@patch("server.skills.external_agent_skill.shutil.which")
def test_check_not_installed_returns_install_msg(mock_which, mock_configs):
    from server.skills.external_agent_skill import check_framework_installed
    mock_which.return_value = None
    result = check_framework_installed("crewai")
    assert result["installed"] is False
    assert "pip install" in result["message"] or "kurulu degil" in result["message"]


@patch("server.skills.external_agent_skill.load_agent_configs", return_value=MOCK_CONFIGS)
def test_check_unknown_agent(mock_configs):
    from server.skills.external_agent_skill import check_framework_installed
    result = check_framework_installed("unknownagent")
    assert result["installed"] is False


@patch("server.skills.external_agent_skill.load_agent_configs", return_value=MOCK_CONFIGS)
@patch("server.skills.external_agent_skill.check_framework_installed")
@patch("server.skills.external_agent_skill.subprocess.run")
def test_run_agent_task_success(mock_run, mock_check, mock_configs):
    from server.skills.external_agent_skill import run_agent_task
    mock_check.return_value = {"installed": True, "message": "OK"}
    mock_run.return_value = MagicMock(returncode=0, stdout="Task completed", stderr="")
    result = run_agent_task("crewai", "test task")
    assert result["ok"] is True
    assert "completed" in result["output"]


@patch("server.skills.external_agent_skill.load_agent_configs", return_value=MOCK_CONFIGS)
@patch("server.skills.external_agent_skill.check_framework_installed")
def test_run_agent_task_not_installed(mock_check, mock_configs):
    from server.skills.external_agent_skill import run_agent_task
    mock_check.return_value = {"installed": False, "message": "pip install crewai"}
    result = run_agent_task("crewai", "do something")
    assert result["ok"] is False
    assert "pip install" in result["output"] or "kurulu" in result["output"]


@patch("server.skills.external_agent_skill.load_agent_configs", return_value=MOCK_CONFIGS)
@patch("server.skills.external_agent_skill.check_framework_installed")
@patch("server.skills.external_agent_skill.subprocess.run")
def test_run_agent_task_timeout(mock_run, mock_check, mock_configs):
    import subprocess
    from server.skills.external_agent_skill import run_agent_task
    mock_check.return_value = {"installed": True, "message": "OK"}
    mock_run.side_effect = subprocess.TimeoutExpired(cmd="python", timeout=60)
    result = run_agent_task("crewai", "heavy task", timeout_seconds=60)
    assert result["ok"] is False
    assert result["error"] == "timeout"


@patch("server.skills.external_agent_skill.load_agent_configs", return_value=MOCK_CONFIGS)
@patch("server.skills.external_agent_skill.shutil.which")
def test_get_agent_status(mock_which, mock_configs):
    from server.skills.external_agent_skill import get_agent_status
    mock_which.return_value = None
    result = get_agent_status("crewai")
    assert result["name"] == "crewai"
    assert "installed" in result
    assert "bridge_command" in result
