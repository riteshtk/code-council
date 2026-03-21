"""Git history analyzer — parse commits, classify sentiment, build author maps."""
from __future__ import annotations

from codecouncil.config.schema import IngestConfig
from codecouncil.models.repo import Commit

_NEGATIVE_KEYWORDS = {"fix", "bug", "hotfix", "urgent", "broken", "revert", "crash", "error"}
_POSITIVE_KEYWORDS = {"feat", "add", "improve", "enhance", "refactor", "optimise", "optimize"}


def _classify_sentiment(message: str) -> str:
    lower = message.lower()
    if any(kw in lower for kw in _NEGATIVE_KEYWORDS):
        return "negative"
    if any(kw in lower for kw in _POSITIVE_KEYWORDS):
        return "positive"
    return "neutral"


async def analyze_git_history(
    repo_path: str,
    config: IngestConfig,
) -> tuple[list[Commit], dict[str, list[str]]]:
    """Parse git log.

    Returns (commits, per_file_authors) where per_file_authors maps each file
    path to the list of author identifiers that committed to it (with repetition
    so the list length reflects commit count per author).
    """
    import git as gitpython

    try:
        repo = gitpython.Repo(repo_path)
    except gitpython.InvalidGitRepositoryError:
        return [], {}

    commits: list[Commit] = []
    per_file_authors: dict[str, list[str]] = {}

    for c in repo.iter_commits(max_count=config.git_log_limit):
        files_changed = list(c.stats.files.keys()) if c.stats else []
        author = str(c.author.email or c.author.name)
        commit = Commit(
            hash=c.hexsha,
            author=author,
            date=c.committed_datetime,
            message=c.message.strip(),
            files_changed=files_changed,
        )
        commits.append(commit)

        for f in files_changed:
            per_file_authors.setdefault(f, []).append(author)

    return commits, per_file_authors
