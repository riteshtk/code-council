"""
Unit tests for the CodeCouncil config system.

Tests cover:
1. Default config validity
2. Agent config defaults
3. Provider inheritance
4. Vote threshold validation
5. YAML loading
6. Environment variable overrides (CC_ prefix)
7. Layer precedence
"""
import os
import tempfile

import pytest
import yaml
from pydantic import ValidationError

from codecouncil.config.schema import (
    AgentsSettings,
    ArchaeologistConfig,
    CouncilConfig,
    CouncilSettings,
    IngestConfig,
    LLMSettings,
    OutputConfig,
    ProviderConfig,
    ScribeConfig,
    SkepticConfig,
    UIConfig,
    VisionaryConfig,
)
from codecouncil.config.loader import load_config


# ---------------------------------------------------------------------------
# 1. test_default_config_is_valid
# ---------------------------------------------------------------------------

class TestDefaultConfig:
    def test_default_config_is_valid(self):
        """CouncilConfig() should construct without error and have expected defaults."""
        cfg = CouncilConfig()

        # council
        assert cfg.council.name == "Default Council"
        assert cfg.council.max_rounds == 3
        assert cfg.council.parallel_analysis is True
        assert cfg.council.debate_topology == "adversarial"
        assert cfg.council.custom_topology == []
        assert cfg.council.vote_threshold == 0.5
        assert cfg.council.vote_threshold_critical == 1.0
        assert cfg.council.deadlock_detection is True
        assert cfg.council.hitl_enabled is False
        assert cfg.council.hitl_timeout_minutes == 30
        assert cfg.council.budget_limit_usd == 0
        assert cfg.council.session_memory is True

        # llm
        assert cfg.llm.default_provider == "openai"
        assert cfg.llm.default_model == "gpt-4o"

        # output
        assert cfg.output.directory == "./output"
        assert cfg.output.save_debate_transcript is True

        # ui
        assert cfg.ui.api_port == 8000
        assert cfg.ui.ui_port == 5173
        assert cfg.ui.theme == "dark"

    def test_council_config_serializes(self):
        """CouncilConfig should be serializable to dict."""
        cfg = CouncilConfig()
        data = cfg.model_dump()
        assert isinstance(data, dict)
        assert "council" in data
        assert "llm" in data
        assert "agents" in data
        assert "ingest" in data
        assert "output" in data
        assert "ui" in data


# ---------------------------------------------------------------------------
# 2. test_agent_config_defaults
# ---------------------------------------------------------------------------

class TestAgentConfigDefaults:
    def test_archaeologist_defaults(self):
        cfg = ArchaeologistConfig()
        assert cfg.temperature == 0.3
        assert cfg.max_tokens == 2000
        assert cfg.enabled is True
        assert cfg.streaming is True
        assert cfg.vote_weight == 1.0

    def test_skeptic_defaults(self):
        cfg = SkepticConfig()
        assert cfg.temperature == 0.2
        assert cfg.max_tokens == 2000
        assert cfg.can_deadlock is True
        assert cfg.deadlock_requires_evidence is True

    def test_visionary_defaults(self):
        cfg = VisionaryConfig()
        assert cfg.temperature == 0.7
        assert cfg.max_tokens == 2500
        assert cfg.max_proposals == 8
        assert cfg.ambition_level == "moderate"

    def test_scribe_defaults(self):
        cfg = ScribeConfig()
        assert cfg.temperature == 0.1
        assert cfg.max_tokens == 4000
        assert cfg.output_format == "markdown"
        assert cfg.preserve_dissent is True
        assert cfg.include_debate_excerpt is True
        assert cfg.excerpt_max_exchanges == 5
        assert cfg.action_item_format == "numbered"

    def test_all_agents_in_settings(self):
        settings = AgentsSettings()
        assert isinstance(settings.archaeologist, ArchaeologistConfig)
        assert isinstance(settings.skeptic, SkepticConfig)
        assert isinstance(settings.visionary, VisionaryConfig)
        assert isinstance(settings.scribe, ScribeConfig)
        assert settings.custom == []


# ---------------------------------------------------------------------------
# 3. test_provider_inherits_default
# ---------------------------------------------------------------------------

class TestProviderInheritsDefault:
    def test_agent_with_empty_provider_string(self):
        """An agent with provider='' should be detectable so caller can fall back to default."""
        cfg = CouncilConfig()
        # By default all agents have provider="" which means "use default"
        assert cfg.agents.archaeologist.provider == ""
        assert cfg.agents.skeptic.provider == ""
        assert cfg.agents.visionary.provider == ""
        assert cfg.agents.scribe.provider == ""

    def test_default_provider_in_llm(self):
        llm = LLMSettings()
        assert llm.default_provider == "openai"
        assert llm.default_model == "gpt-4o"

    def test_all_provider_keys_present(self):
        llm = LLMSettings()
        for key in ("openai", "anthropic", "google", "mistral", "ollama", "bedrock", "azure"):
            assert key in llm.providers, f"Missing provider key: {key}"
            assert isinstance(llm.providers[key], ProviderConfig)

    def test_provider_config_defaults(self):
        pc = ProviderConfig()
        assert pc.api_key == ""
        assert pc.base_url == ""
        assert pc.org_id == ""
        assert pc.region == "us-east-1"
        assert pc.profile == ""
        assert pc.endpoint == ""
        assert pc.api_version == "2024-02-01"


