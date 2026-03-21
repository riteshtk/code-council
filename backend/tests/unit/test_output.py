import pytest
from uuid import uuid4
from codecouncil.output.registry import RendererRegistry
from codecouncil.output.markdown import MarkdownRenderer
from codecouncil.output.json_renderer import JSONRenderer
from codecouncil.output.html import HTMLRenderer
from codecouncil.output.action_items import extract_action_items
from codecouncil.output.cost_report import generate_cost_report


def _make_state():
    run_id = str(uuid4())
    proposal_id = str(uuid4())
    return {
        "run_id": run_id,
        "repo_url": "https://github.com/test/repo",
        "config": {"council": {"max_rounds": 3}},
        "phase": "done",
        "repo_context": {"repo_name": "test/repo"},
        "findings": [
            {"id": str(uuid4()), "run_id": run_id, "agent": "archaeologist",
             "severity": "CRITICAL", "content": "Bus factor of 1", "implication": "Single point of failure", "scope": ""},
            {"id": str(uuid4()), "run_id": run_id, "agent": "skeptic",
             "severity": "HIGH", "content": "CVE in dependency", "implication": "Security risk", "scope": ""},
        ],
        "proposals": [
            {"id": proposal_id, "run_id": run_id, "proposal_number": 1, "version": 1,
             "title": "Add test coverage", "goal": "Improve quality", "effort": "S",
             "status": "passed", "author_agent": "visionary"},
            {"id": str(uuid4()), "run_id": run_id, "proposal_number": 2, "version": 1,
             "title": "Refactor DI module", "goal": "Reduce coupling", "effort": "L",
             "status": "deadlocked", "author_agent": "visionary"},
        ],
        "votes": [
            {"id": str(uuid4()), "run_id": run_id, "proposal_id": proposal_id,
             "agent": "archaeologist", "vote": "YES", "rationale": "Historical data supports this.", "confidence": 0.8},
            {"id": str(uuid4()), "run_id": run_id, "proposal_id": proposal_id,
             "agent": "skeptic", "vote": "YES", "rationale": "Low risk, high value.", "confidence": 0.9},
            {"id": str(uuid4()), "run_id": run_id, "proposal_id": proposal_id,
             "agent": "visionary", "vote": "YES", "rationale": "My proposal.", "confidence": 0.95},
        ],
        "debate_rounds": [
            {"round": 1, "turns": [
                {"agent": "visionary", "content": "I propose adding test coverage.", "action": "propose"},
                {"agent": "skeptic", "content": "Visionary, what's the scope?", "action": "challenge"},
            ]},
        ],
        "opening_statements": [],
        "rfc_content": "",
        "agent_memories": {},
        "events": [
            {"agent": "archaeologist", "event_type": "agent_speaking", "metadata": {
                "provider": "openai", "model": "gpt-4o", "input_tokens": 1000,
                "output_tokens": 500, "cost_usd": 0.01, "latency_ms": 1200}},
            {"agent": "skeptic", "event_type": "agent_speaking", "metadata": {
                "provider": "openai", "model": "gpt-4o", "input_tokens": 1500,
                "output_tokens": 800, "cost_usd": 0.02, "latency_ms": 1500}},
        ],
        "cost_total": 0.03,
        "human_review_pending": False,
        "cancelled": False,
    }


def test_registry_has_renderers():
    names = RendererRegistry.list_all()
    assert "markdown" in names
    assert "json" in names
    assert "html" in names


def test_markdown_render():
    renderer = MarkdownRenderer()
    state = _make_state()
    output = renderer.render(state)
    assert "# RFC:" in output or "# RFC" in output
    assert "test/repo" in output
    assert "Bus factor" in output
    assert "Add test coverage" in output
    assert "PASSED" in output or "passed" in output.lower()


def test_markdown_contains_all_sections():
    renderer = MarkdownRenderer()
    output = renderer.render(_make_state())
    # Check key section headers exist
    lower = output.lower()
    assert "finding" in lower
    assert "proposal" in lower
    assert "action" in lower


def test_json_render():
    renderer = JSONRenderer()
    state = _make_state()
    output = renderer.render(state)
    import json
    data = json.loads(output)
    assert "findings" in data
    assert "proposals" in data
    assert len(data["findings"]) == 2


def test_html_render():
    renderer = HTMLRenderer()
    state = _make_state()
    output = renderer.render(state)
    assert "<html" in output.lower()
    assert "test/repo" in output
    assert "Bus factor" in output


def test_action_items_from_passed():
    state = _make_state()
    items = extract_action_items(state)
    assert len(items) >= 1
    assert items[0].title == "Add test coverage"
    assert items[0].effort == "S"


def test_action_items_excludes_deadlocked():
    state = _make_state()
    items = extract_action_items(state)
    titles = [i.title for i in items]
    assert "Refactor DI module" not in titles


def test_cost_report():
    state = _make_state()
    report = generate_cost_report(state)
    assert "agents" in report
    assert "total" in report
    assert report["total"]["cost_usd"] == pytest.approx(0.03)


def test_markdown_format_key():
    assert MarkdownRenderer().format_key() == "markdown"

def test_json_format_key():
    assert JSONRenderer().format_key() == "json"

def test_html_format_key():
    assert HTMLRenderer().format_key() == "html"
