"""LangGraph StateGraph definition for the CodeCouncil council graph.

The graph encodes the full lifecycle of a CodeCouncil run:

    ingest → analyse → opening → debate ─┐
                                    ↑    │ (loop while rounds < max and proposals unresolved)
                                    └────┘
                                         ↓
                                       voting → scribing ─→ [review] ─→ finalise → END
                                                             └─────────────────────┘
                                                             (HITL optional; review can redebate)
"""

from langgraph.graph import END, StateGraph

from codecouncil.graph.nodes import (
    analyse_node,
    debate_node,
    finalise_node,
    ingest_node,
    opening_node,
    review_decision,
    review_node,
    scribing_node,
    should_continue_debate,
    should_review,
    voting_node,
)


def build_council_graph(checkpointer=None):
    """Build and compile the LangGraph council StateGraph.

    Args:
        checkpointer: An optional LangGraph checkpointer (e.g. MemorySaver).
                      When provided, the graph gains persistence / resumability.

    Returns:
        A compiled LangGraph runnable (CompiledGraph) ready to be invoked with
        ``await graph.ainvoke(initial_state, config={"configurable": {"thread_id": run_id}})``.
    """
    # Use plain dict as the state type — CouncilState is a TypedDict which is
    # compatible with dict at runtime; using dict keeps LangGraph happy with
    # serialisation and avoids annotation issues on older LangGraph versions.
    graph = StateGraph(dict)

    # ------------------------------------------------------------------
    # Register nodes
    # ------------------------------------------------------------------
    graph.add_node("ingest", ingest_node)
    graph.add_node("analyse", analyse_node)
    graph.add_node("opening", opening_node)
    graph.add_node("debate", debate_node)
    graph.add_node("voting", voting_node)
    graph.add_node("scribing", scribing_node)
    graph.add_node("review", review_node)
    graph.add_node("finalise", finalise_node)

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    graph.set_entry_point("ingest")

    # ------------------------------------------------------------------
    # Linear edges
    # ------------------------------------------------------------------
    graph.add_edge("ingest", "analyse")
    graph.add_edge("analyse", "opening")
    graph.add_edge("opening", "debate")

    # ------------------------------------------------------------------
    # Conditional: debate may loop back on itself
    # ------------------------------------------------------------------
    graph.add_conditional_edges(
        "debate",
        should_continue_debate,
        {
            "continue": "debate",
            "vote": "voting",
        },
    )

    graph.add_edge("voting", "scribing")

    # ------------------------------------------------------------------
    # Conditional: optional HITL review after scribing
    # ------------------------------------------------------------------
    graph.add_conditional_edges(
        "scribing",
        should_review,
        {
            "review": "review",
            "finalise": "finalise",
        },
    )

    # ------------------------------------------------------------------
    # Conditional: after review, either redebate or finalise
    # ------------------------------------------------------------------
    graph.add_conditional_edges(
        "review",
        review_decision,
        {
            "redebate": "debate",
            "finalise": "finalise",
        },
    )

    graph.add_edge("finalise", END)

    # ------------------------------------------------------------------
    # Compile
    # ------------------------------------------------------------------
    compiled = graph.compile(checkpointer=checkpointer)
    return compiled