# ---------------------------------------------------------------------------
# 4. test_vote_threshold_range
# ---------------------------------------------------------------------------

class TestVoteThresholdRange:
    def test_valid_threshold(self):
        cs = CouncilSettings(vote_threshold=0.6, vote_threshold_critical=0.9)
        assert cs.vote_threshold == 0.6
        assert cs.vote_threshold_critical == 0.9

    def test_threshold_zero_is_valid(self):
        cs = CouncilSettings(vote_threshold=0.0)
        assert cs.vote_threshold == 0.0

    def test_threshold_one_is_valid(self):
        cs = CouncilSettings(vote_threshold=1.0)
        assert cs.vote_threshold == 1.0

    def test_threshold_below_zero_is_rejected(self):
        with pytest.raises(ValidationError):
            CouncilSettings(vote_threshold=-0.1)

    def test_threshold_above_one_is_rejected(self):
        with pytest.raises(ValidationError):
            CouncilSettings(vote_threshold=1.1)

    def test_critical_threshold_below_zero_is_rejected(self):
        with pytest.raises(ValidationError):
            CouncilSettings(vote_threshold_critical=-0.5)

    def test_critical_threshold_above_one_is_rejected(self):
        with pytest.raises(ValidationError):
            CouncilSettings(vote_threshold_critical=1.5)

    def test_vote_weight_below_zero_rejected(self):
        with pytest.raises(ValidationError):
            ArchaeologistConfig(vote_weight=-1.0)


# ---------------------------------------------------------------------------
# 5. test_config_from_yaml
# ---------------------------------------------------------------------------

