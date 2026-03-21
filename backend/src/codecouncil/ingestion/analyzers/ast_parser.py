"""AST parser using tree-sitter — extract function/class inventory and build import graphs."""
from __future__ import annotations

from codecouncil.models.repo import CircularDep, FileInfo, ImportGraph

# Map language name → tree-sitter language module
_LANG_MODULES: dict[str, str] = {
    "python": "tree_sitter_python",
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "go": "tree_sitter_go",
    "rust": "tree_sitter_rust",
    "java": "tree_sitter_java",
    "ruby": "tree_sitter_ruby",
}


def _get_ts_language(language: str):
    """Return a tree-sitter Language for the given language name."""
    import importlib

    module_name = _LANG_MODULES.get(language)
    if module_name is None:
        return None
    try:
        mod = importlib.import_module(module_name)
        from tree_sitter import Language

        return Language(mod.language())
    except Exception:
        return None


async def parse_ast(file_path: str, content: str, language: str) -> dict:
    """Parse *content* with tree-sitter.

    Returns a dict with:
      - functions: list of {name, line_start, line_count}
      - classes: list of {name, line_start}
      - imports: list of str (module names)
    """
    ts_lang = _get_ts_language(language)
    result: dict = {"functions": [], "classes": [], "imports": []}

    if ts_lang is None:
        return result

    try:
        from tree_sitter import Parser

        parser = Parser(ts_lang)
        tree = parser.parse(content.encode())

        _walk_node(tree.root_node, content, language, result)
    except Exception:
        pass

    return result


def _walk_node(node, content: str, language: str, result: dict) -> None:
    """Recursively walk the tree-sitter node tree and extract symbols."""
    node_type = node.type

    if language == "python":
        if node_type == "function_definition":
            name = _child_name(node, "identifier")
            if name:
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                result["functions"].append(
                    {"name": name, "line_start": start, "line_count": end - start + 1}
                )
        elif node_type == "class_definition":
            name = _child_name(node, "identifier")
            if name:
                result["classes"].append(
                    {"name": name, "line_start": node.start_point[0] + 1}
                )
        elif node_type in ("import_statement", "import_from_statement"):
            text = content[node.start_byte:node.end_byte]
            result["imports"].append(text.strip())

    elif language in ("javascript", "typescript"):
        if node_type in ("function_declaration", "function", "arrow_function"):
            name = _child_name(node, "identifier")
            if name:
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                result["functions"].append(
                    {"name": name, "line_start": start, "line_count": end - start + 1}
                )
        elif node_type == "class_declaration":
            name = _child_name(node, "identifier")
            if name:
                result["classes"].append(
                    {"name": name, "line_start": node.start_point[0] + 1}
                )
        elif node_type == "import_statement":
            text = content[node.start_byte:node.end_byte]
            result["imports"].append(text.strip())

    elif language == "go":
        if node_type == "function_declaration":
            name = _child_name(node, "identifier")
            if name:
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                result["functions"].append(
                    {"name": name, "line_start": start, "line_count": end - start + 1}
                )
        elif node_type == "import_declaration":
            text = content[node.start_byte:node.end_byte]
            result["imports"].append(text.strip())

    else:
        # Generic fallback — best effort
        if "function" in node_type or "method" in node_type:
            name = _child_name(node, "identifier")
            if name:
                start = node.start_point[0] + 1
                end = node.end_point[0] + 1
                result["functions"].append(
                    {"name": name, "line_start": start, "line_count": end - start + 1}
                )

    for child in node.children:
        _walk_node(child, content, language, result)


def _child_name(node, node_type: str) -> str | None:
    for child in node.children:
        if child.type == node_type:
            return child.text.decode() if child.text else None
    return None


async def build_import_graph(
    file_tree: list[FileInfo],
    repo_path: str,
) -> ImportGraph:
    """Build a directed import graph from all parseable files in *file_tree*."""
    from pathlib import Path

    nodes: set[str] = set()
    edges: list[dict] = []

    for fi in file_tree:
        full = Path(repo_path) / fi.path
        nodes.add(fi.path)
        try:
            content = full.read_text(errors="ignore")
            ast_info = await parse_ast(fi.path, content, fi.language)
            for imp in ast_info.get("imports", []):
                # Normalise import string to a module name
                module = _import_to_module(imp, fi.language)
                if module:
                    nodes.add(module)
                    edges.append({"from": fi.path, "to": module})
        except Exception:
            continue

    return ImportGraph(nodes=sorted(nodes), edges=edges)


def _import_to_module(import_str: str, language: str) -> str | None:
    """Extract the primary module name from an import statement string."""
    import re

    if language == "python":
        m = re.match(r"from\s+([\w.]+)", import_str)
        if m:
            return m.group(1)
        m = re.match(r"import\s+([\w.]+)", import_str)
        if m:
            return m.group(1)
    elif language in ("javascript", "typescript"):
        m = re.search(r'from\s+["\']([^"\']+)["\']', import_str)
        if m:
            return m.group(1)
        m = re.search(r'require\(["\']([^"\']+)["\']\)', import_str)
        if m:
            return m.group(1)
    elif language == "go":
        m = re.search(r'"([^"]+)"', import_str)
        if m:
            return m.group(1)
    return None


async def detect_circular_deps(import_graph: ImportGraph) -> list[CircularDep]:
    """Detect circular dependencies via DFS."""
    adj: dict[str, list[str]] = {n: [] for n in import_graph.nodes}
    for edge in import_graph.edges:
        src = edge.get("from", "")
        dst = edge.get("to", "")
        if src in adj:
            adj[src].append(dst)

    visited: set[str] = set()
    rec_stack: set[str] = set()
    cycles: list[CircularDep] = []

    def dfs(node: str, path: list[str]) -> None:
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbour in adj.get(node, []):
            if neighbour in rec_stack:
                # Found a cycle — extract the cycle portion
                cycle_start = path.index(neighbour)
                cycles.append(CircularDep(cycle=path[cycle_start:] + [neighbour]))
            elif neighbour not in visited:
                dfs(neighbour, path)

        path.pop()
        rec_stack.discard(node)

    for node in import_graph.nodes:
        if node not in visited:
            dfs(node, [])

    return cycles
