from __future__ import annotations

import re

SECRET_PATTERNS = [
    re.compile(r'(?i)(authorization:\s*bearer\s+)([^\s"\'\',}]+)'),
    re.compile(r'(?i)(token=)([^\s&"\'\',}]+)'),
    re.compile(r'(?i)(api[_-]?key\s*[:=]\s*)([^\s"\'\',}]+)'),
    re.compile(r'(?i)(secret\s*[:=]\s*)([^\s"\'\',}]+)'),
]


def sanitize_text(text: str) -> str:
    sanitized = text
    for pattern in SECRET_PATTERNS:
        sanitized = pattern.sub(r'\1[REDACTED]', sanitized)
    return sanitized