class TestConfigFromYaml:
    def test_load_simple_yaml(self):
        data = {
            "council": {
                "name": "Test Council",
                "max_rounds": 5,
            },
            "ui": {
                "theme": "light",
            },
        }
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            tmp_path = f.name

        try:
            cfg = load_config(config_path=tmp_path)
            assert cfg.council.name == "Test Council"
            assert cfg.council.max_rounds == 5
            assert cfg.ui.theme == "light"
            # Unspecified fields should keep defaults
            assert cfg.council.debate_topology == "adversarial"
        finally:
            os.unlink(tmp_path)

    def test_load_partial_yaml_preserves_defaults(self):
        data = {"council": {"max_rounds": 10}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            tmp_path = f.name

        try:
            cfg = load_config(config_path=tmp_path)
            assert cfg.council.max_rounds == 10
            # All other defaults intact
            assert cfg.council.name == "Default Council"
            assert cfg.llm.default_provider == "openai"
        finally:
            os.unlink(tmp_path)

    def test_load_nonexistent_yaml_uses_defaults(self):
        cfg = load_config(config_path="/nonexistent/path/config.yaml")
        assert cfg.council.name == "Default Council"


# ---------------------------------------------------------------------------
# 6. test_config_env_override
# ---------------------------------------------------------------------------

class TestConfigEnvOverride:
    def test_cc_council_max_rounds(self, monkeypatch):
        monkeypatch.setenv("CC_COUNCIL__MAX_ROUNDS", "7")
        cfg = load_config()
        assert cfg.council.max_rounds == 7

    def test_cc_llm_default_provider(self, monkeypatch):
        monkeypatch.setenv("CC_LLM__DEFAULT_PROVIDER", "anthropic")
        cfg = load_config()
        assert cfg.llm.default_provider == "anthropic"

    def test_cc_ui_theme(self, monkeypatch):
        monkeypatch.setenv("CC_UI__THEME", "light")
        cfg = load_config()
        assert cfg.ui.theme == "light"

    def test_cc_council_hitl_enabled(self, monkeypatch):
        monkeypatch.setenv("CC_COUNCIL__HITL_ENABLED", "true")
        cfg = load_config()
        assert cfg.council.hitl_enabled is True

    def test_env_bool_false(self, monkeypatch):
        monkeypatch.setenv("CC_COUNCIL__PARALLEL_ANALYSIS", "false")
        cfg = load_config()
        assert cfg.council.parallel_analysis is False

    def test_env_float(self, monkeypatch):
        monkeypatch.setenv("CC_COUNCIL__VOTE_THRESHOLD", "0.75")
        cfg = load_config()
        assert cfg.council.vote_threshold == 0.75


# ---------------------------------------------------------------------------
# 7. test_config_layer_precedence
# ---------------------------------------------------------------------------

class TestConfigLayerPrecedence:
    def test_runtime_config_overrides_defaults(self):
        data = {"council": {"max_rounds": 9}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            tmp_path = f.name

        try:
            cfg = load_config(config_path=tmp_path)
            assert cfg.council.max_rounds == 9
        finally:
            os.unlink(tmp_path)

    def test_api_overrides_override_yaml(self):
        data = {"council": {"max_rounds": 5}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            tmp_path = f.name

        try:
            cfg = load_config(
                config_path=tmp_path,
                overrides={"council": {"max_rounds": 11}},
            )
            assert cfg.council.max_rounds == 11
        finally:
            os.unlink(tmp_path)

    def test_env_overrides_yaml(self, monkeypatch):
        data = {"council": {"max_rounds": 4}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            tmp_path = f.name

        monkeypatch.setenv("CC_COUNCIL__MAX_ROUNDS", "6")
        try:
            cfg = load_config(config_path=tmp_path)
            assert cfg.council.max_rounds == 6
        finally:
            os.unlink(tmp_path)

    def test_api_overrides_override_env(self, monkeypatch):
        monkeypatch.setenv("CC_COUNCIL__MAX_ROUNDS", "6")
        cfg = load_config(overrides={"council": {"max_rounds": 15}})
        assert cfg.council.max_rounds == 15

    def test_project_config_overrides_global(self):
        global_data = {"council": {"name": "Global Council", "max_rounds": 2}}
        project_data = {"council": {"name": "Project Council"}}

        with (
            tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as gf,
            tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as pf,
        ):
            yaml.dump(global_data, gf)
            yaml.dump(project_data, pf)
            global_path = gf.name
            project_path = pf.name

        try:
            cfg = load_config(global_path=global_path, project_path=project_path)
            # project overrides name, but global max_rounds still applies
            assert cfg.council.name == "Project Council"
            assert cfg.council.max_rounds == 2
        finally:
            os.unlink(global_path)
            os.unlink(project_path)

    def test_deep_merge_preserves_sibling_keys(self):
        """Merging partial llm config should not wipe out other provider keys."""
        data = {"llm": {"default_provider": "anthropic"}}
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as f:
            yaml.dump(data, f)
            tmp_path = f.name

        try:
            cfg = load_config(config_path=tmp_path)
            assert cfg.llm.default_provider == "anthropic"
            # The providers dict should still exist with all keys
            assert "openai" in cfg.llm.providers
        finally:
            os.unlink(tmp_path)


# ---------------------------------------------------------------------------
# Personas
# ---------------------------------------------------------------------------

class TestPersonas:
    def test_persona_strings_exist(self):
        from codecouncil.config.defaults import (
            ARCHAEOLOGIST_PERSONA,
            SCRIBE_PERSONA,
            SKEPTIC_PERSONA,
            VISIONARY_PERSONA,
        )
        for persona in (
            ARCHAEOLOGIST_PERSONA,
            SKEPTIC_PERSONA,
            VISIONARY_PERSONA,
            SCRIBE_PERSONA,
        ):
            assert isinstance(persona, str)
            assert len(persona) > 100  # substantive content

    def test_archaeologist_persona_is_data_first(self):
        from codecouncil.config.defaults import ARCHAEOLOGIST_PERSONA
        # Should mention data / commits / historical focus
        lower = ARCHAEOLOGIST_PERSONA.lower()
        assert any(word in lower for word in ("commit", "data", "history", "historical", "codebase"))

    def test_skeptic_persona_mentions_deadlock(self):
        from codecouncil.config.defaults import SKEPTIC_PERSONA
        assert "deadlock" in SKEPTIC_PERSONA.upper() or "DEADLOCK" in SKEPTIC_PERSONA

    def test_visionary_persona_mentions_proposals(self):
        from codecouncil.config.defaults import VISIONARY_PERSONA
        lower = VISIONARY_PERSONA.lower()
        assert any(word in lower for word in ("proposal", "propose", "vision", "future", "improve"))

    def test_scribe_persona_is_neutral(self):
        from codecouncil.config.defaults import SCRIBE_PERSONA
        lower = SCRIBE_PERSONA.lower()
        assert any(word in lower for word in ("neutral", "witness", "quote", "rfc", "record", "vote"))


# ---------------------------------------------------------------------------
# Ingest / Output / Debate topology
# ---------------------------------------------------------------------------

class TestIngestConfig:
    def test_ingest_defaults(self):
        ic = IngestConfig()
        assert ic.max_files == 500
        assert ic.max_file_size_kb == 100
        assert ic.git_log_limit == 200
        assert ic.ast_parse is True
        assert ic.dependency_scan is True
        assert ic.cve_scan is True
        assert ic.secret_detection is True
        assert ic.licence_check is True
        assert ic.incremental is True
        assert len(ic.include_extensions) == 16
        assert "node_modules" in ic.exclude_paths

    def test_output_defaults(self):
        oc = OutputConfig()
        assert oc.directory == "./output"
        assert oc.save_debate_transcript is True
        assert oc.save_agent_events is True
        assert oc.save_cost_report is True
        assert oc.save_state_snapshots is False
        assert oc.open_after_complete is True
        assert "markdown" in oc.formats


class TestDebateTopology:
    def test_valid_topologies(self):
        for topo in (
            "adversarial",
            "collaborative",
            "socratic",
            "open_floor",
            "panel",
            "custom",
        ):
            cs = CouncilSettings(debate_topology=topo)
            assert cs.debate_topology == topo

    def test_invalid_topology_rejected(self):
        with pytest.raises(ValidationError):
            CouncilSettings(debate_topology="random_made_up")
