"""GitLab ingestion source — API v4 + GitPython clone."""
from __future__ import annotations

import re
import tempfile
from pathlib import Path
from urllib.parse import quote

import httpx

from codecouncil.config.schema import IngestConfig
from codecouncil.ingestion.base import IngestionSource
from codecouncil.models.repo import FileInfo, RepoContext

_GITLAB_RE = re.compile(r"https?://gitlab\.com/(?P<path>[^?\s]+?)(?:\.git)?$")


def _parse_gitlab_url(url: str) -> str | None:
    m = _GITLAB_RE.match(url)
    if not m:
        return None
    return m.group("path").rstrip("/")


class GitLabSource(IngestionSource):
    """Ingest a GitLab repository."""

    def can_handle(self, url: str) -> bool:
        return bool(_parse_gitlab_url(url))

    async def ingest(self, url: str, config: IngestConfig) -> RepoContext:
        project_path = _parse_gitlab_url(url)
        if project_path is None:
            raise ValueError(f"Cannot parse GitLab URL: {url}")

        repo_name = project_path.split("/")[-1]
        encoded = quote(project_path, safe="")

        headers: dict[str, str] = {}
        if config.gitlab_token:
            headers["PRIVATE-TOKEN"] = config.gitlab_token

        file_tree: list[FileInfo] = []

        async with httpx.AsyncClient(headers=headers, timeout=30) as client:
            # Fetch repository tree (paginated, recursive)
            page = 1
            count = 0
            while count < config.max_files:
                resp = await client.get(
                    f"https://gitlab.com/api/v4/projects/{encoded}/repository/tree",
                    params={"recursive": "true", "per_page": 100, "page": page},
                )
                if resp.status_code != 200:
                    break
                items = resp.json()
                if not items:
                    break
                for item in items:
                    if item.get("type") != "blob":
                        continue
                    path = item["path"]
                    ext = Path(path).suffix
                    if config.include_extensions and ext not in config.include_extensions:
                        continue
                    if any(ex in path for ex in config.exclude_paths):
                        continue
                    file_tree.append(FileInfo(path=path, language=_ext_to_lang(ext)))
                    count += 1
                    if count >= config.max_files:
                        break
                page += 1

        git_log: list = []
        try:
            import git as gitpython

            clone_url = url if url.endswith(".git") else url + ".git"
            if config.gitlab_token:
                clone_url = clone_url.replace(
                    "https://", f"https://oauth2:{config.gitlab_token}@"
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
