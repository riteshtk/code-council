"""CVE scanner — check dependencies against the OSV.dev batch API."""
from __future__ import annotations

import httpx

from codecouncil.models.repo import CVEResult, Dependency

_OSV_BATCH_URL = "https://api.osv.dev/v1/querybatch"

# Map ecosystem names → OSV ecosystem identifiers
_ECOSYSTEM_MAP: dict[str, str] = {
    "pypi": "PyPI",
    "npm": "npm",
    "go": "Go",
    "crates": "crates.io",
    "maven": "Maven",
    "rubygems": "RubyGems",
}


async def scan_cves(dependencies: list[Dependency]) -> list[CVEResult]:
    """Scan *dependencies* against OSV.dev and return CVEResult objects."""
    if not dependencies:
        return []

    queries = []
    for dep in dependencies:
        ecosystem = _ECOSYSTEM_MAP.get(dep.ecosystem, dep.ecosystem)
        if not ecosystem:
            continue
        query: dict = {
            "package": {"name": dep.name, "ecosystem": ecosystem},
        }
        if dep.current_version:
            query["version"] = dep.current_version
        queries.append(query)

    if not queries:
        return []

    results: list[CVEResult] = []
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(_OSV_BATCH_URL, json={"queries": queries})
            if resp.status_code != 200:
                return []

            data = resp.json()
            for i, batch_result in enumerate(data.get("results", [])):
                dep = dependencies[i] if i < len(dependencies) else None
                for vuln in batch_result.get("vulns", []):
                    vuln_id = vuln.get("id", "")
                    severity = _extract_severity(vuln)
                    summary = vuln.get("summary", "")
                    results.append(
                        CVEResult(
                            package=dep.name if dep else "",
                            cve_id=vuln_id,
                            severity=severity,
                            summary=summary,
                        )
                    )
    except Exception:
        pass

    return results


def _extract_severity(vuln: dict) -> str:
    """Best-effort extraction of CVSS severity label."""
    for rating in vuln.get("severity", []):
        score = rating.get("score", "")
        if score:
            return str(score)
    database_specific = vuln.get("database_specific", {})
    return database_specific.get("severity", "")
