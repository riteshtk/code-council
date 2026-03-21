"""Checkpointing for the CodeCouncil LangGraph council graph.

Uses an in-memory checkpointer by default. A PostgreSQL-backed checkpointer
can be substituted when the database is fully configured (Task 16).
"""

from langgraph.checkpoint.memory import MemorySaver


def create_checkpointer() -> MemorySaver:
    """Create a checkpointer for the council graph.

    Returns a MemorySaver (in-memory) checkpointer suitable for development
    and testing. Replace with an async PostgreSQL checkpointer in production
    once the DB is fully set up.

    Example swap for production:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        checkpointer = AsyncPostgresSaver.from_conn_string(DATABASE_URL)
    """
    return MemorySaver()
