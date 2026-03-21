"""The Skeptic agent — adversarial examiner of security, coupling, and risk."""

from codecouncil.agents.base import AgentResponse, BaseAgent, DebateContext
from codecouncil.config.defaults import SKEPTIC_PERSONA
from codecouncil.models.agents import AgentIdentity, DebateRole
from codecouncil.models.findings import Finding
from codecouncil.models.state import CouncilState
from codecouncil.models.votes import Vote, VoteType
from codecouncil.providers.base import Message


class Skeptic(BaseAgent):
    """The Skeptic: adversarial examiner, last line of rigour."""

    identity: AgentIdentity = AgentIdentity(
        name="The Skeptic",
        handle="skeptic",
        color="#ff6b6b",
        description="Adversarial examiner of risk and correctness.",
        debate_role=DebateRole.CHALLENGER,
    )

    can_deadlock: bool = True

    def _get_persona(self) -> str:
        return SKEPTIC_PERSONA

    async def analyze(self, state: CouncilState) -> list[Finding]:
        """Run analysis focused on security, coupling, CVE, test coverage, API contracts."""
        run_id = state["run_id"]
        repo_context = state.get("repo_context") or {}
        summary_stats = repo_context.get("summary_stats", {})
        file_tree = repo_context.get("file_tree", [])

        system_prompt = self._build_system_prompt()
        user_prompt = (
            "Analyze the following repository context and produce risk findings.\n\n"
            f"Repository: {state.get('repo_url', 'unknown')}\n"
            f"Total files: {summary_stats.get('total_files', 'unknown')}\n"
            f"File tree sample: {str(file_tree[:20])}\n"
            f"Stats: {summary_stats}\n\n"
            "Focus your analysis on:\n"
            "- Security vulnerabilities (CVE-adjacent patterns, insecure dependencies)\n"
            "- Tight coupling and blast radius of changes\n"
            "- Test coverage gaps and missing API contract tests\n"
            "- Performance risk and hidden dependencies\n"
            "- Unacceptable risk areas that would block any proposal\n\n"
            "Format each finding as:\n"
            "[FINDING:CRITICAL|HIGH|MEDIUM|INFO] <what you observed>. Implication: <what it means>\n\n"
            "Be precise. Follow implications to their conclusions."
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        response_text = await self._call_llm(messages)
        return self.parse_findings(response_text, self.identity.handle, run_id)

    async def speak(self, state: CouncilState, context: DebateContext) -> AgentResponse:
        """Challenge other agents by name. Follow implications. Never partially concede."""
        run_id = state["run_id"]
        findings = state.get("findings", [])
        my_findings = [f for f in findings if f.get("agent") == self.identity.handle]

        history_text = ""
        if context.debate_history:
            history_lines = []
            for entry in context.debate_history[-8:]:
                history_lines.append(f"{entry.get('agent', '?')}: {entry.get('content', '')}")
            history_text = "\n".join(history_lines)

        addressed_by = context.addressed_by or ""
        addressing_note = (
            f"You are being directly addressed by {addressed_by}. Respond to their specific points.\n"
            if addressed_by
            else ""
        )

        active_proposal = context.active_proposal
        proposal_text = ""
        if active_proposal:
            proposal_text = (
                f"\nActive proposal under review:\n"
                f"Title: {active_proposal.get('title', '')}\n"
                f"Goal: {active_proposal.get('goal', '')}\n"
                f"Effort: {active_proposal.get('effort', '')}\n"
            )

        user_prompt = (
            f"{addressing_note}"
            f"Round {context.current_round} of {context.max_rounds}.\n\n"
            "Challenge the reasoning in the debate. Name agents directly when challenging their logic. "
            "Follow implications past the point of comfort. A flaw in reasoning is a flaw — not a nuance. "
            "Do not partially concede.\n"
            f"{proposal_text}\n"
            f"Your risk findings:\n{my_findings}\n\n"
            f"Debate history:\n{history_text}"
        )

        messages = [
            Message(role="system", content=self._build_system_prompt()),
            Message(role="user", content=user_prompt),
        ]

        content = await self._call_llm(messages)
        return AgentResponse(content=content, findings=[], proposals=[])

    async def vote(self, proposal: dict, state: CouncilState) -> Vote:
        """Default NO with rationale. Concede only when fully convinced."""
        run_id = state["run_id"]
        proposal_id = proposal.get("id", "")
        findings = state.get("findings", [])
        my_findings = [f for f in findings if f.get("agent") == self.identity.handle]

        user_prompt = (
            f"Vote on this proposal. Your default is NO.\n\n"
            f"Proposal: {proposal.get('title', '')}\n"
            f"Goal: {proposal.get('goal', '')}\n"
            f"Effort: {proposal.get('effort', '')}\n\n"
            f"Your risk findings:\n{my_findings}\n\n"
            "Vote YES only if you are fully convinced the risk is acceptable and the proposal "
            "addresses the underlying issue. Identify the specific weakness you are voting against.\n\n"
            "Format: [VOTE:YES|NO|ABSTAIN]\n<rationale identifying the specific weakness>\nConfidence: <0.0-1.0>"
        )

        messages = [
            Message(role="system", content=self._build_system_prompt()),
            Message(role="user", content=user_prompt),
        ]

        response_text = await self._call_llm(messages)
        return self.parse_vote(response_text, self.identity.handle, run_id, proposal_id)

    async def declare_deadlock(self, proposal: dict, evidence: str) -> dict:
        """Declare a deadlock on a proposal with explicit evidence."""
        return {
            "agent": self.identity.handle,
            "proposal_id": proposal.get("id", ""),
            "proposal_title": proposal.get("title", ""),
            "evidence": evidence,
            "type": "DEADLOCK",
        }
