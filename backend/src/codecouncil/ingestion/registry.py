"""Auto-detect the appropriate ingestion source from a URL or path."""
from __future__ import annotations

from codecouncil.ingestion.base import IngestionSource


class IngestionRegistry:
    """Registry of all available ingestion sources.

    Sources are checked in registration order; the first one whose
    ``can_handle`` returns True is used.  A fallback may be provided via
    ``config.ingest.source`` for ambiguous inputs.
    """

    def __init__(self) -> None:
        self._sources: list[IngestionSource] = []
        self._register_defaults()

    def _register_defaults(self) -> None:
        # Import here to avoid circular imports at module load time.
        from codecouncil.ingestion.archive import ArchiveSource
        from codecouncil.ingestion.bitbucket import BitbucketSource
        from codecouncil.ingestion.github import GitHubSource
        from codecouncil.ingestion.gitlab import GitLabSource
        from codecouncil.ingestion.local import LocalSource

        self._sources = [
            GitHubSource(),
            GitLabSource(),
            BitbucketSource(),
            ArchiveSource(),
            LocalSource(),
        ]

    def register(self, source: IngestionSource) -> None:
        """Register a custom ingestion source at highest priority."""
        self._sources.insert(0, source)

    def detect(self, url: str) -> IngestionSource | None:
        """Return the first source that can handle *url*, or None."""
        for source in self._sources:
            if source.can_handle(url):
                return source
        return None
