import pytest
from codecouncil.providers.base import ProviderPlugin, Message, LLMConfig, LLMResponse
from codecouncil.providers.registry import ProviderRegistry
from codecouncil.providers.cost import CostTracker, LLMCallRecord


class MockProvider(ProviderPlugin):
    name = "mock"

    async def stream(self, messages, config):
        for word in "hello world".split():
            yield word

    async def complete(self, messages, config):
        return LLMResponse(content="hello world", input_tokens=10, output_tokens=5, model="mock-v1")

    def count_tokens(self, text):
        return len(text.split())

    def supports_streaming(self):
        return True

    def max_context_tokens(self):
        return 4096


class FailingProvider(ProviderPlugin):
    name = "failing"

    async def stream(self, messages, config):
        raise ConnectionError("Provider unavailable")
        yield  # make it a generator

    async def complete(self, messages, config):
        raise ConnectionError("Provider unavailable")

    def count_tokens(self, text):
        return 0

    def supports_streaming(self):
        return True

    def max_context_tokens(self):
        return 4096


def test_registry_register_and_get():
    registry = ProviderRegistry()
    provider = MockProvider()
    registry.register("mock", provider)
    assert registry.get("mock") is provider


def test_registry_get_unknown_raises():
    registry = ProviderRegistry()
    with pytest.raises(KeyError):
        registry.get("nonexistent")


def test_registry_list_all():
    registry = ProviderRegistry()
    registry.register("mock", MockProvider())
    assert "mock" in registry.list_all()


@pytest.mark.asyncio
async def test_mock_provider_stream():
    provider = MockProvider()
    config = LLMConfig()
    tokens = []
    async for token in provider.stream([Message(role="user", content="hi")], config):
        tokens.append(token)
    assert tokens == ["hello", "world"]


@pytest.mark.asyncio
async def test_mock_provider_complete():
    provider = MockProvider()
    config = LLMConfig()
    response = await provider.complete([Message(role="user", content="hi")], config)
    assert response.content == "hello world"
    assert response.input_tokens == 10


def test_provider_count_tokens():
    provider = MockProvider()
    assert provider.count_tokens("hello world") == 2


def test_cost_tracker_calculate():
    tracker = CostTracker()
    cost = tracker.calculate_cost("openai", "gpt-4o", 1000, 500)
    assert cost > 0


def test_cost_tracker_record_and_total():
    tracker = CostTracker()
    tracker.record_call(LLMCallRecord(
        provider="openai", model="gpt-4o",
        input_tokens=1000, output_tokens=500,
        cost_usd=0.0075, latency_ms=500,
        cached=False, fallback=False, agent="skeptic"
    ))
    tracker.record_call(LLMCallRecord(
        provider="openai", model="gpt-4o",
        input_tokens=2000, output_tokens=1000,
        cost_usd=0.015, latency_ms=800,
        cached=False, fallback=False, agent="visionary"
    ))
    assert tracker.get_run_cost() == pytest.approx(0.0225)


def test_cost_tracker_agent_breakdown():
    tracker = CostTracker()
    tracker.record_call(LLMCallRecord(
        provider="openai", model="gpt-4o",
        input_tokens=1000, output_tokens=500,
        cost_usd=0.01, latency_ms=500,
        cached=False, fallback=False, agent="skeptic"
    ))
    tracker.record_call(LLMCallRecord(
        provider="openai", model="gpt-4o",
        input_tokens=2000, output_tokens=1000,
        cost_usd=0.02, latency_ms=800,
        cached=False, fallback=False, agent="visionary"
    ))
    breakdown = tracker.get_agent_breakdown()
    assert breakdown["skeptic"] == pytest.approx(0.01)
    assert breakdown["visionary"] == pytest.approx(0.02)


def test_cost_tracker_budget_check():
    tracker = CostTracker()
    tracker.record_call(LLMCallRecord(
        provider="openai", model="gpt-4o",
        input_tokens=1000, output_tokens=500,
        cost_usd=5.0, latency_ms=500,
        cached=False, fallback=False, agent="skeptic"
    ))
    assert tracker.check_budget(10.0) is True  # Under budget
    assert tracker.check_budget(3.0) is False  # Over budget


def test_cost_tracker_unknown_model():
    tracker = CostTracker()
    cost = tracker.calculate_cost("openai", "unknown-model", 1000, 500)
    assert cost == 0.0  # Unknown models return 0
