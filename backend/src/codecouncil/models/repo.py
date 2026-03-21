"""Repository context models for CodeCouncil."""

from datetime import datetime

from pydantic import BaseModel, Field


class FileInfo(BaseModel):
    """Metadata about a single file in the repository."""

    path: str
    language: str = ""
    loc: int = 0
    age_days: int = 0
    last_modified_days: int = 0
    churn_rate: float = 0.0
    authors: list[str] = Field(default_factory=list)


class Commit(BaseModel):
    """A single git commit."""

    hash: str
    author: str
    date: datetime
    message: str
    files_changed: list[str] = Field(default_factory=list)


class ChurnReport(BaseModel):
    """Report on file churn within a time window."""

    window_days: int
    total_commits: int = 0
    flagged_files: list[str] = Field(default_factory=list)


class BusFactorReport(BaseModel):
    """Report on bus factor risk across modules."""

    flagged_modules: list[dict] = Field(default_factory=list)
    min_authors_threshold: int = 2


class DeadCodeItem(BaseModel):
    """A single dead code item detected in the repository."""

    file_path: str
    name: str
    line_start: int = 0
    item_type: str = "function"


class ImportGraph(BaseModel):
    """Directed import graph for the repository."""

    edges: list[dict] = Field(default_factory=list)
    nodes: list[str] = Field(default_factory=list)


class CircularDep(BaseModel):
    """A circular dependency detected in the import graph."""

    cycle: list[str]


class Dependency(BaseModel):
    """A project dependency and its version status."""

    name: str
    current_version: str = ""
    latest_version: str = ""
    is_outdated: bool = False
    is_abandoned: bool = False


class CVEResult(BaseModel):
    """A CVE vulnerability found in a dependency."""

    package: str
    cve_id: str
    severity: str = ""
    summary: str = ""


class SecretFinding(BaseModel):
    """A potential secret detected in the repository."""

    file_path: str
    line_number: int
    pattern_type: str
    hash: str


class LicenceReport(BaseModel):
    """Report on licences used in the project and its dependencies."""

    project_licence: str = ""
    dependencies_licences: list[dict] = Field(default_factory=list)
    incompatibilities: list[str] = Field(default_factory=list)


class TestCoverage(BaseModel):
    """Test coverage statistics for the repository."""

    test_file_count: int = 0
    source_file_count: int = 0
    ratio: float = 0.0
    coverage_percentage: float | None = None


class RepoStats(BaseModel):
    """High-level statistics about the repository."""

    total_files: int = 0
    total_loc: int = 0
    languages: dict[str, int] = Field(default_factory=dict)
    total_authors: int = 0


class RepoContext(BaseModel):
    """Full context gathered during ingestion of a repository."""

    repo_url: str
    repo_name: str
    file_tree: list[FileInfo] = Field(default_factory=list)
    git_log: list[Commit] = Field(default_factory=list)
    churn_report: ChurnReport | None = None
    bus_factor_report: BusFactorReport | None = None
    dead_code: list[DeadCodeItem] = Field(default_factory=list)
    import_graph: ImportGraph | None = None
    circular_deps: list[CircularDep] = Field(default_factory=list)
    dependencies: list[Dependency] = Field(default_factory=list)
    cve_results: list[CVEResult] = Field(default_factory=list)
    secret_findings: list[SecretFinding] = Field(default_factory=list)
    licence_report: LicenceReport | None = None
    test_coverage: TestCoverage | None = None
    summary_stats: RepoStats | None = None
