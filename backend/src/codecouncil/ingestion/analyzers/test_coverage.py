"""Test coverage analyzer — measure test/source ratio and parse coverage reports."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from codecouncil.models.repo import FileInfo, TestCoverage

# Patterns that identify test files
_TEST_PATTERNS = [
    "test_*.py",
    "*_test.py",
    "*_test.go",
    "*.test.ts",
    "*.spec.ts",
    "*.test.js",
    "*.spec.js",
    "*.test.tsx",
    "*.spec.tsx",
    "*Test.java",
    "*Spec.java",
    "*_spec.rb",
]


async def analyze_test_coverage(
    repo_path: str,
    file_tree: list[FileInfo],
) -> TestCoverage:
    """Analyze test coverage.

    Computes ratio of test files to source files, and optionally parses
    a .coverage (Python, sqlite3) or lcov.info file if present.
    """
    source_extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb"}

    test_files: set[str] = set()
    source_files: set[str] = set()

    for fi in file_tree:
        path = fi.path
        name = Path(path).name
        ext = Path(path).suffix

        if ext not in source_extensions:
            continue

        if _is_test_file(path, name):
            test_files.add(path)
        else:
            source_files.add(path)

    ratio = len(test_files) / max(len(source_files), 1)
    coverage_pct = _parse_coverage(repo_path)

    return TestCoverage(
        test_file_count=len(test_files),
        source_file_count=len(source_files),
        ratio=ratio,
        coverage_percentage=coverage_pct,
    )


def _is_test_file(path: str, name: str) -> bool:
    from fnmatch import fnmatch

    for pattern in _TEST_PATTERNS:
        if fnmatch(name, pattern):
            return True
    # Also match paths containing /test/ or /tests/ or /spec/
    lower = path.lower().replace("\\", "/")
    for segment in ("/test/", "/tests/", "/spec/", "/specs/"):
        if segment in lower:
            return True
    return False


def _parse_coverage(repo_path: str) -> float | None:
    root = Path(repo_path)

    # Python .coverage (SQLite)
    coverage_db = root / ".coverage"
    if coverage_db.exists():
        try:
            conn = sqlite3.connect(str(coverage_db))
            cur = conn.cursor()
            # .coverage schema: lines table with file_id, numbits columns
            # arc table for branch coverage; simplest heuristic uses meta table
            cur.execute(
                "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='line_bits'"
            )
            if cur.fetchone()[0]:
                cur.execute(
                    "SELECT SUM(length(numbits)) FROM line_bits"
                )
            conn.close()
        except Exception:
            pass

    # lcov.info
    lcov = root / "lcov.info"
    if lcov.exists():
        try:
            lines_found = 0
            lines_hit = 0
            for line in lcov.read_text().splitlines():
                if line.startswith("LF:"):
                    lines_found += int(line[3:])
                elif line.startswith("LH:"):
                    lines_hit += int(line[3:])
            if lines_found > 0:
                return round(lines_hit / lines_found * 100, 2)
        except Exception:
            pass

    return None
