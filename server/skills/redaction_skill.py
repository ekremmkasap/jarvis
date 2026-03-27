"""
Jarvis - Secret Redaction Skill
"""
import re

SECRET_PATTERNS = [
    (r"sk-[A-Za-z0-9]{20,}",                                    "sk-***REDACTED***"),
    (r"AIza[A-Za-z0-9\-_]{30,}",                                "AIza***REDACTED***"),
    (r"Bearer\s+[A-Za-z0-9\-_\.]{20,}",                         "Bearer ***REDACTED***"),
    (r"ghp_[A-Za-z0-9]{30,}",                                   "ghp_***REDACTED***"),
    (r"xoxb-[A-Za-z0-9\-]{30,}",                                "xoxb-***REDACTED***"),
    (r"(?i)(password|passwd|secret|token|api[_\-]?key)\s*[:=]\s*\S+", r"\1=***REDACTED***"),
]

def _mask_match(match):
    return "***REDACTED***"

def redact_sensitive_text(text: str) -> str:
    if not isinstance(text, str):
        return text
    for pattern, replacement in SECRET_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text
