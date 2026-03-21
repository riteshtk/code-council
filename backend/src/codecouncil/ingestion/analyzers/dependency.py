"""Dependency analyzer — parse package manifests and check for outdated versions."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

from codecouncil.models.repo import Dependency


async def analyze_dependencies(repo_path: str) -> list[Dependency]:
    """Parse package manifests in *repo_path* and check latest versions."""
    root = Path(repo_path)
    deps: list[Dependency] = []

    # Python — pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        deps.extend(_parse_pyproject(pyproject))

    # JavaScript / Node — package.json
    pkg_json = root / "package.json"
    if pkg_json.exists():
        deps.extend(_parse_package_json(pkg_json))

    # Go — go.mod
    go_mod = root / "go.mod"
    if go_mod.exists():
        deps.extend(_parse_go_mod(go_mod))

    # Rust — Cargo.toml
    cargo = root / "Cargo.toml"
    if cargo.exists():
        deps.extend(_parse_cargo_toml(cargo))

    # Java — pom.xml
    pom = root / "pom.xml"
    if pom.exists():
        deps.extend(_parse_pom_xml(pom))

    # Ruby — Gemfile
    gemfile = root / "Gemfile"
    if gemfile.exists():
        deps.extend(_parse_gemfile(gemfile))

    # Enrich with latest versions (best effort)
    deps = await _enrich_versions(deps)
    return deps


def _parse_pyproject(path: Path) -> list[Dependency]:
    try:
        import tomllib

        data = tomllib.loads(path.read_text())
        raw_deps = data.get("project", {}).get("dependencies", [])
        result = []
        for dep in raw_deps:
            name, version = _split_python_dep(dep)
            result.append(
                Dependency(name=name, current_version=version, ecosystem="pypi")
            )
        return result
    except Exception:
        return []


def _split_python_dep(dep: str) -> tuple[str, str]:
    m = re.match(r"^([A-Za-z0-9_\-\.]+)\s*([><=!~^]+)\s*([\S]+)?", dep)
    if m:
        return m.group(1), m.group(3) or ""
    return dep.strip(), ""


def _parse_package_json(path: Path) -> list[Dependency]:
    try:
        data = json.loads(path.read_text())
        result = []
        for section in ("dependencies", "devDependencies"):
            for name, version in data.get(section, {}).items():
                result.append(
                    Dependency(
                        name=name,
                        current_version=version.lstrip("^~>=<"),
                        ecosystem="npm",
                    )
                )
        return result
    except Exception:
        return []


def _parse_go_mod(path: Path) -> list[Dependency]:
    result = []
    for line in path.read_text().splitlines():
        line = line.strip()
        m = re.match(r"^require\s+(\S+)\s+(\S+)", line)
        if not m:
            m = re.match(r"^(\S+)\s+(v[\S]+)", line)
        if m:
            result.append(
                Dependency(
                    name=m.group(1), current_version=m.group(2), ecosystem="go"
                )
            )
    return result


def _parse_cargo_toml(path: Path) -> list[Dependency]:
    try:
        import tomllib

        data = tomllib.loads(path.read_text())
        result = []
        for section in ("dependencies", "dev-dependencies"):
            for name, val in data.get(section, {}).items():
                if isinstance(val, str):
                    version = val.lstrip("^~>=<")
                elif isinstance(val, dict):
                    version = str(val.get("version", "")).lstrip("^~>=<")
                else:
                    version = ""
                result.append(
                    Dependency(name=name, current_version=version, ecosystem="crates")
                )
        return result
    except Exception:
        return []


def _parse_pom_xml(path: Path) -> list[Dependency]:
    try:
        tree = ET.parse(path)
        root = tree.getroot()
        ns = re.match(r"\{(.+)\}", root.tag)
        prefix = f"{{{ns.group(1)}}}" if ns else ""
        result = []
        for dep in root.iter(f"{prefix}dependency"):
            art = dep.findtext(f"{prefix}artifactId", "")
            ver = dep.findtext(f"{prefix}version", "")
            if art:
                result.append(
                    Dependency(
                        name=art, current_version=ver.strip("${}"), ecosystem="maven"
                    )
                )
        return result
    except Exception:
        return []


def _parse_gemfile(path: Path) -> list[Dependency]:
    result = []
    for line in path.read_text().splitlines():
        m = re.match(r"""^\s*gem\s+['"]([^'"]+)['"](?:,\s*['"]([^'"]+)['"])?""", line)
        if m:
            result.append(
                Dependency(
                    name=m.group(1),
                    current_version=m.group(2) or "",
                    ecosystem="rubygems",
                )
            )
    return result


async def _enrich_versions(deps: list[Dependency]) -> list[Dependency]:
    """Best-effort: fetch latest version from PyPI/npm for known ecosystems."""
    async with httpx.AsyncClient(timeout=10) as client:
        for dep in deps:
            try:
                if dep.ecosystem == "pypi":
                    resp = await client.get(
                        f"https://pypi.org/pypi/{dep.name}/json"
                    )
                    if resp.status_code == 200:
                        latest = resp.json()["info"]["version"]
                        dep.latest_version = latest
                        if dep.current_version and latest != dep.current_version:
                            dep.is_outdated = True
                elif dep.ecosystem == "npm":
                    resp = await client.get(
                        f"https://registry.npmjs.org/{dep.name}/latest"
                    )
                    if resp.status_code == 200:
                        latest = resp.json().get("version", "")
                        dep.latest_version = latest
                        if dep.current_version and latest != dep.current_version:
                            dep.is_outdated = True
            except Exception:
                continue
    return deps
