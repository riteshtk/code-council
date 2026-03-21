"""Local filesystem ingestion source."""
from __future__ import annotations

from pathlib import Path

from codecouncil.config.schema import IngestConfig
from codecouncil.ingestion.base import IngestionSource
from codecouncil.models.repo import FileInfo, RepoContext


class LocalSource(IngestionSource):
    """Ingest a local directory (with optional git history)."""

    def can_handle(self, url: str) -> bool:
        # Handle absolute paths, relative paths, and ~ paths.
        # Does not match http/https/ssh URLs.
        if url.startswith(("http://", "https://", "git@", "ssh://")):
            return False
        return True

    async def ingest(self, url: str, config: IngestConfig) -> RepoContext:
        repo_path = Path(url).expanduser().resolve()
        repo_name = repo_path.name

        file_tree = _scan_directory(repo_path, config)
        git_log = _get_git_log(repo_path, config)

        return RepoContext(
            repo_url=str(repo_path),
            repo_name=repo_name,
            file_tree=file_tree,
            git_log=git_log,
        )


def _scan_directory(root: Path, config: IngestConfig) -> list[FileInfo]:
    """Walk the directory tree and collect FileInfo objects."""
    file_tree: list[FileInfo] = []
    count = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        rel_str = str(rel)
        # Exclude directories in exclusion list
        if any(ex in rel_str for ex in config.exclude_paths):
            continue
        ext = path.suffix
        if config.include_extensions and ext not in config.include_extensions:
            continue
        size_kb = path.stat().st_size / 1024
        if size_kb > config.max_file_size_kb:
            continue
        file_tree.append(FileInfo(path=rel_str, language=_ext_to_lang(ext)))
        count += 1
        if count >= config.max_files:
            break
    return file_tree


def _get_git_log(repo_path: Path, config: IngestConfig) -> list:
    if not (repo_path / ".git").exists():
        return []
    try:
        import git as gitpython

        repo = gitpython.Repo(str(repo_path))
        commits = []
        from codecouncil.models.repo import Commit

        for c in repo.iter_commits(max_count=config.git_log_limit):
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
    except Exception:
        return []


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
