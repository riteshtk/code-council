"""Tests for the ingestion system."""
import pytest
from pathlib import Path
from codecouncil.ingestion.registry import IngestionRegistry
from codecouncil.ingestion.analyzers.churn import analyze_churn
from codecouncil.ingestion.analyzers.bus_factor import analyze_bus_factor
from codecouncil.ingestion.analyzers.secrets import detect_secrets, PATTERNS
from codecouncil.ingestion.analyzers.dead_code import analyze_dead_code
from codecouncil.ingestion.analyzers.incremental import compute_file_hashes, diff_against_previous
from codecouncil.ingestion.analyzers.test_coverage import analyze_test_coverage
from codecouncil.ingestion.local import LocalSource
from codecouncil.models.repo import Commit, FileInfo, ImportGraph, ChurnReport


def test_registry_detects_github():
    registry = IngestionRegistry()
    source = registry.detect("https://github.com/owner/repo")
    assert source is not None
    assert source.can_handle("https://github.com/owner/repo")


def test_registry_detects_local():
    registry = IngestionRegistry()
    source = registry.detect("/some/local/path")
    assert source is not None


def test_registry_detects_gitlab():
    registry = IngestionRegistry()
    source = registry.detect("https://gitlab.com/owner/repo")
    assert source is not None
    assert source.can_handle("https://gitlab.com/owner/repo")


def test_registry_detects_bitbucket():
    registry = IngestionRegistry()
    source = registry.detect("https://bitbucket.org/workspace/repo")
    assert source is not None
    assert source.can_handle("https://bitbucket.org/workspace/repo")


def test_registry_detects_archive_zip():
    registry = IngestionRegistry()
    source = registry.detect("/tmp/project.zip")
    assert source is not None
    assert source.can_handle("/tmp/project.zip")


def test_registry_detects_archive_tar_gz():
    registry = IngestionRegistry()
    source = registry.detect("/tmp/project.tar.gz")
    assert source is not None
    assert source.can_handle("/tmp/project.tar.gz")


@pytest.mark.asyncio
async def test_churn_calculation():
    from datetime import datetime, timezone, timedelta
    now = datetime.now(timezone.utc)
    commits = [
        Commit(hash=f"abc{i}", author="dev", date=now - timedelta(days=i),
               message="fix", files_changed=["src/main.py"])
        for i in range(10)
    ]
    # Add some commits touching other files
    commits.extend([
        Commit(hash=f"xyz{i}", author="dev", date=now - timedelta(days=i),
               message="feat", files_changed=["src/other.py"])
        for i in range(3)
    ])
    report = await analyze_churn(commits, window_days=90)
    assert report.total_commits == 13
    assert "src/main.py" in report.flagged_files  # 10/13 = 77% > 50%


@pytest.mark.asyncio
async def test_churn_empty():
    report = await analyze_churn([], window_days=90)
    assert report.total_commits == 0
    assert report.flagged_files == []


@pytest.mark.asyncio
async def test_bus_factor():
    per_file_authors = {
        "src/critical.py": ["alice"] * 50,  # Single author
        "src/healthy.py": ["alice"] * 30 + ["bob"] * 30 + ["charlie"] * 20,
    }
    report = await analyze_bus_factor(per_file_authors, min_threshold=2)
    # critical.py should be flagged (bus factor = 1)
    flagged_paths = [m["module"] for m in report.flagged_modules]
    assert any("critical" in p or "src" in p for p in flagged_paths)


@pytest.mark.asyncio
async def test_bus_factor_healthy_module_not_flagged():
    per_file_authors = {
        "lib/healthy.py": ["alice"] * 30 + ["bob"] * 30 + ["charlie"] * 40,
    }
    report = await analyze_bus_factor(per_file_authors, min_threshold=2)
    assert report.flagged_modules == []


@pytest.mark.asyncio
async def test_secret_detection():
    content = '''
    AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
    password = "supersecret123"
    '''
    findings = await detect_secrets("test.py", content)
    assert len(findings) >= 1
    # Verify hash, not raw value
    for f in findings:
        assert len(f.hash) == 64  # SHA-256 hex


@pytest.mark.asyncio
async def test_secret_detection_no_secrets():
    content = "x = 1\ny = 2\n"
    findings = await detect_secrets("clean.py", content)
    assert findings == []


@pytest.mark.asyncio
async def test_dead_code_detection():
    graph = ImportGraph(
        nodes=["module_a", "module_b", "module_c", "module_d"],
        edges=[
            {"from": "module_a", "to": "module_b"},
            {"from": "module_a", "to": "module_c"},
        ]
    )
    dead = await analyze_dead_code(graph, test_files=set())
    # module_d has no inbound edges, module_a has no inbound edges
    dead_names = [d.name for d in dead]
    assert "module_d" in dead_names


@pytest.mark.asyncio
async def test_dead_code_excluded_by_test_files():
    graph = ImportGraph(
        nodes=["module_a", "module_b"],
        edges=[
            {"from": "test_module_a", "to": "module_a"},
        ]
    )
    # module_a is only imported by a test file — should still be dead from prod perspective
    dead = await analyze_dead_code(graph, test_files={"test_module_a"})
    dead_names = [d.name for d in dead]
    assert "module_a" in dead_names


@pytest.mark.asyncio
async def test_incremental_diff():
    current = {"file1.py": "abc123", "file2.py": "def456", "file3.py": "ghi789"}
    previous = {"file1.py": "abc123", "file2.py": "changed", "file4.py": "removed"}
    changed = await diff_against_previous(current, previous)
    assert "file2.py" in changed  # Changed
    assert "file3.py" in changed  # New
    assert "file1.py" not in changed  # Unchanged


@pytest.mark.asyncio
async def test_incremental_no_changes():
    hashes = {"a.py": "111", "b.py": "222"}
    changed = await diff_against_previous(hashes, hashes.copy())
    assert changed == []


@pytest.mark.asyncio
async def test_test_coverage_ratio(tmp_path):
    # Create a mix of source and test files
    files = [
        FileInfo(path="src/main.py", language="python"),
        FileInfo(path="src/utils.py", language="python"),
        FileInfo(path="tests/test_main.py", language="python"),
    ]
    coverage = await analyze_test_coverage(str(tmp_path), files)
    assert coverage.test_file_count == 1
    assert coverage.source_file_count == 2
    assert coverage.ratio == pytest.approx(0.5)


def test_secret_patterns_compile():
    """All secret patterns should be valid regexes."""
    import re
    for name, pattern in PATTERNS.items():
        re.compile(pattern)  # Should not raise


def test_local_source_can_handle():
    from codecouncil.ingestion.local import LocalSource
    ls = LocalSource()
    assert ls.can_handle("/some/path")
    assert ls.can_handle("relative/path")
    assert not ls.can_handle("https://github.com/foo/bar")
    assert not ls.can_handle("git@github.com:foo/bar.git")


def test_github_source_can_handle():
    from codecouncil.ingestion.github import GitHubSource
    gs = GitHubSource()
    assert gs.can_handle("https://github.com/owner/repo")
    assert not gs.can_handle("https://gitlab.com/owner/repo")
    assert not gs.can_handle("/local/path")
