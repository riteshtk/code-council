"""Action item extraction from council state."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ActionItem:
    number: int
    title: str
    effort: str
    source_proposal: str | None = None
    breaking_change: bool = False


def extract_action_items(state: dict) -> list[ActionItem]:
    """Extract action items from passed proposals and critical findings."""
    items: list[ActionItem] = []
    counter = 1

    # From passed proposals
    for proposal in state.get("proposals", []):
        if proposal.get("status", "").lower() == "passed":
            items.append(
                ActionItem(
                    number=counter,
                    title=proposal.get("title", "Untitled"),
                    effort=proposal.get("effort", "M"),
                    source_proposal=proposal.get("id"),
                    breaking_change=proposal.get("breaking_change", False),
                )
            )
            counter += 1

    # From CRITICAL findings that need action
    for finding in state.get("findings", []):
        if finding.get("severity", "").upper() == "CRITICAL":
            title = f"Address: {finding.get('content', 'Critical finding')}"
            items.append(
                ActionItem(
                    number=counter,
                    title=title,
                    effort="M",
                    source_proposal=None,
                    breaking_change=False,
                )
            )
            counter += 1

    return items
