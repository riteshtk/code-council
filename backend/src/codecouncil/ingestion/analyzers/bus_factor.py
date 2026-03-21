"""Bus factor analyzer — identify modules/files with dangerously few active authors."""
from __future__ import annotations

from collections import Counter

from codecouncil.models.repo import BusFactorReport


async def analyze_bus_factor(
    per_file_authors: dict[str, list[str]],
    min_threshold: int = 2,
) -> BusFactorReport:
    """Identify files and modules (directories) whose bus factor < *min_threshold*.

    A file's "significant author" is one who contributed > 10% of that file's
    commits.  The bus factor of an entry is the number of distinct significant
    authors.

    Analysis is performed at two levels:
    1. Per-file — flags individual files with too few authors.
    2. Per-directory (module) — aggregates authors across files in the same
       directory and flags the directory if its combined author set is too small.

    Both levels are included in ``flagged_modules`` so callers can use either.
    """
    flagged: list[dict] = []

    # Per-file bus factor
    module_authors: dict[str, set[str]] = {}

    for file_path, authors in per_file_authors.items():
        counts = Counter(authors)
        total = len(authors)
        significant = {a for a, n in counts.items() if total > 0 and n / total > 0.10}

        # File-level entry
        if len(significant) < min_threshold:
            flagged.append(
                {
                    "module": file_path,
                    "bus_factor": len(significant),
                    "authors": sorted(significant),
                    "level": "file",
                }
            )

        # Accumulate for directory-level
        directory = _dir_of(file_path)
        module_authors.setdefault(directory, set()).update(significant)

    # Directory-level entries (only add if not already present as file-level)
    seen_dirs = {item["module"] for item in flagged if item.get("level") == "directory"}
    for directory, authors in module_authors.items():
        if directory in seen_dirs:
            continue
        if len(authors) < min_threshold:
            flagged.append(
                {
                    "module": directory,
                    "bus_factor": len(authors),
                    "authors": sorted(authors),
                    "level": "directory",
                }
            )

    return BusFactorReport(
        flagged_modules=flagged,
        min_authors_threshold=min_threshold,
    )


def _dir_of(file_path: str) -> str:
    """Return the immediate parent directory, or the file path for top-level files."""
    parts = file_path.replace("\\", "/").split("/")
    return "/".join(parts[:-1]) if len(parts) > 1 else file_path
