"""The Scribe agent — neutral witness, synthesizer, and RFC author."""

from codecouncil.agents.base import AgentResponse, BaseAgent, DebateContext
from codecouncil.config.defaults import SCRIBE_PERSONA
from codecouncil.models.agents import AgentIdentity, DebateRole
from codecouncil.models.findings import Finding
from codecouncil.models.state import CouncilState
from codecouncil.models.votes import Vote, VoteType
from codecouncil.providers.base import Message


class Scribe(BaseAgent):
    """The Scribe: neutral witness, records all voices, authors the RFC."""

    identity: AgentIdentity = AgentIdentity(
        name="The Scribe",
        handle="scribe",
        color="#4ecdc4",
        description="Neutral witness and RFC author.",
        debate_role=DebateRole.SCRIBE,
    )

    def _get_persona(self) -> str:
        return SCRIBE_PERSONA

    async def analyze(self, state: CouncilState) -> list[Finding]:
        """Scribe observes only. Returns empty list."""
        return []

    async def speak(self, state: CouncilState, context: DebateContext) -> AgentResponse:
        """Summarize the current debate state. Preserve exact quotes."""
        debate_history = context.debate_history or []
        findings = state.get("findings", [])
        proposals = state.get("proposals", [])
        votes = state.get("votes", [])

        history_text = ""
        if debate_history:
            history_lines = []
            for entry in debate_history:
                history_lines.append(f"{entry.get('agent', '?')}: {entry.get('content', '')}")
            history_text = "\n\n".join(history_lines)

        user_prompt = (
            f"Summarize the debate so far for Round {context.current_round}.\n\n"
            "Record what each agent said, preserving their exact key phrases and arguments. "
            "Do not smooth over disagreements. Note where deadlocks or strong challenges occurred. "
            "You do not hold opinions — you record accurately.\n\n"
            f"Findings so far: {len(findings)}\n"
            f"Proposals so far: {len(proposals)}\n"
            f"Votes so far: {len(votes)}\n\n"
            f"Full debate transcript:\n{history_text}"
        )

        messages = [
            Message(role="system", content=self._build_system_prompt()),
            Message(role="user", content=user_prompt),
        ]

        content = await self._call_llm(messages)
        return AgentResponse(content=content, findings=[], proposals=[])

    async def vote(self, proposal: dict, state: CouncilState) -> Vote:
        """Scribe does not vote on proposals. Always ABSTAIN."""
        from uuid import UUID

        run_id = state["run_id"]
        proposal_id = proposal.get("id", "")

        return Vote(
            run_id=UUID(run_id) if isinstance(run_id, str) else run_id,
            proposal_id=UUID(proposal_id) if isinstance(proposal_id, str) else proposal_id,
            agent=self.identity.handle,
            vote=VoteType.ABSTAIN,
            rationale="The Scribe does not vote on proposals. Abstaining as a matter of mandate.",
            confidence=1.0,
        )

    async def synthesize_rfc(self, state: CouncilState) -> str:
        """Build full RFC content from state."""
        repo_url = state.get("repo_url", "unknown")
        findings = state.get("findings", [])
        proposals = state.get("proposals", [])
        votes = state.get("votes", [])
        debate_rounds = state.get("debate_rounds", [])
        opening_statements = state.get("opening_statements", [])

        # Build a rich context for the RFC
        findings_text = "\n".join(
            f"- [{f.get('severity', 'INFO')}] {f.get('agent', '?')}: {f.get('content', '')} "
            f"Implication: {f.get('implication', '')}"
            for f in findings
        )

        proposals_text = "\n".join(
            f"- #{p.get('proposal_number', '?')} {p.get('title', '')} "
            f"by {p.get('author_agent', '?')} | Goal: {p.get('goal', '')} | Effort: {p.get('effort', '')} "
            f"| Status: {p.get('status', '')}"
            for p in proposals
        )

        votes_text = "\n".join(
            f"- {v.get('agent', '?')} voted {v.get('vote', '?')} on proposal "
            f"{v.get('proposal_id', '?')}: {v.get('rationale', '')}"
            for v in votes
        )

        openings_text = "\n\n".join(
            f"**{s.get('agent', '?')}**: {s.get('content', '')}"
            for s in opening_statements
        )

        rounds_text = "\n\n".join(
            f"Round {r.get('round_number', '?')}:\n" +
            "\n".join(
                f"  {t.get('agent', '?')}: {t.get('content', '')}"
                for t in r.get("turns", [])
            )
            for r in debate_rounds
        )

        user_prompt = (
            f"Write a complete RFC for the CodeCouncil session on repository: {repo_url}\n\n"
            "Structure the RFC with these sections:\n"
            "# RFC: [Repository Name] — CodeCouncil Analysis\n\n"
            "## Executive Summary\n"
            "## Findings\n"
            "## Debate\n"
            "## Proposals\n"
            "## Votes\n"
            "## Outcome\n"
            "## Minority Positions (if any)\n\n"
            "Use the exact words agents said. Do not smooth disagreements.\n\n"
            f"Opening Statements:\n{openings_text}\n\n"
            f"Findings:\n{findings_text}\n\n"
            f"Debate Rounds:\n{rounds_text}\n\n"
            f"Proposals:\n{proposals_text}\n\n"
            f"Votes:\n{votes_text}"
        )

        messages = [
            Message(role="system", content=self._build_system_prompt()),
            Message(role="user", content=user_prompt),
        ]

        rfc_content = await self._call_llm(messages)
        return rfc_content.strip()
