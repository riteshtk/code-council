"""EventPersistenceHandler — writes events to PostgreSQL via EventRepository."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from codecouncil.db.repositories import EventRepository
from codecouncil.models.events import Event


class EventPersistenceHandler:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def handle(self, event: Event) -> None:
        """Persist an event to the database."""
        async with self._session_factory() as session:
            repo = EventRepository(session)
            await repo.create_event({
                "id": event.event_id,
                "run_id": event.run_id,
                "sequence": event.sequence,
                "agent": event.agent,
                "event_type": event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type),
                "phase": event.phase.value if hasattr(event.phase, "value") else str(event.phase),
                "round": event.round,
                "content": event.content,
                "structured": event.structured,
                "provider": event.metadata.provider,
                "model": event.metadata.model,
                "input_tokens": event.metadata.input_tokens,
                "output_tokens": event.metadata.output_tokens,
                "cost_usd": event.metadata.cost_usd,
                "latency_ms": event.metadata.latency_ms,
                "cached": event.metadata.cached,
            })
            await session.commit()
