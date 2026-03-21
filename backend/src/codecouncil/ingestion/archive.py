"""Archive ingestion source — .zip and .tar.gz extraction."""
from __future__ import annotations

import tarfile
import tempfile
import zipfile
from pathlib import Path

from codecouncil.config.schema import IngestConfig
from codecouncil.ingestion.base import IngestionSource
from codecouncil.models.repo import RepoContext


class ArchiveSource(IngestionSource):
    """Ingest a .zip or .tar.gz archive by extracting and delegating to LocalSource."""

    def can_handle(self, url: str) -> bool:
        lower = url.lower()
        return lower.endswith(".zip") or lower.endswith(".tar.gz") or lower.endswith(".tgz")

    async def ingest(self, url: str, config: IngestConfig) -> RepoContext:
        from codecouncil.ingestion.local import LocalSource

        archive_path = Path(url).expanduser().resolve()
        if not archive_path.exists():
            raise FileNotFoundError(f"Archive not found: {archive_path}")

        with tempfile.TemporaryDirectory() as tmpdir:
            extract_dir = Path(tmpdir)
            _extract(archive_path, extract_dir)
            # Delegate to LocalSource
            local_source = LocalSource()
            context = await local_source.ingest(str(extract_dir), config)
            # Override name/url to reflect the archive
            context.repo_url = url
            context.repo_name = archive_path.stem.replace(".tar", "")
            return context


def _extract(archive_path: Path, dest: Path) -> None:
    lower = str(archive_path).lower()
    if lower.endswith(".zip"):
        with zipfile.ZipFile(archive_path, "r") as zf:
            zf.extractall(dest)
    elif lower.endswith(".tar.gz") or lower.endswith(".tgz"):
        with tarfile.open(archive_path, "r:gz") as tf:
            tf.extractall(dest)
    else:
        raise ValueError(f"Unsupported archive format: {archive_path}")
