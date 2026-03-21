"""CodeCouncil ingestion package."""
from codecouncil.ingestion.base import IngestionSource
from codecouncil.ingestion.context import build_repo_context
from codecouncil.ingestion.registry import IngestionRegistry

__all__ = [
    "IngestionSource",
    "IngestionRegistry",
    "build_repo_context",
]
