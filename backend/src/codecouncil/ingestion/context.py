"""RepoContext builder — orchestrates all ingestion adapters and analyzers."""
from __future__ import annotations

import asyncio

from codecouncil.config.schema import IngestConfig
from codecouncil.models.repo import RepoContext


async def build_repo_context(
    url: str,
    config: IngestConfig,
    event_bus=None,
) -> RepoContext:
    """Orchestrate ingestion: source adapter + all analyzers in parallel.

    Steps:
      1. Detect the appropriate source adapter from *url*.
      2. Run the adapter to get a basic RepoContext (file_tree, git_log).
      3. Run all analyzers in parallel via asyncio.gather.
      4. Assemble the full RepoContext.
      5. Optionally emit events if *event_bus* is provided.
    """
    from codecouncil.ingestion.analyzers.ast_parser import build_import_graph, detect_circular_deps, parse_ast
    from codecouncil.ingestion.analyzers.bus_factor import analyze_bus_factor
    from codecouncil.ingestion.analyzers.churn import analyze_churn
    from codecouncil.ingestion.analyzers.cve import scan_cves
    from codecouncil.ingestion.analyzers.dead_code import analyze_dead_code
    from codecouncil.ingestion.analyzers.dependency import analyze_dependencies
    from codecouncil.ingestion.analyzers.git_history import analyze_git_history
    from codecouncil.ingestion.analyzers.incremental import compute_file_hashes
    from codecouncil.ingestion.analyzers.licence import analyze_licences
    from codecouncil.ingestion.analyzers.secrets import detect_secrets
    from codecouncil.ingestion.analyzers.test_coverage import analyze_test_coverage
    from codecouncil.ingestion.registry import IngestionRegistry

    registry = IngestionRegistry()
    source = registry.detect(url)
    if source is None:
        raise ValueError(f"No ingestion source found for: {url}")

    _emit(event_bus, "ingestion.started", {"url": url})

    # Step 1 — basic ingestion (file_tree, git_log)
    context = await source.ingest(url, config)
    repo_path = context.repo_url  # may be a local path for cloned/local sources

    _emit(event_bus, "ingestion.files_fetched", {"count": len(context.file_tree)})

    # Step 2 — git history (needed by churn + bus_factor)
    if config.git_log_limit > 0 and context.git_log:
        commits = context.git_log
        per_file_authors: dict[str, list[str]] = {}
        for c in commits:
            for f in c.files_changed:
                per_file_authors.setdefault(f, []).append(c.author)
    else:
        commits = context.git_log
        per_file_authors = {}

    # Step 3 — run analyzers in parallel
    async def _churn():
        return await analyze_churn(commits)

    async def _bus_factor():
        return await analyze_bus_factor(per_file_authors)

    async def _dependencies():
        if config.dependency_scan:
            return await analyze_dependencies(repo_path)
        return []

    async def _test_cov():
        return await analyze_test_coverage(repo_path, context.file_tree)

    # Run independent analyzers concurrently
    (
        churn_report,
        bus_factor_report,
        dependencies,
        test_cov,
    ) = await asyncio.gather(
        _churn(),
        _bus_factor(),
        _dependencies(),
        _test_cov(),
    )

    # CVE scan depends on dependencies
    cve_results = []
    if config.cve_scan and dependencies:
        cve_results = await scan_cves(dependencies)

    # Licence depends on dependencies
    licence_report = None
    if config.licence_check:
        licence_report = await analyze_licences(repo_path, dependencies)

    # AST + import graph (sequential, needed for dead_code)
    import_graph = None
    circular_deps = []
    dead_code = []
    if config.ast_parse:
        try:
            import_graph = await build_import_graph(context.file_tree, repo_path)
            circular_deps = await detect_circular_deps(import_graph)
            test_file_set = {
                fi.path for fi in context.file_tree if _is_test_file(fi.path)
            }
            dead_code = await analyze_dead_code(import_graph, test_file_set)
        except Exception:
            pass

    # Secrets scan per file
    secret_findings = []
    if config.secret_detection:
        for fi in context.file_tree:
            from pathlib import Path

            full = Path(repo_path) / fi.path
            try:
                content = full.read_text(errors="ignore")
                findings = await detect_secrets(fi.path, content)
                secret_findings.extend(findings)
            except Exception:
                continue

    # Assemble
    context.churn_report = churn_report
    context.bus_factor_report = bus_factor_report
    context.dependencies = dependencies
    context.cve_results = cve_results
    context.licence_report = licence_report
    context.import_graph = import_graph
    context.circular_deps = circular_deps
    context.dead_code = dead_code
    context.secret_findings = secret_findings
    context.test_coverage = test_cov

    _emit(event_bus, "ingestion.complete", {"repo": context.repo_name})
    return context


def _is_test_file(path: str) -> bool:
    from fnmatch import fnmatch
    from pathlib import Path

    name = Path(path).name
    patterns = [
        "test_*.py", "*_test.py", "*_test.go",
        "*.test.ts", "*.spec.ts", "*.test.js", "*.spec.js",
    ]
    return any(fnmatch(name, p) for p in patterns)


def _emit(event_bus, event: str, data: dict) -> None:
    if event_bus is None:
        return
    try:
        if hasattr(event_bus, "publish"):
            import asyncio

            asyncio.create_task(event_bus.publish(event, data))
    except Exception:
        pass
