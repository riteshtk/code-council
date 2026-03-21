"""Licence analyzer — detect project licence and flag dependency incompatibilities."""
from __future__ import annotations

from pathlib import Path

from codecouncil.models.repo import Dependency, LicenceReport

_LICENCE_PATTERNS: dict[str, list[str]] = {
    "MIT": ["MIT License", "MIT licence", "Permission is hereby granted, free of charge"],
    "Apache-2.0": ["Apache License", "Apache-2.0", "Version 2.0, January 2004"],
    "GPL-2.0": ["GNU GENERAL PUBLIC LICENSE", "Version 2, June 1991"],
    "GPL-3.0": ["GNU GENERAL PUBLIC LICENSE", "Version 3, 29 June 2007"],
    "LGPL-2.1": ["GNU LESSER GENERAL PUBLIC LICENSE", "Version 2.1"],
    "LGPL-3.0": ["GNU LESSER GENERAL PUBLIC LICENSE", "Version 3"],
    "BSD-2-Clause": ["Redistribution and use in source and binary forms"],
    "BSD-3-Clause": ["Redistribution and use in source and binary forms", "Neither the name"],
    "ISC": ["ISC License", "Permission to use, copy, modify"],
    "MPL-2.0": ["Mozilla Public License 2.0"],
    "AGPL-3.0": ["GNU AFFERO GENERAL PUBLIC LICENSE"],
    "Unlicense": ["This is free and unencumbered software released into the public domain"],
}

_LICENCE_FILES = ["LICENSE", "LICENSE.md", "LICENSE.txt", "LICENCE", "LICENCE.md", "COPYING"]

# GPL-family licences — incompatible with permissive (MIT/Apache/BSD/ISC) projects
_COPYLEFT_LICENCES = {"GPL-2.0", "GPL-3.0", "LGPL-2.1", "LGPL-3.0", "AGPL-3.0"}
_PERMISSIVE_LICENCES = {"MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause", "ISC", "Unlicense"}


async def analyze_licences(
    repo_path: str,
    dependencies: list[Dependency],
) -> LicenceReport:
    """Detect project licence and check dependency compatibility."""
    root = Path(repo_path)

    # Find and parse LICENSE file
    project_licence = _detect_project_licence(root)

    # Check dependency licences (best-effort from PyPI/npm metadata)
    dep_licences: list[dict] = []
    incompatibilities: list[str] = []

    for dep in dependencies:
        dep_licence = await _fetch_dep_licence(dep)
        if dep_licence:
            dep_licences.append({"name": dep.name, "licence": dep_licence})
            # Flag copyleft deps in permissive projects
            if (
                project_licence in _PERMISSIVE_LICENCES
                and dep_licence in _COPYLEFT_LICENCES
            ):
                incompatibilities.append(
                    f"{dep.name} ({dep_licence}) is incompatible with {project_licence} project"
                )

    return LicenceReport(
        project_licence=project_licence,
        dependencies_licences=dep_licences,
        incompatibilities=incompatibilities,
    )


def _detect_project_licence(root: Path) -> str:
    for name in _LICENCE_FILES:
        lic_path = root / name
        if lic_path.exists():
            content = lic_path.read_text(errors="ignore")
            return _match_licence(content)
    return ""


def _match_licence(content: str) -> str:
    # Sort by specificity (longer match lists first)
    scored: list[tuple[int, str]] = []
    for licence, patterns in _LICENCE_PATTERNS.items():
        if all(p in content for p in patterns):
            scored.append((len(patterns), licence))
    if scored:
        return max(scored)[1]
    return "Unknown"


async def _fetch_dep_licence(dep: Dependency) -> str:
    """Best-effort: fetch licence from PyPI metadata."""
    import httpx

    try:
        if dep.ecosystem == "pypi":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"https://pypi.org/pypi/{dep.name}/json")
                if resp.status_code == 200:
                    return resp.json().get("info", {}).get("license", "") or ""
    except Exception:
        pass
    return ""
