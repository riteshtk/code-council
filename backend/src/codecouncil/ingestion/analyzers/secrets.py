"""Secret detection — regex-based scan with SHA-256 hashing of matches."""
from __future__ import annotations

import hashlib
import re

from codecouncil.models.repo import SecretFinding

PATTERNS: dict[str, str] = {
    "aws_access_key": r"AKIA[0-9A-Z]{16}",
    "generic_api_key": r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"][A-Za-z0-9]{20,}['\"]",
    "password_assignment": r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
    "bearer_token": r"(?i)bearer\s+[A-Za-z0-9\-._~+/]+=*",
    "private_key": r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----",
    "github_token": r"gh[ps]_[A-Za-z0-9_]{36,}",
}

_COMPILED: dict[str, re.Pattern] = {
    name: re.compile(pattern) for name, pattern in PATTERNS.items()
}


async def detect_secrets(file_path: str, content: str) -> list[SecretFinding]:
    """Scan *content* for hardcoded secrets.

    Each match is SHA-256 hashed — raw values are never stored.
    Returns a list of SecretFinding objects.
    """
    findings: list[SecretFinding] = []
    lines = content.splitlines()

    for pattern_name, compiled in _COMPILED.items():
        for match in compiled.finditer(content):
            # Compute line number from character offset
            line_number = content.count("\n", 0, match.start()) + 1
            raw_match = match.group(0)
            hashed = hashlib.sha256(raw_match.encode()).hexdigest()
            findings.append(
                SecretFinding(
                    file_path=file_path,
                    line_number=line_number,
                    pattern_type=pattern_name,
                    hash=hashed,
                )
            )

    return findings
