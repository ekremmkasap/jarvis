"""
JARVIS Self-Debug Agent
Automatic error detection, logging, and recovery system.
"""

import json
import os
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


ROOT_DIR = Path(__file__).resolve().parents[2]
HEALTH_LOG = ROOT_DIR / "server" / "logs" / "jarvis_health.log"
KNOWN_ISSUES_DB = ROOT_DIR / "server" / "agent_workspace" / "known_issues.json"


class KnownIssue:
    """Known issue with automatic recovery strategy"""
    def __init__(self, error_pattern: str, recovery_action: str, fallback_mode: str = None):
        self.error_pattern = error_pattern
        self.recovery_action = recovery_action
        self.fallback_mode = fallback_mode


# Known issues database
KNOWN_ISSUES = [
    KnownIssue(
        error_pattern="No such file or directory",
        recovery_action="Check if file exists, create if needed",
        fallback_mode="skip_operation"
    ),
    KnownIssue(
        error_pattern="Connection refused",
        recovery_action="Retry with exponential backoff",
        fallback_mode="use_cached_data"
    ),
    KnownIssue(
        error_pattern="timeout",
        recovery_action="Increase timeout and retry",
        fallback_mode="skip_operation"
    ),
    KnownIssue(
        error_pattern="rate limit",
        recovery_action="Wait and retry with fallback model",
        fallback_mode="use_local_model"
    ),
    KnownIssue(
        error_pattern="OSError.*WinError",
        recovery_action="Retry with error suppression",
        fallback_mode="continue_without_resource"
    ),
    KnownIssue(
        error_pattern="PICOVOICE_ACCESS_KEY",
        recovery_action="Fall back to continuous listen mode",
        fallback_mode="continuous_listen"
    ),
    KnownIssue(
        error_pattern="pyaudio.*PortAudio",
        recovery_action="Fall back to text mode",
        fallback_mode="text_mode"
    ),
]


