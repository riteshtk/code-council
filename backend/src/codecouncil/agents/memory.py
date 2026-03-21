"""Agent memory management for CodeCouncil."""

from codecouncil.models.agents import AgentMemory
from codecouncil.models.state import CouncilState


class AgentMemoryManager:
    """Manages loading, saving, and summarizing agent memory across sessions."""

    async def load_memory(
        self, agent_handle: str, session_factory=None
    ) -> AgentMemory:
        """Load agent memory from the database, or return empty memory."""
        if session_factory is None:
            return AgentMemory(agent_handle=agent_handle)

        try:
            async with session_factory() as session:
                from sqlalchemy import select
                from codecouncil.db.models import AgentMemoryRecord

                result = await session.execute(
                    select(AgentMemoryRecord).where(
                        AgentMemoryRecord.agent_handle == agent_handle
                    )
                )
                record = result.scalar_one_or_none()
                if record is None:
                    return AgentMemory(agent_handle=agent_handle)
                return AgentMemory(
                    agent_handle=agent_handle,
                    session_summaries=record.session_summaries or [],
                    known_patterns=record.known_patterns or [],
                    interpersonal_history=record.interpersonal_history or [],
                    total_token_count=record.total_token_count or 0,
                )
        except Exception:
            return AgentMemory(agent_handle=agent_handle)

    async def save_memory(
        self,
        agent_handle: str,
        session_summary: str,
        session_factory=None,
    ) -> None:
        """Append a session summary to agent memory in the database."""
        if session_factory is None:
            return

        try:
            async with session_factory() as session:
                from sqlalchemy import select
                from codecouncil.db.models import AgentMemoryRecord

                result = await session.execute(
                    select(AgentMemoryRecord).where(
                        AgentMemoryRecord.agent_handle == agent_handle
                    )
                )
                record = result.scalar_one_or_none()
                if record is None:
                    record = AgentMemoryRecord(
                        agent_handle=agent_handle,
                        session_summaries=[session_summary],
                        known_patterns=[],
                        interpersonal_history=[],
                        total_token_count=0,
                    )
                    session.add(record)
                else:
                    summaries = list(record.session_summaries or [])
                    summaries.append(session_summary)
                    # Keep last 20 summaries to bound memory size
                    record.session_summaries = summaries[-20:]
                await session.commit()
        except Exception:
            pass

    async def summarize_session(
        self, agent, state: CouncilState
    ) -> str:
        """Use agent's LLM to compress session into memory summary."""
        from codecouncil.providers.base import Message, LLMConfig

        repo_url = state.get("repo_url", "unknown")
        findings = state.get("findings", [])
        proposals = state.get("proposals", [])

        summary_prompt = (
            f"Summarize this CodeCouncil session for {agent.identity.handle} in 3-5 bullet points. "
            f"Repository: {repo_url}. "
            f"Findings count: {len(findings)}. "
            f"Proposals count: {len(proposals)}. "
            "Focus on patterns worth remembering for future sessions."
        )

        messages = [
            Message(role="system", content=agent._get_persona()),
            Message(role="user", content=summary_prompt),
        ]

        try:
            summary = await agent._call_llm(
                messages,
                LLMConfig(
                    model=agent.config.get("model", "gpt-4o"),
                    temperature=0.2,
                    max_tokens=500,
                ),
            )
            return summary.strip()
        except Exception as e:
            return f"Session summary unavailable: {e}"

    async def clear_memory(
        self, agent_handle: str, session_factory=None
    ) -> None:
        """Clear all memory for an agent."""
        if session_factory is None:
            return

        try:
            async with session_factory() as session:
                from sqlalchemy import select
                from codecouncil.db.models import AgentMemoryRecord

                result = await session.execute(
                    select(AgentMemoryRecord).where(
                        AgentMemoryRecord.agent_handle == agent_handle
                    )
                )
                record = result.scalar_one_or_none()
                if record is not None:
                    await session.delete(record)
                    await session.commit()
        except Exception:
            pass
