"""Real council analysis pipeline — clones repo, calls OpenAI, generates RFC."""
from __future__ import annotations

import asyncio
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path

from openai import AsyncOpenAI

# ── Model configuration ──
# ── Model configuration ──
# GPT-5.4 = most capable, 128k context, best reasoning
# GPT-4.1-mini = fast + cheap for simple structured tasks
MODEL_HEAVY = "gpt-5.4"         # Best: analysis, debate, RFC generation
MODEL_LIGHT = "gpt-4.1-mini"    # Fast: voting, short structured responses
MAX_TOKENS_ANALYSIS = 8192      # Agent analysis — detailed findings
MAX_TOKENS_DEBATE = 4096        # Debate — thorough argumentation
MAX_TOKENS_VOTE = 500           # Vote — structured response
MAX_TOKENS_RFC = 16384          # RFC — comprehensive institutional document

# GPT-5.x uses max_completion_tokens, GPT-4.x uses max_tokens
# We handle both via a helper
def _model_kwargs(model: str, max_tokens: int) -> dict:
    """Return the right token-limit kwarg for the model family."""
    if model.startswith("gpt-5"):
        return {"max_completion_tokens": max_tokens}
    return {"max_tokens": max_tokens}


def _load_api_key() -> str:
    """Load OpenAI API key from environment or project root .env file."""
    key = os.environ.get("OPENAI_API_KEY", "")
    if not key:
        env_path = Path(__file__).parents[4] / ".env"  # project root .env
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("OPENAI_API_KEY="):
                    key = line.split("=", 1)[1].strip()
                    break
    return key


# Extension -> language mapping
_EXT_LANG: dict[str, str] = {
    ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript", ".tsx": "TypeScript",
    ".jsx": "JavaScript", ".go": "Go", ".rs": "Rust", ".java": "Java",
    ".rb": "Ruby", ".c": "C", ".cpp": "C++", ".cs": "C#", ".swift": "Swift",
    ".kt": "Kotlin", ".sh": "Shell", ".yaml": "YAML", ".yml": "YAML",
    ".json": "JSON", ".md": "Markdown", ".toml": "TOML", ".cfg": "Config",
    ".html": "HTML", ".css": "CSS", ".sql": "SQL",
}

_EXCLUDE_DIRS: set[str] = {
    ".git", "node_modules", ".venv", "__pycache__", "dist", "build",
    ".next", ".cache", "vendor", ".tox", ".mypy_cache", ".ruff_cache",
}


async def _persist_event(session_factory, event_dict: dict) -> None:
    """Persist a single event to DB. Best-effort — never crashes the pipeline."""
    try:
        async with session_factory() as db:
            from codecouncil.db.repositories import EventRepository
            repo = EventRepository(db)
            await repo.create_event({
                "id": uuid.UUID(event_dict["event_id"]),
                "run_id": uuid.UUID(event_dict["run_id"]),
                "sequence": event_dict["sequence"],
                "agent": event_dict["agent"],
                "event_type": event_dict["event_type"],
                "phase": event_dict.get("phase", ""),
                "round": event_dict.get("round"),
                "content": event_dict.get("content", ""),
                "structured": event_dict.get("structured", {}),
                "provider": event_dict.get("metadata", {}).get("provider"),
                "model": event_dict.get("metadata", {}).get("model"),
                "input_tokens": event_dict.get("metadata", {}).get("input_tokens", 0),
                "output_tokens": event_dict.get("metadata", {}).get("output_tokens", 0),
                "cost_usd": event_dict.get("metadata", {}).get("cost_usd", 0),
                "latency_ms": event_dict.get("metadata", {}).get("latency_ms", 0),
                "cached": event_dict.get("metadata", {}).get("cached", False),
            })
            await db.commit()
    except Exception as exc:
        import logging
        logging.getLogger("codecouncil.pipeline").warning("DB persist failed: %s", exc)


async def _update_run_phase(session_factory, run_id: str, status: str, phase: str) -> None:
    """Update run status/phase in DB. Best-effort."""
    try:
        async with session_factory() as db:
            from codecouncil.db.repositories import RunRepository
            await RunRepository(db).update_run_status(uuid.UUID(run_id), status, phase)
            await db.commit()
    except Exception as exc:
        import logging
        logging.getLogger("codecouncil.pipeline").warning("DB persist failed: %s", exc)


async def llm_call(
    client: AsyncOpenAI,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int,
    temperature: float = 0.3,
) -> tuple[str, int, int]:
    """Make an LLM call with separate system and user messages.

    Returns (text, input_tokens, output_tokens).
    """
    response = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        **_model_kwargs(model, max_tokens),
        temperature=temperature,
    )
    text = response.choices[0].message.content or ""
    tokens_in = response.usage.prompt_tokens if response.usage else 0
    tokens_out = response.usage.completion_tokens if response.usage else 0
    return text, tokens_in, tokens_out


