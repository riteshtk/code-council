"""Agent definition model — single source of truth for agent identity, config, and prompts."""
from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field


class AgentDefinition(BaseModel):
    """Complete agent definition."""
    # Identity
    handle: str
    name: str
    abbr: str
    role: str
    short_role: str
    color: str
    icon: str  # lucide icon name
    description: str = ""

    # LLM Config
    temperature: float = 0.3
    max_tokens: int = 4096
    provider: str = ""
    model: str = ""

    # Behavior
    debate_role: str = "analyst"  # analyst | challenger | proposer | scribe
    vote_weight: float = 1.0
    can_vote: bool = True
    can_deadlock: bool = False
    can_propose: bool = False

    # Persona
    persona: str = ""

    # Phase prompt templates — use {{var}} for template variables
    prompts: dict[str, str] = Field(default_factory=dict)

    # Focus areas
    focus_areas: list[str] = Field(default_factory=list)

    # Policies
    policies: dict[str, str] = Field(default_factory=dict)

    # Extra config
    extra: dict[str, Any] = Field(default_factory=dict)

    # Metadata
    is_builtin: bool = True
    is_enabled: bool = True

    def build_system_prompt(self, memory_context: str = "") -> str:
        parts = [self.persona]
        if self.policies:
            parts.append("\n## Your Policies")
            for policy_name, policy_text in self.policies.items():
                parts.append(f"\n### {policy_name}\n{policy_text}")
        if memory_context:
            parts.append(f"\n## Your Memory (from past sessions)\n{memory_context}")
        return "\n".join(parts)

    def get_prompt(self, phase: str, **kwargs: Any) -> str:
        template = self.prompts.get(phase, "")
        if not template:
            return ""
        for key, value in kwargs.items():
            template = template.replace("{{" + key + "}}", str(value))
        return template

    def to_api_dict(self) -> dict:
        """Return identity + config for API (excludes prompts/persona for brevity)."""
        return {
            "id": self.handle,
            "handle": self.handle,
            "name": self.name,
            "abbr": self.abbr,
            "role": self.role,
            "short_role": self.short_role,
            "color": self.color,
            "icon": self.icon,
            "description": self.description,
            "debate_role": self.debate_role,
            "temperature": self.temperature,
            "can_vote": self.can_vote,
            "can_deadlock": self.can_deadlock,
            "can_propose": self.can_propose,
            "is_builtin": self.is_builtin,
            "is_enabled": self.is_enabled,
            "focus_areas": self.focus_areas,
        }
