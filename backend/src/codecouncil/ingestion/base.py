"""Abstract base class for ingestion sources."""
from __future__ import annotations

from abc import ABC, abstractmethod

from codecouncil.config.schema import IngestConfig
from codecouncil.models.repo import RepoContext


class IngestionSource(ABC):
    """Abstract base for all repository ingestion sources."""

    @abstractmethod
    def can_handle(self, url: str) -> bool:
        """Return True if this source can handle the given URL/path."""
        ...

    @abstractmethod
    async def ingest(self, url: str, config: IngestConfig) -> RepoContext:
        """Ingest the repository and return a basic RepoContext."""
        ...
