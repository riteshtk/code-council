"""The Visionary agent — forward architect and proposal generator."""

from codecouncil.agents.base import AgentResponse, BaseAgent, DebateContext
from codecouncil.config.defaults import VISIONARY_PERSONA
from codecouncil.models.agents import AgentIdentity, DebateRole
from codecouncil.models.findings import Finding
from codecouncil.models.state import CouncilState
from codecouncil.models.votes import Vote, VoteType
from codecouncil.providers.base import Message


class Visionary(BaseAgent):
    """The Visionary: forward architect, grounded in technical reality."""

    identity: AgentIdentity = AgentIdentity(
        name="The Visionary",
        handle="visionary",
        color="#6c5ce7",
        description="Forward architect and concrete improvement proposer.",
        debate_role=DebateRole.PROPOSER,
    )

    def _get_persona(self) -> str:
        return VISIONARY_PERSONA

    async def analyze(self, state: CouncilState) -> list[Finding]:
        """Run analysis focused on DDD patterns, refactor paths, design patterns, boundaries."""
        run_id = state["run_id"]
        repo_context = state.get("repo_context") or {}
        summary_stats = repo_context.get("summary_stats", {})
        file_tree = repo_context.get("file_tree", [])

        system_prompt = self._build_system_prompt()
        user_prompt = (
            "Analyze the following repository context for architectural findings.\n\n"
            f"Repository: {state.get('repo_url', 'unknown')}\n"
            f"Total files: {summary_stats.get('total_files', 'unknown')}\n"
            f"File tree sample: {str(file_tree[:20])}\n"
            f"Stats: {summary_stats}\n\n"
            "Focus your analysis on:\n"
            "- DDD pattern violations and bounded context leakage\n"
            "- Refactoring opportunities (design pattern improvements)\n"
            "- Module boundary violations\n"
            "- Architectural debt and coupling hotspots\n"
            "- Paths toward improved structure\n\n"
            "Format each finding as:\n"
            "[FINDING:CRITICAL|HIGH|MEDIUM|INFO] <what you observed>. Implication: <what it means>\n\n"
            "Ground every finding in technical reality from the repository context."
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        response_text = await self._call_llm(messages)
        return self.parse_findings(response_text, self.identity.handle, run_id)

    async def speak(self, state: CouncilState, context: DebateContext) -> AgentResponse:
        """Create proposals with [PROPOSAL] markers. Can revise or withdraw proposals."""
        run_id = state["run_id"]
        findings = state.get("findings", [])
        existing_proposals = state.get("proposals", [])
        my_proposals = [p for p in existing_proposals if p.get("author_agent") == self.identity.handle]

        history_text = ""
        if context.debate_history:
            history_lines = []
            for entry in context.debate_history[-8:]:
                history_lines.append(f"{entry.get('agent', '?')}: {entry.get('content', '')}")
            history_text = "\n".join(history_lines)

        addressed_by = context.addressed_by or ""
        addressing_note = (
            f"You are being directly addressed by {addressed_by}. Respond and revise your proposal if their challenge lands.\n"
            if addressed_by
            else ""
        )

        start_number = len(existing_proposals) + 1

        user_prompt = (
            f"{addressing_note}"
            f"Round {context.current_round} of {context.max_rounds}.\n\n"
            "Present or revise concrete improvement proposals. Ground every proposal in the findings. "
            "If a challenge lands, update your proposal rather than defending the original blindly. "
            "You may withdraw a proposal if the evidence against it is conclusive.\n\n"
            "For each NEW proposal, use this exact format:\n"
            "[PROPOSAL]\n"
            "Title: <short title>\n"
            "Goal: <what it achieves>\n"
            "Effort: <S|M|L|XL>\n\n"
            f"All findings so far:\n{findings}\n\n"
            f"Your existing proposals:\n{my_proposals}\n\n"
            f"Debate history:\n{history_text}"
        )

        messages = [
            Message(role="system", content=self._build_system_prompt()),
            Message(role="user", content=user_prompt),
        ]

        content = await self._call_llm(messages)
        proposals = self.parse_proposals(content, self.identity.handle, run_id, start_number)
        return AgentResponse(content=content, findings=[], proposals=proposals)

    async def vote(self, proposal: dict, state: CouncilState) -> Vote:
        """YES on own proposals unless genuinely convinced otherwise."""
        run_id = state["run_id"]
        proposal_id = proposal.get("id", "")
        is_own = proposal.get("author_agent") == self.identity.handle

        findings = state.get("findings", [])
        votes = state.get("votes", [])
        challenges = [v for v in votes if v.get("vote") == "NO"]

        own_note = (
            "This is your own proposal. Vote YES unless the Skeptic or Archaeologist has surfaced "
            "evidence that genuinely changes your assessment.\n\n"
            if is_own
            else "Vote on this proposal based on its architectural merit.\n\n"
        )

        user_prompt = (
            f"{own_note}"
            f"Proposal: {proposal.get('title', '')}\n"
            f"Goal: {proposal.get('goal', '')}\n"
            f"Effort: {proposal.get('effort', '')}\n\n"
            f"Challenges so far:\n{challenges}\n\n"
            f"Architectural findings:\n{findings}\n\n"
            "Format: [VOTE:YES|NO|ABSTAIN]\n<rationale>\nConfidence: <0.0-1.0>"
        )

        messages = [
            Message(role="system", content=self._build_system_prompt()),
            Message(role="user", content=user_prompt),
        ]

        response_text = await self._call_llm(messages)
        return self.parse_vote(response_text, self.identity.handle, run_id, proposal_id)
