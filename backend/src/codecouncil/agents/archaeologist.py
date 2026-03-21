"""The Archaeologist agent — forensic historian of the codebase."""

from codecouncil.agents.base import AgentResponse, BaseAgent, DebateContext
from codecouncil.config.defaults import ARCHAEOLOGIST_PERSONA
from codecouncil.models.agents import AgentIdentity, DebateRole
from codecouncil.models.findings import Finding
from codecouncil.models.state import CouncilState
from codecouncil.models.votes import Vote, VoteType
from codecouncil.providers.base import Message


class Archaeologist(BaseAgent):
    """The Archaeologist: speaks only in verifiable facts from commit history and metrics."""

    identity: AgentIdentity = AgentIdentity(
        name="The Archaeologist",
        handle="archaeologist",
        color="#d4a574",
        description="Forensic historian of the codebase.",
        debate_role=DebateRole.ANALYST,
    )

    def _get_persona(self) -> str:
        return ARCHAEOLOGIST_PERSONA

    async def analyze(self, state: CouncilState) -> list[Finding]:
        """Run analysis focused on churn, bus factor, dead code, TODOs, commit sentiment."""
        run_id = state["run_id"]
        repo_context = state.get("repo_context") or {}
        summary_stats = repo_context.get("summary_stats", {})
        file_tree = repo_context.get("file_tree", [])

        system_prompt = self._build_system_prompt()
        user_prompt = (
            "Analyze the following repository context and produce findings.\n\n"
            f"Repository: {state.get('repo_url', 'unknown')}\n"
            f"Total files: {summary_stats.get('total_files', 'unknown')}\n"
            f"File tree sample: {str(file_tree[:20])}\n"
            f"Stats: {summary_stats}\n\n"
            "Focus your analysis on:\n"
            "- File churn (files changed most frequently)\n"
            "- Bus factor (single author concentration)\n"
            "- Dead code and obsolete modules\n"
            "- Unresolved TODOs / FIXMEs and their age\n"
            "- Commit sentiment (regression patterns, repeated failures)\n"
            "- File age and author concentration\n\n"
            "Format each finding as:\n"
            "[FINDING:CRITICAL|HIGH|MEDIUM|INFO] <what you observed>. Implication: <what it means>\n\n"
            "Cite specific evidence. Do not make recommendations."
        )

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt),
        ]

        response_text = await self._call_llm(messages)
        return self.parse_findings(response_text, self.identity.handle, run_id)

    async def speak(self, state: CouncilState, context: DebateContext) -> AgentResponse:
        """Present findings declaratively. Reference specific files, commits, numbers."""
        run_id = state["run_id"]
        findings = state.get("findings", [])
        my_findings = [f for f in findings if f.get("agent") == self.identity.handle]

        history_text = ""
        if context.debate_history:
            history_lines = []
            for entry in context.debate_history[-6:]:
                history_lines.append(f"{entry.get('agent', '?')}: {entry.get('content', '')}")
            history_text = "\n".join(history_lines)

        addressed_by = context.addressed_by or ""
        addressing_note = (
            f"You are being directly addressed by {addressed_by}. Respond to their points.\n"
            if addressed_by
            else ""
        )

        user_prompt = (
            f"{addressing_note}"
            f"Round {context.current_round} of {context.max_rounds}.\n\n"
            "Present your forensic findings. Reference specific files, commit counts, author "
            "concentrations, and dates. Speak declaratively — you report facts, not opinions. "
            "Do not recommend actions.\n\n"
            f"Your findings:\n{my_findings}\n\n"
            f"Debate history so far:\n{history_text}"
        )

        messages = [
            Message(role="system", content=self._build_system_prompt()),
            Message(role="user", content=user_prompt),
        ]

        content = await self._call_llm(messages)
        return AgentResponse(content=content, findings=[], proposals=[])

    async def vote(self, proposal: dict, state: CouncilState) -> Vote:
        """Vote based on historical precedent."""
        run_id = state["run_id"]
        proposal_id = proposal.get("id", "")
        findings = state.get("findings", [])
        my_findings = [f for f in findings if f.get("agent") == self.identity.handle]

        user_prompt = (
            f"Vote on this proposal based solely on historical evidence from the codebase.\n\n"
            f"Proposal: {proposal.get('title', '')}\n"
            f"Goal: {proposal.get('goal', '')}\n"
            f"Effort: {proposal.get('effort', '')}\n\n"
            f"Your findings:\n{my_findings}\n\n"
            "If this proposal contradicts patterns seen in codebase history (repeated failures, "
            "high churn in the affected area, insufficient test coverage), vote NO.\n\n"
            "Format: [VOTE:YES|NO|ABSTAIN]\n<rationale citing specific evidence>\nConfidence: <0.0–1.0>"
        )

        messages = [
            Message(role="system", content=self._build_system_prompt()),
            Message(role="user", content=user_prompt),
        ]

        response_text = await self._call_llm(messages)
        return self.parse_vote(response_text, self.identity.handle, run_id, proposal_id)
