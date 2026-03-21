import uuid
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from codecouncil.db.models import (
    AgentMemoryModel,
    EventModel,
    FindingModel,
    PersonaModel,
    ProposalModel,
    RunModel,
    SessionModel,
    VoteModel,
)


class RunRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_run(
        self,
        run_id: uuid.UUID,
        repo_url: str,
        repo_name: str,
        config_snapshot: dict,
    ) -> RunModel:
        run = RunModel(
            id=run_id,
            repo_url=repo_url,
            repo_name=repo_name,
            status="pending",
            phase="init",
            config_snapshot=config_snapshot,
        )
        self.session.add(run)
        await self.session.flush()
        await self.session.refresh(run)
        return run

    async def get_run(self, run_id: uuid.UUID) -> RunModel | None:
        result = await self.session.execute(select(RunModel).where(RunModel.id == run_id))
        return result.scalar_one_or_none()

    async def list_runs(self, limit: int = 20, offset: int = 0) -> list[RunModel]:
        result = await self.session.execute(
            select(RunModel)
            .order_by(RunModel.started_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def update_run_status(
        self, run_id: uuid.UUID, status: str, phase: str | None = None
    ) -> None:
        values: dict = {"status": status}
        if phase is not None:
            values["phase"] = phase
        if status in ("completed", "failed", "cancelled"):
            values["completed_at"] = datetime.now(tz=timezone.utc)
        await self.session.execute(
            update(RunModel).where(RunModel.id == run_id).values(**values)
        )

    async def update_run_cost(self, run_id: uuid.UUID, cost: float) -> None:
        await self.session.execute(
            update(RunModel).where(RunModel.id == run_id).values(total_cost_usd=cost)
        )

    async def delete_run(self, run_id: uuid.UUID) -> None:
        await self.session.execute(delete(RunModel).where(RunModel.id == run_id))


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_event(self, event_data: dict) -> EventModel:
        event = EventModel(**event_data)
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def get_events_for_run(
        self,
        run_id: uuid.UUID,
        agent: str | None = None,
        event_type: str | None = None,
        phase: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[EventModel]:
        query = select(EventModel).where(EventModel.run_id == run_id)
        if agent is not None:
            query = query.where(EventModel.agent == agent)
        if event_type is not None:
            query = query.where(EventModel.event_type == event_type)
        if phase is not None:
            query = query.where(EventModel.phase == phase)
        query = query.order_by(EventModel.sequence).limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_events_after_sequence(
        self, run_id: uuid.UUID, sequence: int
    ) -> list[EventModel]:
        result = await self.session.execute(
            select(EventModel)
            .where(EventModel.run_id == run_id, EventModel.sequence > sequence)
            .order_by(EventModel.sequence)
        )
        return list(result.scalars().all())


class FindingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_finding(self, finding_data: dict) -> FindingModel:
        finding = FindingModel(**finding_data)
        self.session.add(finding)
        await self.session.flush()
        await self.session.refresh(finding)
        return finding

    async def get_findings_for_run(self, run_id: uuid.UUID) -> list[FindingModel]:
        result = await self.session.execute(
            select(FindingModel)
            .where(FindingModel.run_id == run_id)
            .order_by(FindingModel.created_at)
        )
        return list(result.scalars().all())


class ProposalRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_proposal(self, proposal_data: dict) -> ProposalModel:
        proposal = ProposalModel(**proposal_data)
        self.session.add(proposal)
        await self.session.flush()
        await self.session.refresh(proposal)
        return proposal

    async def get_proposals_for_run(self, run_id: uuid.UUID) -> list[ProposalModel]:
        result = await self.session.execute(
            select(ProposalModel)
            .where(ProposalModel.run_id == run_id)
            .order_by(ProposalModel.proposal_number, ProposalModel.version)
        )
        return list(result.scalars().all())

    async def update_proposal_status(self, proposal_id: uuid.UUID, status: str) -> None:
        await self.session.execute(
            update(ProposalModel)
            .where(ProposalModel.id == proposal_id)
            .values(status=status, updated_at=datetime.now(tz=timezone.utc))
        )


class VoteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_vote(self, vote_data: dict) -> VoteModel:
        vote = VoteModel(**vote_data)
        self.session.add(vote)
        await self.session.flush()
        await self.session.refresh(vote)
        return vote

    async def get_votes_for_run(self, run_id: uuid.UUID) -> list[VoteModel]:
        result = await self.session.execute(
            select(VoteModel)
            .where(VoteModel.run_id == run_id)
            .order_by(VoteModel.created_at)
        )
        return list(result.scalars().all())

    async def get_votes_for_proposal(self, proposal_id: uuid.UUID) -> list[VoteModel]:
        result = await self.session.execute(
            select(VoteModel)
            .where(VoteModel.proposal_id == proposal_id)
            .order_by(VoteModel.created_at)
        )
        return list(result.scalars().all())


class SessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(
        self, name: str, run_ids: list | None = None
    ) -> SessionModel:
        sess = SessionModel(
            id=uuid.uuid4(),
            name=name,
            run_ids=run_ids or [],
            created_at=datetime.now(tz=timezone.utc),
        )
        self.session.add(sess)
        await self.session.flush()
        await self.session.refresh(sess)
        return sess

    async def get_session(self, session_id: uuid.UUID) -> SessionModel | None:
        result = await self.session.execute(
            select(SessionModel).where(SessionModel.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_sessions(self, limit: int = 20, offset: int = 0) -> list[SessionModel]:
        result = await self.session.execute(
            select(SessionModel)
            .order_by(SessionModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())


class AgentMemoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_memory(self, agent_handle: str) -> list[AgentMemoryModel]:
        result = await self.session.execute(
            select(AgentMemoryModel)
            .where(AgentMemoryModel.agent_handle == agent_handle)
            .order_by(AgentMemoryModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def save_memory(
        self,
        agent_handle: str,
        session_id: uuid.UUID | None,
        summary: str,
        token_count: int,
    ) -> AgentMemoryModel:
        memory = AgentMemoryModel(
            id=uuid.uuid4(),
            agent_handle=agent_handle,
            session_id=session_id,
            summary=summary,
            token_count=token_count,
            created_at=datetime.now(tz=timezone.utc),
        )
        self.session.add(memory)
        await self.session.flush()
        await self.session.refresh(memory)
        return memory

    async def clear_memory(self, agent_handle: str) -> None:
        await self.session.execute(
            delete(AgentMemoryModel).where(AgentMemoryModel.agent_handle == agent_handle)
        )


class PersonaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_persona(
        self, name: str, content: str, is_default: bool = False
    ) -> PersonaModel:
        now = datetime.now(tz=timezone.utc)
        persona = PersonaModel(
            id=uuid.uuid4(),
            name=name,
            content=content,
            is_default=is_default,
            created_at=now,
            updated_at=now,
        )
        self.session.add(persona)
        await self.session.flush()
        await self.session.refresh(persona)
        return persona

    async def get_persona(self, name: str) -> PersonaModel | None:
        result = await self.session.execute(
            select(PersonaModel).where(PersonaModel.name == name)
        )
        return result.scalar_one_or_none()

    async def list_personas(self) -> list[PersonaModel]:
        result = await self.session.execute(
            select(PersonaModel).order_by(PersonaModel.name)
        )
        return list(result.scalars().all())

    async def update_persona(self, name: str, content: str) -> None:
        await self.session.execute(
            update(PersonaModel)
            .where(PersonaModel.name == name)
            .values(content=content, updated_at=datetime.now(tz=timezone.utc))
        )

    async def delete_persona(self, name: str) -> None:
        await self.session.execute(delete(PersonaModel).where(PersonaModel.name == name))
