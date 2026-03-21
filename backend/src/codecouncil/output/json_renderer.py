"""JSON RFC renderer."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from .base import RFCRenderer
from .action_items import extract_action_items
from .cost_report import generate_cost_report


class JSONRenderer(RFCRenderer):
    def format_key(self) -> str:
        return "json"

    def render(self, state: dict) -> str:
        repo_context = state.get("repo_context") or {}
        repo_name = repo_context.get("repo_name") or state.get("repo_url", "Unknown")

        proposals = state.get("proposals", [])
        votes = state.get("votes", [])
        findings = state.get("findings", [])

        passed = sum(1 for p in proposals if p.get("status", "").lower() == "passed")
        total = len(proposals) if proposals else 1
        consensus = round(passed / total, 4)

        # Enrich proposals with their votes
        vote_map: dict[str, list[dict]] = {}
        for v in votes:
            pid = v.get("proposal_id", "")
            vote_map.setdefault(pid, []).append(v)

        enriched_proposals = []
        for p in proposals:
            ep = dict(p)
            ep["votes"] = vote_map.get(p.get("id", ""), [])
            enriched_proposals.append(ep)

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

        output = {
            "meta": {
                "run_id": state.get("run_id"),
                "repo_name": repo_name,
                "repo_url": state.get("repo_url"),
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "consensus_score": consensus,
                "cost_total_usd": state.get("cost_total", 0.0),
                "phase": state.get("phase"),
            },
            "findings": findings,
            "proposals": enriched_proposals,
            "debate_rounds": state.get("debate_rounds", []),
            "action_items": action_items,
            "cost_report": cost_report,
        }

        return json.dumps(output, indent=2, default=str)
