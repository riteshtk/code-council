"""Council simulation engine — runs as a background asyncio task."""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone


async def simulate_council_run(run: dict, runs_store: dict) -> None:
    """Simulate a full council run with realistic delays and data."""
    run_id = run["run_id"]
    repo_url = run["repo_url"]

    # Extract repo name from URL
    repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
    parts = repo_url.rstrip("/").split("/")
    repo_org = parts[-2] if len(parts) >= 2 else ""

    def emit_event(
        agent: str,
        event_type: str,
        content: str,
        phase: str,
        **extra: object,
    ) -> dict:
        event = {
            "id": str(uuid.uuid4()),
            "event_id": str(uuid.uuid4()),
            "run_id": run_id,
            "agent": agent,
            "agent_id": agent,
            "type": event_type,
            "event_type": event_type,
            "content": content,
            "phase": phase,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "sequence": len(run["events"]) + 1,
            "structured": extra.get("structured", {}),
            "payload": extra.get("structured", {}),
            "metadata": {
                "provider": "openai",
                "model": "gpt-4o",
                "input_tokens": 500,
                "output_tokens": 200,
                "cost_usd": 0.005,
                "latency_ms": 1200,
                "cached": False,
                "fallback": False,
            },
        }
        run["events"].append(event)
        return event

    try:
        # ── Phase 1: INGESTION ──────────────────────────────────────────
        run["status"] = "running"
        run["phase"] = "ingestion"
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        emit_event("system", "phase_started", f"Ingesting repository: {repo_url}", "ingestion")
        await asyncio.sleep(1.5)
        emit_event(
            "system",
            "phase_completed",
            f"Repository {repo_name} ingested: 47 files, 12,340 LOC",
            "ingestion",
            structured={
                "files": 47,
                "loc": 12340,
                "languages": {"Python": 8500, "TypeScript": 3200, "YAML": 640},
            },
        )

        # ── Phase 2: ANALYSIS ──────────────────────────────────────────
        run["phase"] = "analysis"
        emit_event("system", "phase_started", "Analysis phase: agents running in parallel", "analysis")

        await asyncio.sleep(0.5)
        emit_event("archaeologist", "agent_thinking", "Archaeologist activated — scanning history", "analysis")
        emit_event("skeptic", "agent_thinking", "Skeptic activated — scanning for risks", "analysis")
        emit_event("visionary", "agent_thinking", "Visionary activated — reading architecture", "analysis")

        await asyncio.sleep(1.5)

        # Findings
        findings = [
            {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "agent": "archaeologist",
                "agent_id": "archaeologist",
                "severity": "critical",
                "title": f"Bus factor of 1 in {repo_name}",
                "description": f"Bus factor of 1 detected in core modules of {repo_name}. 82% of commits from single contributor.",
                "content": f"Bus factor of 1 detected in core modules of {repo_name}. 82% of commits from single contributor.",
                "implication": "A single departure would leave critical subsystems without institutional knowledge.",
                "scope": "repository",
                "phase": "analysis",
                "tags": ["bus-factor", "risk"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "agent": "archaeologist",
                "agent_id": "archaeologist",
                "severity": "high",
                "title": "23 unresolved TODOs",
                "description": f"23 unresolved TODOs accumulated over 18+ months in {repo_name}.",
                "content": f"23 unresolved TODOs accumulated over 18+ months in {repo_name}.",
                "implication": "Technical debt accumulation erodes developer trust.",
                "scope": "repository",
                "phase": "analysis",
                "tags": ["tech-debt", "todos"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "agent": "archaeologist",
                "agent_id": "archaeologist",
                "severity": "medium",
                "title": "High config file churn",
                "description": "File churn rate of 67% on core configuration files in the last 90 days.",
                "content": "File churn rate of 67% on core configuration files in the last 90 days.",
                "implication": "High churn suggests instability in foundational code.",
                "scope": "config/",
                "phase": "analysis",
                "tags": ["churn", "config"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "agent": "skeptic",
                "agent_id": "skeptic",
                "severity": "high",
                "title": "No automated test suite",
                "description": "No automated test suite detected. Test-to-source file ratio is 0.0.",
                "content": "No automated test suite detected. Test-to-source file ratio is 0.0.",
                "implication": "Changes cannot be validated automatically, increasing regression risk.",
                "scope": "repository",
                "phase": "analysis",
                "tags": ["testing", "risk"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "agent": "skeptic",
                "agent_id": "skeptic",
                "severity": "medium",
                "title": "3 CVE vulnerabilities",
                "description": "3 dependencies have known CVEs flagged by OSV database.",
                "content": "3 dependencies have known CVEs flagged by OSV database.",
                "implication": "Potential security vulnerabilities in production.",
                "scope": "dependencies",
                "phase": "analysis",
                "tags": ["security", "cve"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
        run["findings"] = findings

        for f in findings:
            emit_event(
                f["agent"],
                "finding_emitted",
                f"[{f['severity'].upper()}] {f['content']}",
                "analysis",
                structured=f,
            )

        await asyncio.sleep(1)
        emit_event("system", "phase_completed", f"Analysis complete: {len(findings)} findings", "analysis")

        # ── Phase 3: DEBATE (opening + debate rounds) ──────────────────
        run["phase"] = "debate"
        emit_event("system", "phase_started", "Debate phase: Adversarial topology, max 3 rounds", "debate")

        await asyncio.sleep(0.8)
        emit_event(
            "archaeologist",
            "agent_response",
            f"This repository has survived 14 months of active development with a bus factor of 1. "
            f"The commit history reveals a pattern of concentrated ownership — 82% of changes authored by a single contributor. "
            f"I have identified 23 unresolved TODOs, the oldest dating back 18 months. Configuration files show 67% churn.",
            "debate",
        )

        await asyncio.sleep(0.6)
        emit_event(
            "skeptic",
            "agent_response",
            f"My primary concern is the complete absence of automated tests. Without test coverage, "
            f"every change is a gamble. Additionally, 3 dependencies carry known CVEs. "
            f"The blast radius of any refactoring is unconstrained.",
            "debate",
        )

        await asyncio.sleep(0.6)
        emit_event(
            "visionary",
            "agent_response",
            f"Despite these concerns, {repo_name} has a clear bounded context structure that could be formalized. "
            f"I see opportunities to extract reusable modules and establish clear API boundaries. "
            f"The architecture wants to evolve — it just needs guidance.",
            "debate",
        )

        # Proposals
        proposals = [
            {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "proposal_number": 1,
                "version": 1,
                "title": "Add comprehensive test suite",
                "description": "Establish test coverage baseline to enable safe refactoring.",
                "goal": "Establish test coverage baseline",
                "effort": "M",
                "status": "pending",
                "agent_id": "visionary",
                "author_agent": "visionary",
                "breaking_change": False,
                "finding_ids": [findings[3]["id"]],
                "votes": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "proposal_number": 2,
                "version": 1,
                "title": "Upgrade vulnerable dependencies",
                "description": "Patch 3 known CVEs in project dependencies.",
                "goal": "Patch 3 known CVEs",
                "effort": "S",
                "status": "pending",
                "agent_id": "skeptic",
                "author_agent": "skeptic",
                "breaking_change": False,
                "finding_ids": [findings[4]["id"]],
                "votes": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "proposal_number": 3,
                "version": 1,
                "title": "Extract core module boundaries",
                "description": "Reduce coupling and improve maintainability through module extraction.",
                "goal": "Reduce coupling and improve maintainability",
                "effort": "L",
                "status": "pending",
                "agent_id": "visionary",
                "author_agent": "visionary",
                "breaking_change": True,
                "finding_ids": [findings[0]["id"], findings[2]["id"]],
                "votes": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        ]
        run["proposals"] = proposals

        await asyncio.sleep(0.5)
        emit_event(
            "visionary",
            "proposal_created",
            f"[PROPOSAL] Title: {proposals[0]['title']}\nGoal: {proposals[0]['goal']}\nEffort: {proposals[0]['effort']}",
            "debate",
            structured=proposals[0],
        )

        await asyncio.sleep(0.5)
        emit_event(
            "skeptic",
            "proposal_created",
            f"[PROPOSAL] Title: {proposals[1]['title']}\nGoal: {proposals[1]['goal']}\nEffort: {proposals[1]['effort']}",
            "debate",
            structured=proposals[1],
        )

        await asyncio.sleep(0.5)
        emit_event(
            "visionary",
            "proposal_created",
            f"[PROPOSAL] Title: {proposals[2]['title']}\nGoal: {proposals[2]['goal']}\nEffort: {proposals[2]['effort']}",
            "debate",
            structured=proposals[2],
        )

        # Round 1: Skeptic challenges
        await asyncio.sleep(0.8)
        emit_event(
            "skeptic",
            "agent_response",
            "Visionary, your Proposal 3 to extract module boundaries is ambitious but premature. "
            "With zero test coverage, any refactoring is flying blind. The Archaeologist's data shows "
            "this repo has already survived 14 months — rushing a major restructure risks breaking what works. "
            "I propose we add tests FIRST (Proposal 1), then consider structural changes.",
            "debate",
        )

        # Archaeologist supports with evidence
        await asyncio.sleep(0.6)
        emit_event(
            "archaeologist",
            "agent_response",
            "Confirming Skeptic's concern. The commit history shows 2 previous attempts at restructuring "
            "(commits 7 and 11 months ago) that both increased complexity without reducing churn. "
            "Evidence suggests incremental improvement outperforms big-bang refactors in this codebase.",
            "debate",
        )

        # Visionary revises
        await asyncio.sleep(0.6)
        proposals[2]["version"] = 2
        proposals[2]["title"] = "Extract core module boundaries (phased, post-tests)"
        proposals[2]["status"] = "amended"
        proposals[2]["updated_at"] = datetime.now(timezone.utc).isoformat()
        emit_event(
            "visionary",
            "agent_response",
            "Skeptic, your point about test coverage first is valid. I'm revising Proposal 3 to be phased: "
            "module extraction happens AFTER Proposal 1 (tests) is complete. This de-risks the refactor. "
            "Does this address your objection?",
            "debate",
        )

        await asyncio.sleep(0.5)
        emit_event(
            "skeptic",
            "agent_response",
            "The phased approach is acceptable. I withdraw my objection to Proposal 3 contingent on "
            "Proposal 1 being completed first. The dependency is critical.",
            "debate",
        )

        run["debate_rounds"] = [
            {
                "round": 1,
                "turns": [
                    {"agent": "visionary", "action": "propose", "content": proposals[0]["title"]},
                    {"agent": "skeptic", "action": "propose", "content": proposals[1]["title"]},
                    {"agent": "visionary", "action": "propose", "content": proposals[2]["title"]},
                    {"agent": "skeptic", "action": "challenge", "content": "Proposal 3 premature without tests"},
                    {"agent": "archaeologist", "action": "evidence", "content": "Prior restructures increased complexity"},
                    {"agent": "visionary", "action": "revision", "content": "Phased approach post-tests"},
                    {"agent": "skeptic", "action": "response", "content": "Phased approach acceptable"},
                ],
            },
        ]

        emit_event("system", "phase_completed", "Debate complete: 3 proposals, 1 revised", "debate")

        # ── Phase 4: VOTING ────────────────────────────────────────────
        run["phase"] = "synthesis"
        emit_event("system", "phase_started", "Voting phase", "synthesis")

        await asyncio.sleep(0.5)

        votes: list[dict] = []

        # Vote on P1: Add tests — unanimous YES
        for agent in ["archaeologist", "skeptic", "visionary"]:
            confidence = 0.95 if agent == "skeptic" else 0.85
            rationale = "Non-negotiable. Must have tests." if agent == "skeptic" else "Test coverage is foundational."
            v = {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "proposal_id": proposals[0]["id"],
                "agent": agent,
                "agent_id": agent,
                "vote": "YES",
                "vote_type": "approve",
                "rationale": rationale,
                "reasoning": rationale,
                "confidence": confidence,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            votes.append(v)
            proposals[0].setdefault("votes", []).append(v)
            emit_event(agent, "vote_cast", f"[VOTE:YES] on Proposal 1. Confidence: {confidence}", "synthesis", structured=v)
            await asyncio.sleep(0.3)
        proposals[0]["status"] = "accepted"

        # Vote on P2: Upgrade deps — unanimous YES
        for agent in ["archaeologist", "skeptic", "visionary"]:
            v = {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "proposal_id": proposals[1]["id"],
                "agent": agent,
                "agent_id": agent,
                "vote": "YES",
                "vote_type": "approve",
                "rationale": "CVE patches are low-risk, high-value.",
                "reasoning": "CVE patches are low-risk, high-value.",
                "confidence": 0.9,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            votes.append(v)
            proposals[1].setdefault("votes", []).append(v)
            emit_event(agent, "vote_cast", f"[VOTE:YES] on Proposal 2. Confidence: {v['confidence']}", "synthesis", structured=v)
            await asyncio.sleep(0.3)
        proposals[1]["status"] = "accepted"

        # Vote on P3: Extract modules — 2 YES, 1 conditional YES
        for agent in ["archaeologist", "visionary"]:
            rationale = "Phased approach is sound." if agent == "visionary" else "Historical patterns support incremental extraction."
            v = {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "proposal_id": proposals[2]["id"],
                "agent": agent,
                "agent_id": agent,
                "vote": "YES",
                "vote_type": "approve",
                "rationale": rationale,
                "reasoning": rationale,
                "confidence": 0.7,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            votes.append(v)
            proposals[2].setdefault("votes", []).append(v)
            emit_event(agent, "vote_cast", f"[VOTE:YES] on Proposal 3 (v2). Confidence: {v['confidence']}", "synthesis", structured=v)
            await asyncio.sleep(0.3)

        # Skeptic conditional YES
        v = {
            "id": str(uuid.uuid4()),
            "run_id": run_id,
            "proposal_id": proposals[2]["id"],
            "agent": "skeptic",
            "agent_id": "skeptic",
            "vote": "YES",
            "vote_type": "approve",
            "rationale": "Conditional YES: only after Proposal 1 (tests) is complete. My vote flips to NO if sequencing is not enforced.",
            "reasoning": "Conditional YES: only after Proposal 1 (tests) is complete. My vote flips to NO if sequencing is not enforced.",
            "confidence": 0.6,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        votes.append(v)
        proposals[2].setdefault("votes", []).append(v)
        emit_event("skeptic", "vote_cast", f"[VOTE:YES] on Proposal 3 (conditional). Confidence: {v['confidence']}", "synthesis", structured=v)
        proposals[2]["status"] = "accepted"

        run["votes"] = votes
        emit_event("system", "phase_completed", "Voting complete: 3 passed, 0 failed, 0 deadlocked", "synthesis")

        # ── Phase 5: OUTPUT (RFC synthesis) ────────────────────────────
        run["phase"] = "output"
        emit_event("system", "phase_started", "Scribe synthesizing RFC", "output")
        emit_event("scribe", "agent_thinking", "Compiling council proceedings into RFC", "output")

        await asyncio.sleep(1.5)

        rfc_content = f"""# RFC: {repo_org}/{repo_name} Codebase Analysis

**Date:** {datetime.now(timezone.utc).strftime('%B %d, %Y')}
**Council:** Archaeologist, Skeptic, Visionary, Scribe
**Topology:** Adversarial | **Rounds:** 1 | **Consensus:** 100%

## Executive Summary

{repo_name} is an actively maintained repository with clear purpose but significant operational risks. The council identified {len(findings)} findings including a critical bus factor issue and absence of automated tests. Three proposals were unanimously passed, with a phased approach recommended: tests first, dependency patches second, structural improvements third.

## Critical Findings

1. **[CRITICAL] Bus Factor of 1** — 82% of commits from single contributor. Institutional knowledge concentrated.
2. **[HIGH] Zero Test Coverage** — No automated test suite. Changes cannot be validated.
3. **[HIGH] 23 Stale TODOs** — Accumulated over 18 months. Technical promises unfulfilled.
4. **[MEDIUM] 3 CVE Vulnerabilities** — Known security issues in dependencies.
5. **[MEDIUM] High Config Churn** — 67% churn rate on configuration files.

## Proposals & Votes

### P-1: Add Comprehensive Test Suite [PASSED 3-0]
- Archaeologist: YES (0.85) — "Test coverage is foundational."
- Skeptic: YES (0.95) — "Non-negotiable. Must have tests."
- Visionary: YES (0.85) — "Test coverage is foundational."

### P-2: Upgrade Vulnerable Dependencies [PASSED 3-0]
- All agents: YES (0.90) — "CVE patches are low-risk, high-value."

### P-3-v2: Extract Core Module Boundaries (Phased) [PASSED 3-0]
- Visionary: YES (0.70) — "Phased approach is sound."
- Archaeologist: YES (0.70) — "Historical patterns support incremental extraction."
- **Skeptic: YES (0.60) — CONDITIONAL** — "Only after P-1 is complete. Vote flips to NO if sequencing not enforced."

## Action Items

1. **[Effort: M]** Add comprehensive test suite — establish baseline coverage (from P-1)
2. **[Effort: S]** Upgrade 3 vulnerable dependencies to patched versions (from P-2)
3. **[Effort: L]** Extract core module boundaries with phased approach, post-tests (from P-3-v2) — Breaking change

## Cost Summary

| Agent | Provider | Tokens | Cost |
|-------|----------|--------|------|
| Archaeologist | OpenAI GPT-4o | ~2,400 | $0.02 |
| Skeptic | OpenAI GPT-4o | ~3,100 | $0.03 |
| Visionary | OpenAI GPT-4o | ~2,800 | $0.02 |
| Scribe | OpenAI GPT-4o | ~1,500 | $0.01 |
| **Total** | | **~9,800** | **$0.08** |
"""
        run["rfc_content"] = rfc_content
        emit_event("scribe", "agent_response", "RFC synthesis complete", "output")
        emit_event("system", "phase_completed", "RFC finalized", "output")

        # ── Phase 6: DONE ──────────────────────────────────────────────
        run["phase"] = "output"
        run["status"] = "completed"
        run["cost_usd"] = 0.08
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        emit_event(
            "system",
            "run_completed",
            f"Council run complete. {len(proposals)} proposals passed. Consensus: 100%",
            "output",
        )

    except Exception as e:
        run["status"] = "failed"
        run["phase"] = "output"
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        emit_event("system", "run_failed", f"Run failed: {str(e)}", "output")
