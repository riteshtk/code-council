"""BaseAgent abstract class for CodeCouncil agents."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import AsyncIterator

from codecouncil.events.bus import EventBus
from codecouncil.models.agents import AgentIdentity, AgentMemory, DebateRole
from codecouncil.models.findings import Finding
from codecouncil.models.proposals import Proposal
from codecouncil.models.state import CouncilState
from codecouncil.models.votes import Vote, VoteType
from codecouncil.providers.base import LLMConfig, LLMResponse, Message, ProviderPlugin


@dataclass
class DebateContext:
    current_round: int = 0
    max_rounds: int = 3
    active_proposal: dict | None = None
    addressed_by: str | None = None
    debate_history: list[dict] = field(default_factory=list)
    addressing_agent: str | None = None


@dataclass
class AgentResponse:
    content: str
    findings: list[Finding] = field(default_factory=list)
    proposals: list[Proposal] = field(default_factory=list)
    addressing: str | None = None


class BaseAgent(ABC):
    identity: AgentIdentity
    config: dict  # Agent config from CouncilConfig
    memory: AgentMemory | None = None
    provider: ProviderPlugin | None = None
    event_bus: EventBus | None = None

    def __init__(
        self,
        config: dict | None = None,
        provider: ProviderPlugin | None = None,
        event_bus: EventBus | None = None,
    ):
        self.config = config or {}
        self.provider = provider
        self.event_bus = event_bus
        self.memory = None

    @abstractmethod
    async def analyze(self, state: CouncilState) -> list[Finding]:
        """Run analysis phase. Return findings."""
        ...

    @abstractmethod
    async def speak(self, state: CouncilState, context: DebateContext) -> AgentResponse:
        """Speak during debate. Return response with potential proposals."""
        ...

    @abstractmethod
    async def vote(self, proposal: dict, state: CouncilState) -> Vote:
        """Vote on a proposal."""
        ...

    async def update_memory(self, state: CouncilState) -> None:
        """Update agent memory after session."""
        pass

    def _build_system_prompt(self) -> str:
        """Build system prompt from persona + memory."""
        parts = [self._get_persona()]
        if self.memory and self.memory.known_patterns:
            parts.append("\n## Your Memory (from past sessions)")
            for pattern in self.memory.known_patterns[-5:]:
                parts.append(f"- {pattern}")
        if self.memory and self.memory.interpersonal_history:
            parts.append("\n## Interpersonal Notes")
            for note in self.memory.interpersonal_history[-3:]:
                parts.append(f"- {note}")
        return "\n".join(parts)

    @abstractmethod
    def _get_persona(self) -> str:
        """Return persona prompt string."""
        ...

    async def _call_llm(self, messages: list[Message], config: LLMConfig | None = None) -> str:
        """Call LLM and return full response. Emits events."""
        if not self.provider:
            raise RuntimeError(f"No provider configured for {self.identity.handle}")

        llm_config = config or LLMConfig(
            model=self.config.get("model", "gpt-4o"),
            temperature=self.config.get("temperature", 0.3),
            max_tokens=self.config.get("max_tokens", 2000),
        )

        if self.event_bus:
            # Emit thinking event
            pass

        response = await self.provider.complete(messages, llm_config)

        if self.event_bus:
            # Emit speaking event
            pass

        return response.content

    async def _stream_llm(
        self,
        messages: list[Message],
        run_id=None,
        phase=None,
    ) -> AsyncIterator[str]:
        """Stream LLM response. Yields tokens."""
        if not self.provider:
            raise RuntimeError(f"No provider configured for {self.identity.handle}")

        llm_config = LLMConfig(
            model=self.config.get("model", "gpt-4o"),
            temperature=self.config.get("temperature", 0.3),
            max_tokens=self.config.get("max_tokens", 2000),
        )

        async for token in self.provider.stream(messages, llm_config):
            yield token

    @staticmethod
    def parse_findings(text: str, agent: str, run_id) -> list[Finding]:
        """Parse findings from agent text output using markers."""
        import re
        from uuid import UUID

        from codecouncil.models.findings import Finding, Severity

        findings = []
        pattern = r"\[FINDING:(CRITICAL|HIGH|MEDIUM|INFO)\]\s*(.*?)(?=\[FINDING:|$)"
        for match in re.finditer(pattern, text, re.DOTALL):
            severity = Severity[match.group(1)]
            content = match.group(2).strip()
            # Split content and implication if separated by "Implication:"
            parts = content.split("Implication:", 1)
            findings.append(
                Finding(
                    run_id=UUID(run_id) if isinstance(run_id, str) else run_id,
                    agent=agent,
                    severity=severity,
                    content=parts[0].strip(),
                    implication=parts[1].strip() if len(parts) > 1 else "",
                )
            )
        return findings

    @staticmethod
    def parse_proposals(
        text: str, agent: str, run_id, start_number: int = 1
    ) -> list[Proposal]:
        """Parse proposals from agent text output."""
        import re
        from uuid import UUID

        from codecouncil.models.proposals import Proposal

        proposals = []
        pattern = r"\[PROPOSAL\]\s*Title:\s*(.*?)\n.*?Goal:\s*(.*?)\n.*?Effort:\s*(.*?)\n"
        for i, match in enumerate(re.finditer(pattern, text, re.DOTALL)):
            proposals.append(
                Proposal(
                    run_id=UUID(run_id) if isinstance(run_id, str) else run_id,
                    proposal_number=start_number + i,
                    title=match.group(1).strip(),
                    goal=match.group(2).strip(),
                    effort=match.group(3).strip(),
                    author_agent=agent,
                )
            )
        return proposals

    @staticmethod
    def parse_vote(text: str, agent: str, run_id, proposal_id) -> Vote:
        """Parse vote from agent text output."""
        import re
        from uuid import UUID

        vote_type = VoteType.ABSTAIN
        confidence = 0.5
        rationale = text.strip()

        if re.search(r"\[VOTE:YES\]", text):
            vote_type = VoteType.YES
        elif re.search(r"\[VOTE:NO\]", text):
            vote_type = VoteType.NO
        elif re.search(r"\[VOTE:ABSTAIN\]", text):
            vote_type = VoteType.ABSTAIN

        conf_match = re.search(r"Confidence:\s*([\d.]+)", text)
        if conf_match:
            confidence = min(1.0, max(0.0, float(conf_match.group(1))))

        return Vote(
            run_id=UUID(run_id) if isinstance(run_id, str) else run_id,
            proposal_id=UUID(proposal_id) if isinstance(proposal_id, str) else proposal_id,
            agent=agent,
            vote=vote_type,
            rationale=rationale,
            confidence=confidence,
        )
