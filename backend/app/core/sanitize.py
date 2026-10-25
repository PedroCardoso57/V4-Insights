"""Remoção de segredos de mensagens de erro e logs."""

from __future__ import annotations

import re

_PATTERNS = [
    (
        re.compile(
            r"(access_token|refresh_token|client_secret|developer-token|id_token|"
            r"fb_exchange_token)([\"']?\s*[:=]\s*[\"']?)[^\s&\"',}]+",
            re.I,
        ),
        r"\1\2***",
    ),
    (re.compile(r"(\bcode=)[A-Za-z0-9/_\-.]{20,}"), r"\1***"),
    (re.compile(r"(Bearer\s+)[A-Za-z0-9._\-~+/]+=*", re.I), r"\1***"),
    (re.compile(r"\bEA[A-Za-z0-9]{20,}\b"), "***"),  # tokens Meta
    (re.compile(r"\bya29\.[A-Za-z0-9._\-]+"), "***"),  # tokens Google
    (re.compile(r"\b1//[A-Za-z0-9._\-]+"), "***"),  # refresh tokens Google
]


def sanitize(message: str, max_len: int = 1000) -> str:
    out = message
    for pattern, repl in _PATTERNS:
        out = pattern.sub(repl, out)
    return out[:max_len]
