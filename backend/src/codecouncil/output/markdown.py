"""Markdown RFC renderer."""

from __future__ import annotations

from datetime import datetime, timezone

from .base import RFCRenderer
from .action_items import extract_action_items
from .cost_report import generate_cost_report

_SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}


class MarkdownRenderer(RFCRenderer):
    def format_key(self) -> str:
        return "markdown"

    def render(self, state: dict) -> str:
        sections: list[str] = []
        sections.append(self._header(state))
        sections.append(self._executive_summary(state))
        sections.append(self._critical_findings(state))
        sections.append(self._proposals_and_votes(state))
        sections.append(self._dissent_blocks(state))
        sections.append(self._deadlocked_items(state))
        sections.append(self._action_items(state))
        sections.append(self._debate_appendix(state))
        sections.append(self._cost_summary(state))
        return "\n\n".join(s for s in sections if s.strip())

    # ------------------------------------------------------------------
    def _header(self, state: dict) -> str:
        repo_context = state.get("repo_context") or {}
        repo_name = repo_context.get("repo_name") or state.get("repo_url", "Unknown")
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        proposals = state.get("proposals", [])
        findings = state.get("findings", [])
        agents = sorted({p.get("author_agent", "") for p in proposals} | {f.get("agent", "") for f in findings} - {""})

        # Consensus score: fraction of proposals that passed
        passed = sum(1 for p in proposals if p.get("status", "").lower() == "passed")
        total = len(proposals) if proposals else 1
        consensus = round(passed / total, 2)

        cost = state.get("cost_total", 0.0)

        lines = [
            f"# RFC: {repo_name}",
            "",
            f"| Field | Value |",
            f"|-------|-------|",
            f"| **Repository** | `{repo_name}` |",
            f"| **Date** | {date} |",
            f"| **Agents** | {', '.join(agents) if agents else 'N/A'} |",
            f"| **Consensus Score** | {consensus:.0%} |",
            f"| **Total Cost** | ${cost:.4f} |",
        ]
        return "\n".join(lines)

    def _executive_summary(self, state: dict) -> str:
        rfc_content = state.get("rfc_content", "").strip()
        if rfc_content:
            return f"## Executive Summary\n\n{rfc_content}"

        findings = state.get("findings", [])
        proposals = state.get("proposals", [])
        critical = [f for f in findings if f.get("severity", "").upper() == "CRITICAL"]
        passed = [p for p in proposals if p.get("status", "").lower() == "passed"]

        lines = ["## Executive Summary", ""]
        lines.append(
            f"Analysis identified **{len(findings)} finding(s)** "
            f"({len(critical)} critical) across the codebase. "
            f"The council reviewed **{len(proposals)} proposal(s)**, "
            f"passing **{len(passed)}**."
        )
        return "\n".join(lines)

    def _critical_findings(self, state: dict) -> str:
        findings = state.get("findings", [])
        if not findings:
            return ""

        sorted_findings = sorted(
            findings,
            key=lambda f: _SEVERITY_ORDER.get(f.get("severity", "INFO").upper(), 99),
        )

        lines = ["## Critical Findings", ""]
        lines.append("| # | Severity | Agent | Finding | Implication |")
        lines.append("|---|----------|-------|---------|-------------|")
        for i, f in enumerate(sorted_findings, 1):
            severity = f.get("severity", "INFO").upper()
            agent = f.get("agent", "")
            content = f.get("content", "").replace("|", "\\|")
            implication = f.get("implication", "").replace("|", "\\|")
            lines.append(f"| {i} | **{severity}** | {agent} | {content} | {implication} |")

        return "\n".join(lines)

    def _proposals_and_votes(self, state: dict) -> str:
        proposals = state.get("proposals", [])
        votes = state.get("votes", [])
        if not proposals:
            return ""

        # Build vote lookup: proposal_id -> {agent: vote}
        vote_map: dict[str, dict[str, str]] = {}
        for v in votes:
            pid = v.get("proposal_id", "")
            agent = v.get("agent", "")
            vote_val = v.get("vote", "")
            if pid not in vote_map:
                vote_map[pid] = {}
            vote_map[pid][agent] = vote_val

        # Collect all agents across all votes
        all_agents = sorted({v.get("agent", "") for v in votes if v.get("agent")})

        lines = ["## Proposals", ""]

        # Build header row
        header_agents = " | ".join(f"**{a}**" for a in all_agents)
        lines.append(f"| # | Proposal | Status | {header_agents} | Result |" if all_agents else "| # | Proposal | Status | Result |")
        separator_agents = " | ".join("---" for _ in all_agents)
        lines.append(f"|---|----------|--------|{separator_agents + ' | ' if all_agents else ''}--------|")

        for p in proposals:
            pid = p.get("id", "")
            num = p.get("proposal_number", "?")
            title = p.get("title", "Untitled").replace("|", "\\|")
            status = p.get("status", "unknown").upper()
            agent_votes = vote_map.get(pid, {})

            vote_cells = " | ".join(agent_votes.get(a, "-") for a in all_agents)
            result = _result_badge(status)

            if all_agents:
                lines.append(f"| {num} | {title} | {status} | {vote_cells} | {result} |")
            else:
                lines.append(f"| {num} | {title} | {status} | {result} |")

        return "\n".join(lines)

    def _dissent_blocks(self, state: dict) -> str:
        votes = state.get("votes", [])
        no_votes = [v for v in votes if v.get("vote", "").upper() == "NO"]
        if not no_votes:
            return ""

        lines = ["## Dissent", ""]
        for v in no_votes:
            agent = v.get("agent", "unknown")
            rationale = v.get("rationale", "No rationale provided.")
            lines.append(f"### {agent} — NO")
            lines.append("")
            lines.append(f"> {rationale}")
            lines.append("")

        return "\n".join(lines)

    def _deadlocked_items(self, state: dict) -> str:
        deadlocked = [p for p in state.get("proposals", []) if p.get("status", "").lower() == "deadlocked"]
        if not deadlocked:
            return ""

        votes = state.get("votes", [])

        lines = ["## Deadlocked Items", ""]
        for p in deadlocked:
            pid = p.get("id", "")
            title = p.get("title", "Untitled")
            lines.append(f"### {title}")
            lines.append("")

            # Split votes into YES/NO positions
            proposal_votes = [v for v in votes if v.get("proposal_id") == pid]
            yes_votes = [v for v in proposal_votes if v.get("vote", "").upper() == "YES"]
            no_votes = [v for v in proposal_votes if v.get("vote", "").upper() == "NO"]

            lines.append("**For:**")
            for v in yes_votes:
                lines.append(f"- **{v.get('agent')}**: {v.get('rationale', '')}")
            lines.append("")
            lines.append("**Against:**")
            for v in no_votes:
                lines.append(f"- **{v.get('agent')}**: {v.get('rationale', '')}")
            lines.append("")

        return "\n".join(lines)

    def _action_items(self, state: dict) -> str:
        items = extract_action_items(state)
        if not items:
            return ""

        lines = ["## Action Items", ""]
        for item in items:
            source = f" _(from proposal {item.source_proposal[:8]}...)_" if item.source_proposal else ""
            breaking = " **[BREAKING]**" if item.breaking_change else ""
            lines.append(f"{item.number}. **{item.title}**{breaking} — Effort: `{item.effort}`{source}")

        return "\n".join(lines)

    def _debate_appendix(self, state: dict) -> str:
        rounds = state.get("debate_rounds", [])
        if not rounds:
            return ""

        lines = ["## Debate Appendix", ""]
        turn_count = 0
        max_turns = 5

        for round_data in rounds:
            round_num = round_data.get("round", "?")
            turns = round_data.get("turns", [])
            if not turns:
                continue
            lines.append(f"### Round {round_num}")
            lines.append("")
            for turn in turns:
                if turn_count >= max_turns:
                    break
                agent = turn.get("agent", "unknown")
                content = turn.get("content", "")
                action = turn.get("action", "")
                lines.append(f"**{agent}** _{action}_: {content}")
                lines.append("")
                turn_count += 1
            if turn_count >= max_turns:
                break

        return "\n".join(lines)

    def _cost_summary(self, state: dict) -> str:
        report = generate_cost_report(state)
        agents = report.get("agents", [])
        total = report.get("total", {})

        if not agents:
            return ""

        lines = ["## Cost Summary", ""]
        lines.append("| Agent | Provider | Model | Input Tokens | Output Tokens | Cost (USD) | Latency (ms) |")
        lines.append("|-------|----------|-------|-------------|--------------|------------|-------------|")

        for entry in agents:
            lines.append(
                f"| {entry['agent']} | {entry['provider']} | {entry['model']} "
                f"| {entry['input_tokens']:,} | {entry['output_tokens']:,} "
                f"| ${entry['cost_usd']:.4f} | {entry['latency_ms']} |"
            )

        lines.append(
            f"| **Total** | | | {total.get('input_tokens', 0):,} "
            f"| {total.get('output_tokens', 0):,} "
            f"| **${total.get('cost_usd', 0.0):.4f}** "
            f"| {total.get('latency_ms', 0)} |"
        )

        return "\n".join(lines)


def _result_badge(status: str) -> str:
    status_upper = status.upper()
    mapping = {
        "PASSED": "PASSED",
        "REJECTED": "REJECTED",
        "DEADLOCKED": "DEADLOCKED",
        "PENDING": "PENDING",
        "AMENDED": "AMENDED",
    }
    return mapping.get(status_upper, status_upper)
