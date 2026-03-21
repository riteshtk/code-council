"""Dead code detector — find nodes with no inbound references in the import graph."""
from __future__ import annotations

from codecouncil.models.repo import DeadCodeItem, ImportGraph


async def analyze_dead_code(
    import_graph: ImportGraph,
    test_files: set[str],
) -> list[DeadCodeItem]:
    """Return nodes that have zero inbound edges (excluding test files as consumers).

    Test files are not counted as meaningful consumers because they import
    modules purely for testing purposes — those modules can still be "dead"
    from production code's perspective.
    """
    # Build set of nodes that are referenced by at least one non-test importer
    referenced: set[str] = set()
    for edge in import_graph.edges:
        source = edge.get("from", "")
        target = edge.get("to", "")
        if source not in test_files:
            referenced.add(target)

    dead: list[DeadCodeItem] = []
    for node in import_graph.nodes:
        if node not in referenced:
            dead.append(
                DeadCodeItem(
                    file_path=node,
                    name=node,
                    item_type="module",
                )
            )
    return dead
