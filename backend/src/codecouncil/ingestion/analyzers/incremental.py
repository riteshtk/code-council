"""Incremental ingestion support — SHA-256 file hashing and diff detection."""
from __future__ import annotations

import hashlib
from pathlib import Path

from codecouncil.models.repo import FileInfo


async def compute_file_hashes(
    file_tree: list[FileInfo],
    repo_path: str,
) -> dict[str, str]:
    """Return a mapping of file path → SHA-256 hex digest."""
    hashes: dict[str, str] = {}
    root = Path(repo_path)

    for fi in file_tree:
        full_path = root / fi.path
        try:
            content = full_path.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            hashes[fi.path] = digest
        except Exception:
            continue

    return hashes


async def diff_against_previous(
    current_hashes: dict[str, str],
    previous_hashes: dict[str, str],
) -> list[str]:
    """Return file paths that are new or have changed content.

    - New files: present in *current_hashes* but not in *previous_hashes*.
    - Changed files: present in both but with different hash.
    - Deleted files are NOT included (the caller decides how to handle removals).
    """
    changed: list[str] = []
    for path, digest in current_hashes.items():
        if path not in previous_hashes or previous_hashes[path] != digest:
            changed.append(path)
    return changed