def _log_health_event(level: str, component: str, message: str, data: dict = None):
    """Log health event to jarvis_health.log"""
    HEALTH_LOG.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "time": datetime.now().isoformat(),
        "level": level,
        "component": component,
        "message": message,
        "data": data or {}
    }
    with open(HEALTH_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _find_known_issue(error_msg: str) -> Optional[KnownIssue]:
    """Find matching known issue by error pattern"""
    import re
    for issue in KNOWN_ISSUES:
        if re.search(issue.error_pattern, error_msg, re.IGNORECASE):
            return issue
    return None


def safe_execute(func: Callable, *args, fallback_result=None, component="unknown", **kwargs) -> Any:
    """
    Execute function with automatic error handling and recovery.

    Args:
        func: Function to execute
        *args: Function arguments
        fallback_result: Value to return on failure
        component: Component name for logging
        **kwargs: Function keyword arguments

    Returns:
        Function result or fallback_result on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        error_msg = str(e)
        error_type = type(e).__name__

        # Log the error
        _log_health_event(
            level="ERROR",
            component=component,
            message=f"{error_type}: {error_msg}",
            data={
                "function": func.__name__,
                "args": str(args)[:200],
                "kwargs": str(kwargs)[:200],
                "traceback": traceback.format_exc()[:1000]
            }
        )

        # Check for known issues
        known_issue = _find_known_issue(error_msg)
        if known_issue:
            _log_health_event(
                level="INFO",
                component=component,
                message=f"Known issue detected: {known_issue.error_pattern}",
                data={
                    "recovery_action": known_issue.recovery_action,
                    "fallback_mode": known_issue.fallback_mode
                }
            )
            print(f"[DEBUG] Known issue: {known_issue.recovery_action}")

        return fallback_result


def health_check() -> Dict[str, Any]:
    """
    Perform comprehensive health check on JARVIS systems.

    Returns:
        Health status dictionary
    """
    status = {
        "timestamp": datetime.now().isoformat(),
        "overall_status": "healthy",
        "components": {},
        "issues": []
    }

    # Check 1: File system access
    try:
        test_file = ROOT_DIR / "server" / "agent_workspace" / ".health_check"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("health_check", encoding="utf-8")
        test_file.unlink()
        status["components"]["filesystem"] = "healthy"
    except Exception as e:
        status["components"]["filesystem"] = "unhealthy"
        status["issues"].append(f"Filesystem error: {e}")
        status["overall_status"] = "degraded"

    # Check 2: Ollama availability
    try:
        import urllib.request
        ollama_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
        req = urllib.request.Request(f"{ollama_url}/api/tags", method="GET")
        urllib.request.urlopen(req, timeout=2)
        status["components"]["ollama"] = "healthy"
    except Exception as e:
        status["components"]["ollama"] = "unavailable"
        status["issues"].append(f"Ollama unavailable: {e}")

    # Check 3: Voice system (Piper TTS)
    try:
        piper_model = Path(r"C:\Users\sergen\AppData\Local\piper-models\tr_TR-dfki-medium.onnx")
        if piper_model.exists():
            status["components"]["tts"] = "healthy"
        else:
            status["components"]["tts"] = "model_missing"
            status["issues"].append("Piper TTS model not found")
    except Exception as e:
        status["components"]["tts"] = "error"
        status["issues"].append(f"TTS check error: {e}")

    # Check 4: Microphone access
    try:
        import speech_recognition as sr
        recognizer = sr.Recognizer()
        mic = sr.Microphone(device_index=1)
        with mic as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
        status["components"]["microphone"] = "healthy"
    except Exception as e:
        status["components"]["microphone"] = "unavailable"
        status["issues"].append(f"Microphone error: {e}")
        status["overall_status"] = "degraded"

    # Check 5: Wake word system (pvporcupine)
    try:
        import pvporcupine
        access_key = os.environ.get("PICOVOICE_ACCESS_KEY", "")
        if access_key:
            status["components"]["wake_word"] = "healthy"
        else:
            status["components"]["wake_word"] = "key_missing"
            status["issues"].append("PICOVOICE_ACCESS_KEY not configured")
    except ImportError:
        status["components"]["wake_word"] = "not_installed"
        status["issues"].append("pvporcupine not installed")
    except Exception as e:
        status["components"]["wake_word"] = "error"
        status["issues"].append(f"Wake word error: {e}")

    # Check 6: Collaboration bridge
    try:
        bridge_state = ROOT_DIR / "server" / "agent_workspace" / "exchange" / "bridge_state.json"
        if bridge_state.exists():
            status["components"]["collaboration_bridge"] = "healthy"
        else:
            status["components"]["collaboration_bridge"] = "not_initialized"
    except Exception as e:
        status["components"]["collaboration_bridge"] = "error"
        status["issues"].append(f"Bridge error: {e}")

    # Check 7: Recent health log errors
    try:
        if HEALTH_LOG.exists():
            recent_errors = []
            with open(HEALTH_LOG, "r", encoding="utf-8") as f:
                lines = f.readlines()[-50:]  # Last 50 events
                for line in lines:
                    try:
                        event = json.loads(line)
                        if event.get("level") == "ERROR":
                            recent_errors.append({
                                "time": event["time"],
                                "component": event["component"],
                                "message": event["message"][:100]
                            })
                    except:
                        pass

            if recent_errors:
                status["components"]["health_log"] = "has_errors"
                status["recent_errors"] = recent_errors[-5:]  # Last 5 errors
            else:
                status["components"]["health_log"] = "clean"
    except Exception as e:
        status["components"]["health_log"] = "error"
        status["issues"].append(f"Health log check error: {e}")

    # Overall status determination
    unhealthy_components = sum(1 for v in status["components"].values()
                               if v in ["unhealthy", "unavailable", "error"])
    if unhealthy_components >= 3:
        status["overall_status"] = "critical"
    elif unhealthy_components >= 1:
        status["overall_status"] = "degraded"

    _log_health_event(
        level="INFO",
        component="health_check",
        message=f"Health check completed: {status['overall_status']}",
        data=status
    )

    return status


def get_health_report() -> str:
    """
    Get human-readable health report.

    Returns:
        Formatted health report string
    """
    status = health_check()

    report = []
    report.append("\n" + "=" * 60)
    report.append("  JARVIS HEALTH CHECK REPORT")
    report.append("=" * 60)
    report.append(f"Time: {status['timestamp']}")
    report.append(f"Overall Status: {status['overall_status'].upper()}")
    report.append("")
    report.append("Component Status:")
    report.append("-" * 60)

    for component, state in status["components"].items():
        icon = "✓" if state == "healthy" else "✗" if state in ["unhealthy", "unavailable", "error"] else "⚠"
        report.append(f"  {icon} {component:20s}: {state}")

    if status["issues"]:
        report.append("")
        report.append("Issues Detected:")
        report.append("-" * 60)
        for i, issue in enumerate(status["issues"], 1):
            report.append(f"  {i}. {issue}")

    if status.get("recent_errors"):
        report.append("")
        report.append("Recent Errors:")
        report.append("-" * 60)
        for err in status["recent_errors"]:
            report.append(f"  [{err['time']}] {err['component']}: {err['message']}")

    report.append("=" * 60 + "\n")

    return "\n".join(report)


def auto_recover_voice_mode():
    """
    Automatic recovery for voice mode failures.
    Tries different fallback strategies.
    """
    _log_health_event(
        level="INFO",
        component="auto_recover",
        message="Attempting voice mode auto-recovery"
    )

    # Strategy 1: Try without wake word
    try:
        print("[DEBUG] Recovery: Trying continuous listen mode...")
        from hey_jarvis import run_continuous_listen_mode
        return safe_execute(
            run_continuous_listen_mode,
            component="voice_recovery",
            fallback_result=None
        )
    except Exception as e:
        _log_health_event(
            level="WARN",
            component="auto_recover",
            message=f"Continuous listen failed: {e}"
        )

    # Strategy 2: Fall back to text mode
    try:
        print("[DEBUG] Recovery: Falling back to text mode...")
        from hey_jarvis import run_text_loop
        return safe_execute(
            run_text_loop,
            component="voice_recovery",
            fallback_result=None
        )
    except Exception as e:
        _log_health_event(
            level="ERROR",
            component="auto_recover",
            message=f"Text mode fallback failed: {e}"
        )
        raise


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        print(get_health_report())
    else:
        # Quick test
        print("[Self-Debug Agent] Testing safe_execute...")

        def test_success():
            return "Success!"

        def test_failure():
            raise ValueError("Test error")

        result1 = safe_execute(test_success, component="test")
        print(f"Test 1 (success): {result1}")

        result2 = safe_execute(test_failure, fallback_result="Fallback", component="test")
        print(f"Test 2 (failure): {result2}")

        print("\n[Self-Debug Agent] Running health check...")
        print(get_health_report())
