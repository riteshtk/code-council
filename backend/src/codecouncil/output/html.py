"""HTML RFC renderer using Jinja2."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .base import RFCRenderer
from .action_items import extract_action_items
from .cost_report import generate_cost_report

_TEMPLATES_DIR = Path(__file__).parent / "templates"
_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


class HTMLRenderer(RFCRenderer):
    def format_key(self) -> str:
        return "html"

    def render(self, state: dict) -> str:
        env = Environment(
            loader=FileSystemLoader(str(_TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "j2"]),
        )
        template = env.get_template("rfc.html.j2")

        repo_context = state.get("repo_context") or {}
        repo_name = repo_context.get("repo_name") or state.get("repo_url", "Unknown")

        proposals = state.get("proposals", [])
        findings = state.get("findings", [])
        votes = state.get("votes", [])

        # Collect all unique agents
        all_agents = sorted({v.get("agent", "") for v in votes if v.get("agent")})

        # Build vote_map: proposal_id -> {agent: vote_value}
        vote_map: dict[str, dict[str, str]] = {}
        for v in votes:
            pid = v.get("proposal_id", "")
            agent = v.get("agent", "")
            vote_map.setdefault(pid, {})[agent] = v.get("vote", "-")

        # Compute consensus
        passed = sum(1 for p in proposals if p.get("status", "").lower() == "passed")
        total = len(proposals) if proposals else 1
        consensus_score = passed / total

        # Annotate findings with sort key
        annotated_findings = []
        for f in sorted(
            findings,
            key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "INFO").upper(), 99),
        ):
            af = dict(f)
            af["severity_order"] = _SEVERITY_ORDER.get(f.get("severity", "INFO").upper(), 99)
            annotated_findings.append(af)

        action_items = [
            {
                "number": item.number,
                "title": item.title,
                "effort": item.effort,
                "source_proposal": item.source_proposal,
                "breaking_change": item.breaking_change,
            }
            for item in extract_action_items(state)
        ]

        cost_report = generate_cost_report(state)

        context = {
            "repo_name": repo_name,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "agents": sorted(
                {p.get("author_agent", "") for p in proposals}
                | {f.get("agent", "") for f in findings} - {""}
            ),
            "consensus_score": consensus_score,
            "cost_total": state.get("cost_total", 0.0),
            "rfc_content": state.get("rfc_content", ""),
            "findings": annotated_findings,
            "proposals": proposals,
            "votes": votes,
            "all_agents": all_agents,
            "vote_map": vote_map,
            "debate_rounds": state.get("debate_rounds", []),
            "action_items": action_items,
            "cost_report": cost_report,
        }

        return template.render(**context)
