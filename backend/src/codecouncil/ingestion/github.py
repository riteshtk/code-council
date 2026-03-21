"""GitHub ingestion source — REST API + GitPython clone."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path

import httpx

from codecouncil.config.schema import IngestConfig
from codecouncil.ingestion.base import IngestionSource
from codecouncil.models.repo import FileInfo, RepoContext

_GITHUB_RE = re.compile(r"https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/\s]+)")


def _parse_github_url(url: str) -> tuple[str, str] | None:
    m = _GITHUB_RE.match(url)
    if not m:
        return None
    owner = m.group("owner")
    repo = m.group("repo").rstrip("/").removesuffix(".git")
    return owner, repo


class GitHubSource(IngestionSource):
    """Ingest a public or private GitHub repository."""

    def can_handle(self, url: str) -> bool:
        return bool(_parse_github_url(url))

    async def ingest(self, url: str, config: IngestConfig) -> RepoContext:
        parsed = _parse_github_url(url)
        if parsed is None:
            raise ValueError(f"Cannot parse GitHub URL: {url}")
        owner, repo_name = parsed

        headers: dict[str, str] = {"Accept": "application/vnd.github+json"}
        if config.github_token:
            headers["Authorization"] = f"Bearer {config.github_token}"

        file_tree: list[FileInfo] = []

        async with httpx.AsyncClient(headers=headers, timeout=30) as client:
            # Fetch repository tree via API (recursive)
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/HEAD",
                params={"recursive": "1"},
            )
            if resp.status_code == 200:
                data = resp.json()
                count = 0
                for item in data.get("tree", []):
                    if item.get("type") != "blob":
                        continue
                    path = item["path"]
                    # Filter by extension
                    ext = Path(path).suffix
                    if config.include_extensions and ext not in config.include_extensions:
                        continue
                    # Filter excluded paths
                    if any(ex in path for ex in config.exclude_paths):
                        continue
                    # Filter by size
                    size_kb = item.get("size", 0) / 1024
                    if size_kb > config.max_file_size_kb:
                        continue
                    file_tree.append(FileInfo(path=path, language=_ext_to_lang(ext)))
                    count += 1
                    if count >= config.max_files:
                        break

        # Clone the repo to get git history
        git_log: list = []
        try:
            import git as gitpython

            clone_url = url if url.endswith(".git") else url + ".git"
            if config.github_token:
                clone_url = clone_url.replace(
                    "https://", f"https://{config.github_token}@"
                )
            with tempfile.TemporaryDirectory() as tmpdir:
                repo = gitpython.Repo.clone_from(
                    clone_url, tmpdir, depth=config.git_log_limit
                )
                git_log = _build_git_log(repo, config.git_log_limit)
        except Exception:
            pass

        return RepoContext(
            repo_url=url,
            repo_name=repo_name,
            file_tree=file_tree,
            git_log=git_log,
        )


def _ext_to_lang(ext: str) -> str:
    mapping = {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
    }
    return mapping.get(ext, ext.lstrip("."))


def _build_git_log(repo, limit: int) -> list:
    from codecouncil.models.repo import Commit

    commits = []
    for c in repo.iter_commits(max_count=limit):
        files_changed = list(c.stats.files.keys()) if c.stats else []
        commits.append(
            Commit(
                hash=c.hexsha,
                author=str(c.author.email or c.author.name),
                date=c.committed_datetime,
                message=c.message.strip(),
                files_changed=files_changed,
            )
        )
    return commits