async def run_real_council(run: dict, runs_store: dict, *, session_factory=None, agent_registry=None) -> None:
    """Run a REAL council analysis on a GitHub repository."""
    run_id = run["run_id"]
    repo_url = run["repo_url"]
    api_key = _load_api_key()

    def emit(
        agent: str,
        event_type: str,
        content: str,
        phase: str,
        **extra: object,
    ) -> None:
        event_id = str(uuid.uuid4())
        event = {
            "id": event_id,
            "event_id": event_id,
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
            "metadata": extra.get("metadata", {}),
        }
        run["events"].append(event)
        run["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Persist event to DB immediately (best-effort)
        if session_factory:
            asyncio.ensure_future(_persist_event(session_factory, event))

    if not api_key:
        run["status"] = "failed"
        run["phase"] = "error"
        emit("system", "run_failed", "No OpenAI API key configured", "error")
        if session_factory:
            async with session_factory() as _db:
                from codecouncil.db.repositories import RunRepository as _RR
                await _RR(_db).update_run_status(uuid.UUID(run_id), "failed", "error")
                await _db.commit()
        return

    client = AsyncOpenAI(api_key=api_key)

    tmpdir: str | None = None
    try:
        # =================================================================
        # PHASE 1: INGESTION — Clone repo & scan files
        # =================================================================
        run["status"] = "running"
        run["phase"] = "ingesting"
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        emit("system", "phase_started", f"Cloning repository: {repo_url}", "ingesting")

        # DB checkpoint: mark running
        if session_factory:
            await _update_run_phase(session_factory, run_id, "running", "ingesting")

        tmpdir = tempfile.mkdtemp(prefix="codecouncil_")
        clone_url = repo_url if repo_url.endswith(".git") else repo_url + ".git"

        proc = await asyncio.create_subprocess_exec(
            "git", "clone", "--depth", "50", clone_url, tmpdir + "/repo",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()

        if proc.returncode != 0:
            emit("system", "run_failed", f"Failed to clone: {stderr.decode()[:200]}", "ingesting")
            run["status"] = "failed"
            run["phase"] = "error"
            return

        repo_path = Path(tmpdir) / "repo"

        # Scan file tree
        files: list[dict] = []
        total_loc = 0
        languages: dict[str, int] = {}

        for f in repo_path.rglob("*"):
            if f.is_dir():
                continue
            rel = f.relative_to(repo_path)
            if any(part in _EXCLUDE_DIRS for part in rel.parts):
                continue
            try:
                content_text = f.read_text(errors="ignore")
                loc = len(content_text.splitlines())
            except Exception as exc:
                import logging
                logging.getLogger("codecouncil.pipeline").warning("DB persist failed: %s", exc)
                loc = 0
            lang = _EXT_LANG.get(f.suffix.lower(), "Other")
            languages[lang] = languages.get(lang, 0) + loc
            total_loc += loc
            try:
                size = f.stat().st_size
            except Exception as exc:
                import logging
                logging.getLogger("codecouncil.pipeline").warning("DB persist failed: %s", exc)
                size = 0
            files.append({"path": str(rel), "language": lang, "loc": loc, "size": size})

        files.sort(key=lambda x: x["loc"], reverse=True)

        # Git log
        proc2 = await asyncio.create_subprocess_exec(
            "git", "-C", str(repo_path), "log", "--oneline", "-50", "--format=%H|%an|%s",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        log_out, _ = await proc2.communicate()
        commits: list[dict] = []
        authors: set[str] = set()
        for line in log_out.decode().strip().splitlines():
            parts = line.split("|", 2)
            if len(parts) >= 3:
                commits.append({"hash": parts[0][:8], "author": parts[1], "message": parts[2]})
                authors.add(parts[1])

        repo_name = repo_url.rstrip("/").split("/")[-1].replace(".git", "")
        repo_org = repo_url.rstrip("/").split("/")[-2] if repo_url.count("/") >= 4 else ""

        # Build context summary for agents
        top_files_text = "\n".join(
            [f"  {f['path']} ({f['language']}, {f['loc']} LOC)" for f in files[:30]]
        )
        lang_summary = ", ".join(
            [f"{k}: {v} LOC" for k, v in sorted(languages.items(), key=lambda x: -x[1])[:8]]
        )
        recent_commits = "\n".join(
            [f"  {c['hash']} ({c['author']}): {c['message']}" for c in commits[:15]]
        )

        context = (
            f"Repository: {repo_org}/{repo_name}\n"
            f"URL: {repo_url}\n"
            f"Total files: {len(files)}\n"
            f"Total LOC: {total_loc}\n"
            f"Languages: {lang_summary}\n"
            f"Unique authors: {len(authors)} ({', '.join(list(authors)[:5])})\n"
            f"Recent commits ({len(commits)} total):\n{recent_commits}\n\n"
            f"Top files by LOC:\n{top_files_text}\n"
        )

        emit(
            "system", "ingest_completed",
            f"Repository cloned: {len(files)} files, {total_loc:,} LOC, "
            f"{len(commits)} commits, {len(authors)} authors",
            "ingesting",
            structured={"files": len(files), "loc": total_loc, "languages": languages, "authors": len(authors)},
        )

        # Read key files for deeper context
        key_file_contents = ""
        for name in ["README.md", "readme.md", "README.rst", "README"]:
            p = repo_path / name
            if p.exists():
                try:
                    key_file_contents += f"\n--- README ---\n{p.read_text(errors='ignore')[:4000]}\n"
                except Exception as exc:
                    import logging
                    logging.getLogger("codecouncil.pipeline").warning("DB persist failed: %s", exc)
                break

        for manifest in [
            "pyproject.toml", "package.json", "go.mod", "Cargo.toml",
            "requirements.txt", "Gemfile", "setup.py", "setup.cfg",
        ]:
            mp = repo_path / manifest
            if mp.exists():
                try:
                    key_file_contents += f"\n--- {manifest} ---\n{mp.read_text(errors='ignore')[:3000]}\n"
                except Exception as exc:
                    import logging
                    logging.getLogger("codecouncil.pipeline").warning("DB persist failed: %s", exc)

        full_context = context + key_file_contents

        # =================================================================
        # PHASE 2: ANALYSIS — Each agent analyses independently
        # =================================================================
        run["phase"] = "analysing"
        if session_factory:
            await _update_run_phase(session_factory, run_id, "running", "analysing")
        emit("system", "phase_started", "Analysis phase: agents running in parallel", "analysing")

        # Agent registry is required — no fallback to hardcoded prompts
        if not agent_registry:
            raise RuntimeError("Agent registry is required — cannot run without agent definitions")

        analysts = agent_registry.list_analysts()

        async def _run_agent_analysis(agent_def):
            agent_name = agent_def.handle
            emit(agent_name, "agent_thinking", f"{agent_name.capitalize()} analyzing repository...", "analysing")
            try:
                system = agent_def.build_system_prompt(memory_context="")
                user = agent_def.get_prompt("analyze", repo_context=full_context)
                if not user:
                    emit(agent_name, "agent_response", "No analyze prompt configured", "analysing")
                    return [], ""

                text, tokens_in, tokens_out = await llm_call(
                    client, system, user, MODEL_HEAVY,
                    agent_def.max_tokens, agent_def.temperature,
                )
                cost = round((tokens_in * 2.5 + tokens_out * 10) / 1_000_000, 4)

                emit(
                    agent_name, "agent_response", text, "analysing",
                    metadata={
                        "provider": "openai", "model": MODEL_HEAVY,
                        "input_tokens": tokens_in, "output_tokens": tokens_out,
                        "cost_usd": cost,
                    },
                )

                # Parse findings
                findings: list[dict] = []
                for match in re.finditer(
                    r'\[FINDING:\s*(CRITICAL|HIGH|MEDIUM|INFO)\]\s*(.*?)(?=\[FINDING:|$)',
                    text, re.DOTALL,
                ):
                    severity = match.group(1).lower()
                    raw = match.group(2).strip()
                    parts = raw.split("Implication:", 1)
                    finding = {
                        "id": str(uuid.uuid4()),
                        "run_id": run_id,
                        "agent": agent_name,
                        "agent_id": agent_name,
                        "severity": severity,
                        "title": parts[0].strip()[:200],
                        "content": parts[0].strip(),
                        "description": parts[0].strip(),
                        "implication": parts[1].strip() if len(parts) > 1 else "",
                        "scope": "repository",
                        "phase": "analysis",
                        "tags": [],
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    findings.append(finding)
                    emit(
                        agent_name, "finding_emitted",
                        f"[{severity.upper()}] {parts[0].strip()}",
                        "analysing", structured=finding,
                    )

                return findings, text
            except Exception as e:
                emit(agent_name, "agent_response", f"Analysis error: {e!s:.200}", "analysing")
                return [], ""

        results = await asyncio.gather(
            *[_run_agent_analysis(ad) for ad in analysts]
        )

        all_findings: list[dict] = []
        agent_analyses: dict[str, str] = {}
        for (findings, analysis_text), agent_def in zip(results, analysts):
            all_findings.extend(findings)
            agent_analyses[agent_def.handle] = analysis_text

        run["findings"] = all_findings
        emit("system", "phase_completed", f"Analysis complete: {len(all_findings)} findings", "analysing")

        # DB checkpoint: persist findings
        if session_factory:
            await _update_run_phase(session_factory, run_id, "running", "analysing")
            try:
                async with session_factory() as _db:
                    from codecouncil.db.repositories import FindingRepository as _FR
                    fr = _FR(_db)
                    for f in all_findings:
                        await fr.create_finding({
                            "id": uuid.UUID(f["id"]),
                            "run_id": uuid.UUID(run_id),
                            "agent": f["agent"],
                            "severity": f["severity"],
                            "scope": f.get("scope", "repository"),
                            "content": f["content"],
                            "implication": f.get("implication", ""),
                            "created_at": datetime.now(timezone.utc),
                        })
                    await _db.commit()
            except Exception as exc:
                import logging
                logging.getLogger("codecouncil.pipeline").warning("DB persist failed: %s", exc)

        # =================================================================
        # PHASE 3: DEBATE — Visionary proposes, Skeptic challenges
        # =================================================================
        run["phase"] = "debate"
        if session_factory:
            await _update_run_phase(session_factory, run_id, "running", "debate")
        emit("system", "phase_started", "Debate phase: Adversarial topology", "debate")

        findings_summary = "\n".join(
            [f"[{f['severity'].upper()}] ({f['agent']}) {f['content']}" for f in all_findings]
        )

        # Determine proposer/challenger
        proposer = agent_registry.get_proposer()
        challenger = agent_registry.get_challenger()

        proposal_system = proposer.build_system_prompt(memory_context="")
        proposal_user = proposer.get_prompt(
            "debate_propose",
            repo_name=f"{repo_org}/{repo_name}",
            findings_summary=findings_summary,
            archaeologist_analysis=agent_analyses.get("archaeologist", ""),
            skeptic_analysis=agent_analyses.get("skeptic", ""),
        )

        proposal_text, prop_in, prop_out = await llm_call(
            client, proposal_system, proposal_user,
            MODEL_HEAVY, MAX_TOKENS_DEBATE, proposer.temperature,
        )
        emit(
            "visionary", "agent_response", proposal_text, "debate",
            metadata={
                "provider": "openai", "model": MODEL_HEAVY,
                "input_tokens": prop_in, "output_tokens": prop_out,
            },
        )

        # Parse proposals
        proposals: list[dict] = []
        for i, match in enumerate(re.finditer(
            r'\[PROPOSAL\]\s*Title:\s*(.*?)\n.*?Goal:\s*(.*?)\n.*?Effort:\s*(.*?)\n'
            r'.*?Breaking:\s*(.*?)\n.*?Description:\s*(.*?)(?=\[PROPOSAL\]|$)',
            proposal_text, re.DOTALL,
        )):
            proposal = {
                "id": str(uuid.uuid4()),
                "run_id": run_id,
                "proposal_number": i + 1,
                "version": 1,
                "title": match.group(1).strip(),
                "goal": match.group(2).strip(),
                "description": match.group(5).strip(),
                "effort": match.group(3).strip(),
                "status": "proposed",
                "agent_id": "visionary",
                "author_agent": "visionary",
                "breaking_change": "yes" in match.group(4).strip().lower(),
                "finding_ids": [],
                "votes": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            proposals.append(proposal)
            emit(
                "visionary", "proposal_created",
                f"Proposal {i + 1}: {proposal['title']}",
                "debate", structured=proposal,
            )

        if not proposals:
            proposals.append({
                "id": str(uuid.uuid4()), "run_id": run_id, "proposal_number": 1,
                "version": 1, "title": "Address identified findings",
                "goal": "Improve codebase quality", "description": proposal_text,
                "effort": "M", "status": "proposed", "agent_id": "visionary",
                "author_agent": "visionary", "breaking_change": False,
                "finding_ids": [], "votes": [],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })

        run["proposals"] = proposals

        # Multi-round debate
        overrides = run.get("config_overrides", {})
        max_rounds = overrides.get("rounds", 3)
        topology_name = overrides.get("topology", "adversarial")
        budget_limit = float(overrides.get("budget", 0))
        hitl_enabled = overrides.get("hitl", False)
        debate_rounds = []
        challenge_text = ""
        evidence_text = ""
        visionary_response_text = ""

        emit("system", "phase_started", f"Debate phase: {topology_name.replace('_', ' ').title()} topology, {max_rounds} rounds", "debate")

        for round_num in range(1, max_rounds + 1):
            # Budget check before each round
            if budget_limit > 0:
                current_cost = sum(e.get("metadata", {}).get("cost_usd", 0) for e in run["events"])
                if current_cost >= budget_limit:
                    emit("system", "budget_exceeded", f"Budget limit ${budget_limit} reached (spent ${current_cost:.2f})", run["phase"])
                    run["status"] = "failed"
                    run["phase"] = "error"
                    if session_factory:
                        await _update_run_phase(session_factory, run_id, "failed", "error")
                    return

            emit("system", "round_started", f"Round {round_num}/{max_rounds}", "debate",
                 structured={"round": round_num, "max_rounds": max_rounds})

            # ── Skeptic challenges ──
            proposal_status_text = "\n".join(
                [f"P-{p['proposal_number']}: {p['title']} (status: {p['status']})" for p in proposals]
            )

            challenge_system = challenger.build_system_prompt(memory_context="")
            if round_num == 1:
                challenge_user = challenger.get_prompt(
                    "debate_challenge",
                    repo_name=f"{repo_org}/{repo_name}",
                    proposal_text=proposal_text,
                )
            else:
                challenge_user = challenger.get_prompt(
                    "debate_followup",
                    round_number=str(round_num),
                    repo_name=f"{repo_org}/{repo_name}",
                    visionary_text=visionary_response_text,
                    evidence_text=evidence_text,
                    proposal_status_text=proposal_status_text,
                )

            challenge_text, ch_in, ch_out = await llm_call(
                client, challenge_system, challenge_user,
                MODEL_HEAVY, MAX_TOKENS_DEBATE, challenger.temperature,
            )
            emit("skeptic", "agent_speaking", challenge_text, "debate",
                 metadata={"provider": "openai", "model": MODEL_HEAVY,
                           "input_tokens": ch_in, "output_tokens": ch_out})

            # ── Visionary responds to challenges ──
            defend_system = proposer.build_system_prompt(memory_context="")
            if round_num == 1:
                defend_user = proposer.get_prompt(
                    "debate_defend",
                    repo_name=f"{repo_org}/{repo_name}",
                    challenge_text=challenge_text,
                )
            else:
                defend_user = proposer.get_prompt(
                    "debate_defend_followup",
                    round_number=str(round_num),
                    repo_name=f"{repo_org}/{repo_name}",
                    challenge_text=challenge_text,
                    evidence_text=evidence_text,
                )

            visionary_response_text, def_in, def_out = await llm_call(
                client, defend_system, defend_user,
                MODEL_HEAVY, MAX_TOKENS_DEBATE, proposer.temperature,
            )
            emit("visionary", "agent_speaking", visionary_response_text, "debate",
                 metadata={"provider": "openai", "model": MODEL_HEAVY,
                           "input_tokens": def_in, "output_tokens": def_out})

            # Check for revised/withdrawn proposals
            for p in proposals:
                if p["status"] == "proposed":
                    title_lower = p["title"].lower()
                    if f"withdraw" in visionary_response_text.lower() and title_lower in visionary_response_text.lower():
                        p["status"] = "withdrawn"
                        emit("visionary", "proposal_withdrawn", f"Withdrawn: {p['title']}", "debate")
                    elif "[REVISED]" in visionary_response_text and title_lower in visionary_response_text.lower():
                        p["version"] += 1
                        p["status"] = "revised"
                        emit("visionary", "proposal_revised", f"Revised (v{p['version']}): {p['title']}", "debate")

            # ── Analysts provide evidence ──
            round_turns = [
                {"agent": "skeptic", "action": "challenge", "content": challenge_text},
                {"agent": "visionary", "action": "respond", "content": visionary_response_text},
            ]

            # Each analyst that has a debate_evidence prompt provides evidence
            skip_handles = set()
            if proposer:
                skip_handles.add(proposer.handle)
            if challenger:
                skip_handles.add(challenger.handle)

            for agent_def in analysts:
                if agent_def.handle in skip_handles:
                    continue
                evidence_user = agent_def.get_prompt(
                    "debate_evidence",
                    round_number=str(round_num),
                    max_rounds=str(max_rounds),
                    repo_name=f"{repo_org}/{repo_name}",
                    visionary_text=visionary_response_text,
                    challenge_text=challenge_text,
                )
                if not evidence_user:
                    continue
                evidence_system = agent_def.build_system_prompt(memory_context="")
                evidence_text, ev_in, ev_out = await llm_call(
                    client, evidence_system, evidence_user,
                    MODEL_HEAVY, MAX_TOKENS_DEBATE, agent_def.temperature,
                )
                emit(agent_def.handle, "agent_speaking", evidence_text, "debate",
                     metadata={"provider": "openai", "model": MODEL_HEAVY,
                               "input_tokens": ev_in, "output_tokens": ev_out})
                round_turns.append({"agent": agent_def.handle, "action": "evidence", "content": evidence_text})

            debate_rounds.append({
                "round": round_num,
                "turns": round_turns,
            })

            emit("system", "round_ended", f"Round {round_num}/{max_rounds} complete", "debate",
                 structured={"round": round_num, "max_rounds": max_rounds})

        run["debate_rounds"] = debate_rounds
        emit("system", "phase_completed", f"Debate complete: {max_rounds} rounds", "debate")

        # DB checkpoint: persist proposals
        if session_factory:
            await _update_run_phase(session_factory, run_id, "running", "debate")
            try:
                async with session_factory() as _db:
                    from codecouncil.db.repositories import ProposalRepository as _PR
                    pr = _PR(_db)
                    for p in proposals:
                        await pr.create_proposal({
                            "id": uuid.UUID(p["id"]),
                            "run_id": uuid.UUID(run_id),
                            "proposal_number": p["proposal_number"],
                            "version": p["version"],
                            "title": p["title"],
                            "goal": p["goal"],
                            "effort": p.get("effort", "M"),
                            "status": p["status"],
                            "author_agent": p.get("author_agent", "visionary"),
                            "created_at": datetime.now(timezone.utc),
                            "updated_at": datetime.now(timezone.utc),
                        })
                    await _db.commit()
            except Exception as exc:
                import logging
                logging.getLogger("codecouncil.pipeline").warning("DB persist failed: %s", exc)

        # =================================================================
        # PHASE 4: VOTING
        # =================================================================
        run["phase"] = "synthesis"
        if session_factory:
            await _update_run_phase(session_factory, run_id, "running", "synthesis")
        emit("system", "phase_started", "Voting phase", "synthesis")

        all_votes: list[dict] = []

        # Determine voting agents
        voting_agents = agent_registry.list_voting()

        # Build debate context string for vote prompts
        debate_context = (
            f"Skeptic's challenges:\n{challenge_text}\n\n"
            f"Archaeologist's evidence:\n{evidence_text}"
        )

        for proposal in proposals:
            for agent_def in voting_agents:
                agent = agent_def.handle
                try:
                    vote_user = agent_def.get_prompt(
                        "vote",
                        repo_name=f"{repo_org}/{repo_name}",
                        proposal_title=proposal["title"],
                        proposal_goal=proposal["goal"],
                        proposal_effort=proposal.get("effort", ""),
                        proposal_description=proposal.get("description", ""),
                        challenge_text=challenge_text,
                        evidence_text=evidence_text,
                        debate_context=debate_context,
                    )
                    if not vote_user:
                        continue
                    vote_system = agent_def.build_system_prompt(memory_context="")

                    vote_text, v_in, v_out = await llm_call(
                        client, vote_system, vote_user,
                        MODEL_LIGHT, MAX_TOKENS_VOTE, 0.2,
                    )

                    vote_type = "YES"
                    if "[VOTE:NO]" in vote_text:
                        vote_type = "NO"
                    elif "[VOTE:ABSTAIN]" in vote_text:
                        vote_type = "ABSTAIN"
                    elif "NO" in vote_text.upper()[:20]:
                        vote_type = "NO"

                    conf_match = re.search(r"Confidence:\s*([\d.]+)", vote_text)
                    confidence = float(conf_match.group(1)) if conf_match else 0.7
                    confidence = min(1.0, max(0.0, confidence))

                    vote = {
                        "id": str(uuid.uuid4()),
                        "run_id": run_id,
                        "proposal_id": proposal["id"],
                        "agent": agent,
                        "agent_id": agent,
                        "vote": vote_type,
                        "vote_type": "approve" if vote_type == "YES" else "reject",
                        "rationale": vote_text.strip(),
                        "reasoning": vote_text.strip(),
                        "confidence": confidence,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                    }
                    all_votes.append(vote)
                    proposal.setdefault("votes", []).append(vote)
                    emit(
                        agent, "vote_cast",
                        f"[VOTE:{vote_type}] on '{proposal['title']}' (confidence: {confidence})",
                        "synthesis", structured=vote,
                    )
                except Exception as e:
                    emit(agent, "vote_cast", f"Vote error: {e!s:.100}", "synthesis")

        # Determine outcomes
        for proposal in proposals:
            p_votes = [v for v in all_votes if v["proposal_id"] == proposal["id"]]
            yes_count = sum(1 for v in p_votes if v["vote"] == "YES")
            total_voting = len(p_votes)
            if total_voting > 0 and yes_count / total_voting >= 0.5:
                proposal["status"] = "accepted"
            else:
                proposal["status"] = "rejected"

        run["votes"] = all_votes
        passed = sum(1 for p in proposals if p["status"] == "accepted")
        failed = len(proposals) - passed
        emit("system", "phase_completed", f"Voting complete: {passed} passed, {failed} failed", "synthesis")

        # DB checkpoint: persist votes and update proposal statuses
        if session_factory:
            await _update_run_phase(session_factory, run_id, "running", "synthesis")
            try:
                async with session_factory() as _db:
                    from codecouncil.db.repositories import (
                        ProposalRepository as _PR2,
                        VoteRepository as _VR,
                    )
                    vr = _VR(_db)
                    for v in all_votes:
                        await vr.create_vote({
                            "id": uuid.UUID(v["id"]),
                            "run_id": uuid.UUID(run_id),
                            "proposal_id": uuid.UUID(v["proposal_id"]),
                            "agent": v["agent"],
                            "vote": v["vote"],
                            "rationale": v.get("rationale", ""),
                            "confidence": v.get("confidence", 0.7),
                            "created_at": datetime.now(timezone.utc),
                        })
                    pr2 = _PR2(_db)
                    for p in proposals:
                        await pr2.update_proposal_status(uuid.UUID(p["id"]), p["status"])
                    await _db.commit()
            except Exception as exc:
                import logging
                logging.getLogger("codecouncil.pipeline").warning("DB persist failed: %s", exc)

        # =================================================================
        # PHASE 5: SCRIBING — Generate RFC
        # =================================================================
        run["phase"] = "scribing"
        if session_factory:
            await _update_run_phase(session_factory, run_id, "running", "scribing")
        emit("system", "phase_started", "Scribe generating RFC", "scribing")
        emit("scribe", "agent_thinking", "Synthesizing council proceedings into RFC", "scribing")

        vote_summary = ""
        for proposal in proposals:
            p_votes = [v for v in all_votes if v["proposal_id"] == proposal["id"]]
            vote_lines = "\n".join(
                [f"  - {v['agent'].capitalize()}: {v['vote']} ({v['confidence']}) -- "
                 f"{v['rationale']}" for v in p_votes]
            )
            status_label = "PASSED" if proposal["status"] == "accepted" else "FAILED"
            vote_summary += (
                f"\n### P-{proposal['proposal_number']}: {proposal['title']} "
                f"[{status_label}]\n{vote_lines}\n"
            )

        # Build full findings list for RFC (not truncated)
        findings_by_severity = {"critical": [], "high": [], "medium": [], "info": []}
        for f in all_findings:
            bucket = findings_by_severity.get(f["severity"], findings_by_severity["info"])
            bucket.append(f)
        full_findings_text = ""
        for sev in ["critical", "high", "medium", "info"]:
            group = findings_by_severity[sev]
            if group:
                full_findings_text += f"\n**{sev.upper()} ({len(group)})**\n"
                for f in group:
                    full_findings_text += (
                        f"- [{f['agent'].upper()}] {f['content']}\n"
                        f"  _Implication:_ {f.get('implication', 'N/A')}\n"
                    )

        # Build full vote detail block
        full_vote_details = ""
        for proposal in proposals:
            p_votes = [v for v in all_votes if v["proposal_id"] == proposal["id"]]
            status_label = "PASSED" if proposal["status"] == "accepted" else "FAILED"
            full_vote_details += (
                f"\n#### P-{proposal['proposal_number']}: {proposal['title']} [{status_label}]\n"
                f"Effort: {proposal.get('effort', 'N/A')} | "
                f"Breaking: {'YES' if proposal.get('breaking_change') else 'NO'} | "
                f"Author: {proposal.get('author_agent', 'visionary')}\n"
                f"Description: {proposal.get('description', '')}\n\n"
                "| Agent | Vote | Confidence | Rationale |\n"
                "|---|---|---|---|\n"
            )
            for v in p_votes:
                full_vote_details += (
                    f"| {v['agent'].capitalize()} | **{v['vote']}** | {v['confidence']:.0%} "
                    f"| {v['rationale']} |\n"
                )
            no_votes = [v for v in p_votes if v["vote"] == "NO"]
            for v in no_votes:
                full_vote_details += (
                    f"\n> **DISSENT ({v['agent'].capitalize()}):** {v['rationale']}\n"
                )

        scribe_def = agent_registry.get_scribe()
        if not scribe_def:
            raise RuntimeError("Scribe agent not found in registry")

        rfc_system = scribe_def.build_system_prompt(memory_context="")
        rfc_user = scribe_def.get_prompt(
            "synthesize",
            repo_name=f"{repo_org}/{repo_name}",
            repo_url=repo_url,
            file_count=str(len(files)),
            total_loc=f"{total_loc:,}",
            lang_summary=lang_summary,
            author_count=str(len(authors)),
            analysis_date=datetime.now(timezone.utc).strftime('%Y-%m-%d'),
            archaeologist_analysis=agent_analyses.get("archaeologist", ""),
            skeptic_analysis=agent_analyses.get("skeptic", ""),
            proposal_text=proposal_text,
            challenge_text=challenge_text,
            evidence_text=evidence_text,
            all_findings_text=full_findings_text,
            vote_summary=full_vote_details,
            proposal_count=str(len(proposals)),
        )

        rfc_content, rfc_in, rfc_out = await llm_call(
            client, rfc_system, rfc_user,
            MODEL_HEAVY, scribe_def.max_tokens, scribe_def.temperature,
        )

        run["rfc_content"] = rfc_content
        emit(
            "scribe", "agent_response", "RFC synthesis complete", "scribing",
            metadata={
                "provider": "openai", "model": MODEL_HEAVY,
                "input_tokens": rfc_in, "output_tokens": rfc_out,
            },
        )
        # Persist RFC content as a special event so it survives restart
        emit("scribe", "rfc_generated", rfc_content, "scribing", structured={"rfc_content": rfc_content})
        emit("system", "phase_completed", "RFC finalized", "scribing")

        # =================================================================
        # PHASE 6: FINALIZE
        # =================================================================
        run["phase"] = "done"
        run["status"] = "completed"

        total_cost = 0.0
        for e in run["events"]:
            c = e.get("metadata", {}).get("cost_usd", 0)
            if c:
                total_cost += c
        run["cost_usd"] = round(total_cost, 4)
        run["updated_at"] = datetime.now(timezone.utc).isoformat()

        consensus = round(passed / max(len(proposals), 1) * 100, 1)
        emit(
            "system", "run_completed",
            f"Council complete. {len(all_findings)} findings, {len(proposals)} proposals "
            f"({passed} passed). Consensus: {consensus}%",
            "output",
        )

        # DB checkpoint: update final run state (events already persisted incrementally)
        if session_factory:
            try:
                async with session_factory() as _db:
                    from codecouncil.db.repositories import RunRepository as _RR5
                    from sqlalchemy import update as _sa_update
                    from codecouncil.db.models import RunModel as _RM
                    run_repo = _RR5(_db)
                    await run_repo.update_run_status(uuid.UUID(run_id), "completed", "done")
                    await run_repo.update_run_cost(uuid.UUID(run_id), total_cost)
                    # Also persist consensus score
                    await _db.execute(
                        _sa_update(_RM).where(_RM.id == uuid.UUID(run_id)).values(
                            consensus_score=consensus
                        )
                    )
                    await _db.commit()
            except Exception as exc:
                import logging
                logging.getLogger("codecouncil.pipeline").warning("DB persist failed: %s", exc)

        # Send webhook notification if configured
        webhook_url = run.get("config_overrides", {}).get("webhook_url") or os.environ.get("WEBHOOK_URL", "")
        if webhook_url and session_factory:
            try:
                import httpx
                async with httpx.AsyncClient() as http:
                    await http.post(webhook_url, json={
                        "event": "run_completed",
                        "run_id": run_id,
                        "repo_url": repo_url,
                        "status": "completed",
                        "findings_count": len(all_findings),
                        "proposals_count": len(proposals),
                        "passed_count": passed,
                        "consensus_score": consensus,
                        "total_cost": total_cost,
                        "rfc_preview": rfc_content[:500] if rfc_content else "",
                    }, timeout=10)
            except Exception as exc:
                import logging
                logging.getLogger("codecouncil.pipeline").warning("Webhook failed: %s", exc)

        # Remove from in-memory cache — it's now fully in DB
        runs_store.pop(run_id, None)

    except Exception as e:
        import traceback
        run["status"] = "failed"
        run["phase"] = "error"
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        emit("system", "run_failed", f"Pipeline error: {e!s}\n{traceback.format_exc()[:500]}", "error")

        # DB checkpoint: mark failed
        if session_factory:
            try:
                async with session_factory() as _db:
                    from codecouncil.db.repositories import RunRepository as _RR6
                    await _RR6(_db).update_run_status(uuid.UUID(run_id), "failed", "error")
                    await _db.commit()
            except Exception as exc:
                import logging
                logging.getLogger("codecouncil.pipeline").warning("DB persist failed: %s", exc)

    finally:
        # Cleanup temp dir
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
