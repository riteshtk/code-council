"""Agent registry — discovers and manages agent definitions."""
from __future__ import annotations
import importlib
import json
import logging
from pathlib import Path
from codecouncil.agents.definition import AgentDefinition

logger = logging.getLogger("codecouncil.registry")


class AgentRegistry:
    def __init__(self):
        self._agents: dict[str, AgentDefinition] = {}

    def discover_builtin(self) -> None:
        """Scan agents/definitions/ for built-in agent definitions."""
        definitions_dir = Path(__file__).parent / "definitions"
        if not definitions_dir.exists():
            logger.warning("No definitions directory found at %s", definitions_dir)
            return
        for py_file in sorted(definitions_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            try:
                module = importlib.import_module(f"codecouncil.agents.definitions.{py_file.stem}")
                if hasattr(module, "definition"):
                    defn = module.definition
                    self._agents[defn.handle] = defn
                    logger.info("Loaded agent: %s (%s)", defn.handle, defn.name)
            except Exception as exc:
                logger.error("Failed to load agent definition %s: %s", py_file.name, exc)

    async def load_custom_from_db(self, session_factory) -> None:
        """Load custom agents from DB."""
        try:
            async with session_factory() as db:
                from codecouncil.db.repositories import PersonaRepository
                repo = PersonaRepository(db)
                personas = await repo.list_personas()
                for p in personas:
                    if p.name and p.name.startswith("agent:"):
                        try:
                            data = json.loads(p.content)
                            defn = AgentDefinition(**data, is_builtin=False)
                            self._agents[defn.handle] = defn
                            logger.info("Loaded custom agent from DB: %s", defn.handle)
                        except Exception as exc:
                            logger.warning("Failed to load custom agent %s: %s", p.name, exc)
        except Exception as exc:
            logger.warning("Failed to load custom agents from DB: %s", exc)

    def get(self, handle: str) -> AgentDefinition | None:
        return self._agents.get(handle)

    def list_all(self) -> list[AgentDefinition]:
        return list(self._agents.values())

    def list_enabled(self) -> list[AgentDefinition]:
        return [a for a in self._agents.values() if a.is_enabled]

    def list_analysts(self) -> list[AgentDefinition]:
        """Agents that run analysis (everyone except scribe)."""
        return [a for a in self.list_enabled() if a.debate_role != "scribe"]

    def list_voting(self) -> list[AgentDefinition]:
        return [a for a in self.list_enabled() if a.can_vote]

    def get_proposer(self) -> AgentDefinition | None:
        for a in self.list_enabled():
            if a.debate_role == "proposer":
                return a
        return None

    def get_challenger(self) -> AgentDefinition | None:
        for a in self.list_enabled():
            if a.debate_role == "challenger":
                return a
        return None

    def get_scribe(self) -> AgentDefinition | None:
        for a in self.list_enabled():
            if a.debate_role == "scribe":
                return a
        return None

    def register(self, defn: AgentDefinition) -> None:
        self._agents[defn.handle] = defn

    def unregister(self, handle: str) -> bool:
        if handle in self._agents and not self._agents[handle].is_builtin:
            del self._agents[handle]
            return True
        return False
