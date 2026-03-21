"""File churn analyzer — identify hot files within a time window."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from codecouncil.models.repo import ChurnReport, Commit


async def analyze_churn(commits: list[Commit], window_days: int = 90) -> ChurnReport:
    """Calculate per-file churn rate within *window_days*.

    Churn rate for a file = (commits touching file) / (total commits in window).
    Files above 50% churn are flagged.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=window_days)

    windowed = [c for c in commits if _as_utc(c.date) >= cutoff]
    total = len(windowed)

    file_counts: dict[str, int] = {}
    for commit in windowed:
        for f in commit.files_changed:
            file_counts[f] = file_counts.get(f, 0) + 1

    flagged: list[str] = []
    if total > 0:
        for path, count in file_counts.items():
            if count / total > 0.5:
                flagged.append(path)

    return ChurnReport(
        window_days=window_days,
        total_commits=total,
        flagged_files=flagged,
    )


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)
