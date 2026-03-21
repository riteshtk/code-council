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


async def run_real_council(run: dict, runs_store: dict) -> None:
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
            "metadata": extra.get("metadata", {}),
        }
        run["events"].append(event)
        run["updated_at"] = datetime.now(timezone.utc).isoformat()

    if not api_key:
        run["status"] = "failed"
        run["phase"] = "error"
        emit("system", "run_failed", "No OpenAI API key configured", "error")
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
            except Exception:
                loc = 0
            lang = _EXT_LANG.get(f.suffix.lower(), "Other")
            languages[lang] = languages.get(lang, 0) + loc
            total_loc += loc
            try:
                size = f.stat().st_size
            except Exception:
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
                except Exception:
                    pass
                break

        for manifest in [
            "pyproject.toml", "package.json", "go.mod", "Cargo.toml",
            "requirements.txt", "Gemfile", "setup.py", "setup.cfg",
        ]:
            mp = repo_path / manifest
            if mp.exists():
                try:
                    key_file_contents += f"\n--- {manifest} ---\n{mp.read_text(errors='ignore')[:3000]}\n"
                except Exception:
                    pass

        full_context = context + key_file_contents

        # =================================================================
        # PHASE 2: ANALYSIS — Each agent analyses independently
        # =================================================================
        run["phase"] = "analysing"
        emit("system", "phase_started", "Analysis phase: agents running in parallel", "analysing")

        agent_prompts = {
            "archaeologist": (
                "You are the Archaeologist -- the council's historian and evidence collector. "
                "You are declarative, data-first, and speak in facts.\n\n"
                "Analyze this repository and produce findings. Focus on:\n"
                "- Bus factor (author concentration)\n"
                "- Code churn and stability\n"
                "- TODO/FIXME accumulation\n"
                "- File age and commit patterns\n"
                "- Dead code indicators\n\n"
                "For each finding, use this format:\n"
                "[FINDING:CRITICAL|HIGH|MEDIUM|INFO] <description>\n"
                "Implication: <why this matters>\n\n"
                f"Repository context:\n{full_context}"
            ),
            "skeptic": (
                "You are the Skeptic -- the council's risk analyst and challenger. "
                "You are clipped, direct, and precise.\n\n"
                "Analyze this repository for risks. Focus on:\n"
                "- Security surface and vulnerabilities\n"
                "- Test coverage gaps\n"
                "- Dependency risks\n"
                "- API contract issues\n"
                "- Performance anti-patterns\n"
                "- Hidden dependencies\n\n"
                "For each finding, use this format:\n"
                "[FINDING:CRITICAL|HIGH|MEDIUM|INFO] <description>\n"
                "Implication: <why this matters>\n\n"
                f"Repository context:\n{full_context}"
            ),
            "visionary": (
                "You are the Visionary -- the council's proposal author and architecture reader. "
                "You are constructive but not naive.\n\n"
                "Analyze this repository and identify improvement opportunities. Focus on:\n"
                "- Architecture patterns and evolution paths\n"
                "- Refactoring opportunities\n"
                "- Module boundary clarification\n"
                "- Design pattern improvements\n"
                "- Bounded context identification\n\n"
                "For each finding, use this format:\n"
                "[FINDING:MEDIUM|INFO] <description>\n"
                "Implication: <opportunity>\n\n"
                f"Repository context:\n{full_context}"
            ),
        }

        _temperatures = {"archaeologist": 0.3, "skeptic": 0.2, "visionary": 0.5}

        async def _run_agent_analysis(
            agent_name: str, prompt: str,
        ) -> tuple[list[dict], str]:
            emit(agent_name, "agent_thinking", f"{agent_name.capitalize()} analyzing repository...", "analysing")
            try:
                response = await client.chat.completions.create(
                    model=MODEL_HEAVY,
                    messages=[{"role": "system", "content": prompt}],
                    **_model_kwargs(MODEL_HEAVY, MAX_TOKENS_ANALYSIS),
                    temperature=_temperatures.get(agent_name, 0.3),
                )
                text = response.choices[0].message.content or ""
                tokens_in = response.usage.prompt_tokens if response.usage else 0
                tokens_out = response.usage.completion_tokens if response.usage else 0
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
            _run_agent_analysis("archaeologist", agent_prompts["archaeologist"]),
            _run_agent_analysis("skeptic", agent_prompts["skeptic"]),
            _run_agent_analysis("visionary", agent_prompts["visionary"]),
        )

        all_findings: list[dict] = []
        agent_analyses: dict[str, str] = {}
        for (findings, analysis_text), agent_name in zip(
            results, ["archaeologist", "skeptic", "visionary"]
        ):
            all_findings.extend(findings)
            agent_analyses[agent_name] = analysis_text

        run["findings"] = all_findings
        emit("system", "phase_completed", f"Analysis complete: {len(all_findings)} findings", "analysing")

        # =================================================================
        # PHASE 3: DEBATE — Visionary proposes, Skeptic challenges
        # =================================================================
        run["phase"] = "debate"
        emit("system", "phase_started", "Debate phase: Adversarial topology", "debate")

        findings_summary = "\n".join(
            [f"[{f['severity'].upper()}] ({f['agent']}) {f['content']}" for f in all_findings]
        )

        proposal_prompt = (
            f"You are the Visionary. Based on these findings from the council analysis "
            f"of {repo_org}/{repo_name}:\n\n{findings_summary}\n\n"
            f"Archaeologist's analysis:\n{agent_analyses.get('archaeologist', '')}\n\n"
            f"Skeptic's analysis:\n{agent_analyses.get('skeptic', '')}\n\n"
            "Propose 2-4 concrete improvements. For each, use this format:\n"
            "[PROPOSAL]\nTitle: <short title>\nGoal: <one sentence goal>\n"
            "Effort: <XS|S|M|L|XL>\nBreaking: <yes|no>\n"
            "Description: <2-3 sentences explaining the proposal>\n\n"
            "Be specific and actionable. Reference actual files/patterns from the codebase."
        )

        proposal_response = await client.chat.completions.create(
            model=MODEL_HEAVY,
            messages=[{"role": "system", "content": proposal_prompt}],
            **_model_kwargs(MODEL_HEAVY, MAX_TOKENS_DEBATE),
            temperature=0.6,
        )
        proposal_text = proposal_response.choices[0].message.content or ""
        emit(
            "visionary", "agent_response", proposal_text, "debate",
            metadata={
                "provider": "openai", "model": MODEL_HEAVY,
                "input_tokens": proposal_response.usage.prompt_tokens if proposal_response.usage else 0,
                "output_tokens": proposal_response.usage.completion_tokens if proposal_response.usage else 0,
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
        max_rounds = run.get("config_overrides", {}).get("rounds", 3)
        debate_rounds = []
        challenge_text = ""
        evidence_text = ""
        visionary_response_text = ""

        for round_num in range(1, max_rounds + 1):
            emit("system", "round_started", f"Round {round_num}/{max_rounds}", "debate",
                 structured={"round": round_num, "max_rounds": max_rounds})

            if round_num == 1:
                # Round 1: Skeptic challenges proposals
                challenge_prompt = (
                    f"You are the Skeptic — clipped, direct, precise. "
                    f"The Visionary has proposed these changes for {repo_org}/{repo_name}:\n\n"
                    f"{proposal_text}\n\n"
                    "Challenge each proposal. Address the Visionary by name. For each proposal:\n"
                    "1. State your position (support/oppose)\n"
                    "2. Name specific risks and costs\n"
                    "3. Suggest conditions under which you'd change your position\n\n"
                    "Be thorough but concise."
                )
            else:
                # Subsequent rounds: Skeptic responds to Visionary's defense
                challenge_prompt = (
                    f"You are the Skeptic. This is round {round_num} of the debate on {repo_org}/{repo_name}.\n\n"
                    f"Visionary's latest response:\n{visionary_response_text}\n\n"
                    f"Archaeologist's evidence:\n{evidence_text}\n\n"
                    f"Current proposals:\n" +
                    "\n".join([f"P-{p['proposal_number']}: {p['title']} (status: {p['status']})" for p in proposals]) +
                    "\n\nHave your concerns been addressed? Update your positions. "
                    "If convinced, concede explicitly. If not, explain what's still missing. "
                    "You may declare DEADLOCK on any proposal where agreement is impossible."
                )

            challenge_response = await client.chat.completions.create(
                model=MODEL_HEAVY,
                messages=[{"role": "system", "content": challenge_prompt}],
                **_model_kwargs(MODEL_HEAVY, MAX_TOKENS_DEBATE),
                temperature=0.2,
            )
            challenge_text = challenge_response.choices[0].message.content or ""
            emit("skeptic", "agent_speaking", challenge_text, "debate",
                 metadata={"provider": "openai", "model": MODEL_HEAVY,
                           "input_tokens": challenge_response.usage.prompt_tokens if challenge_response.usage else 0,
                           "output_tokens": challenge_response.usage.completion_tokens if challenge_response.usage else 0})

            # Visionary responds to challenges
            if round_num == 1:
                visionary_defend_prompt = (
                    f"You are the Visionary. The Skeptic has challenged your proposals for {repo_org}/{repo_name}:\n\n"
                    f"Skeptic's challenges:\n{challenge_text}\n\n"
                    "Respond to each challenge. You may:\n"
                    "- Defend your proposal with reasoning\n"
                    "- Revise the proposal to address concerns (mark as [REVISED])\n"
                    "- Withdraw a proposal if evidence is overwhelming (mark as [WITHDRAWN])\n\n"
                    "Address the Skeptic by name. Be constructive."
                )
            else:
                visionary_defend_prompt = (
                    f"You are the Visionary. Round {round_num} of debate on {repo_org}/{repo_name}.\n\n"
                    f"Skeptic's latest:\n{challenge_text}\n\n"
                    f"Archaeologist's evidence:\n{evidence_text}\n\n"
                    "Respond. Have the Skeptic's remaining concerns been addressed by your revisions? "
                    "Final round — make your closing argument for each proposal."
                )

            visionary_defend = await client.chat.completions.create(
                model=MODEL_HEAVY,
                messages=[{"role": "system", "content": visionary_defend_prompt}],
                **_model_kwargs(MODEL_HEAVY, MAX_TOKENS_DEBATE),
                temperature=0.5,
            )
            visionary_response_text = visionary_defend.choices[0].message.content or ""
            emit("visionary", "agent_speaking", visionary_response_text, "debate",
                 metadata={"provider": "openai", "model": MODEL_HEAVY,
                           "input_tokens": visionary_defend.usage.prompt_tokens if visionary_defend.usage else 0,
                           "output_tokens": visionary_defend.usage.completion_tokens if visionary_defend.usage else 0})

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

            # Archaeologist provides evidence
            evidence_prompt = (
                f"You are the Archaeologist. Round {round_num} of debate on {repo_org}/{repo_name}.\n\n"
                f"Visionary's position:\n{visionary_response_text}\n"
                f"Skeptic's challenges:\n{challenge_text}\n\n"
                "Provide factual evidence from commit history and file patterns. "
                "State which side the data supports for each proposal. Be neutral and data-driven."
            )
            evidence_response = await client.chat.completions.create(
                model=MODEL_HEAVY,
                messages=[{"role": "system", "content": evidence_prompt}],
                **_model_kwargs(MODEL_HEAVY, MAX_TOKENS_DEBATE),
                temperature=0.3,
            )
            evidence_text = evidence_response.choices[0].message.content or ""
            emit("archaeologist", "agent_speaking", evidence_text, "debate",
                 metadata={"provider": "openai", "model": MODEL_HEAVY,
                           "input_tokens": evidence_response.usage.prompt_tokens if evidence_response.usage else 0,
                           "output_tokens": evidence_response.usage.completion_tokens if evidence_response.usage else 0})

            debate_rounds.append({
                "round": round_num,
                "turns": [
                    {"agent": "skeptic", "action": "challenge", "content": challenge_text},
                    {"agent": "visionary", "action": "respond", "content": visionary_response_text},
                    {"agent": "archaeologist", "action": "evidence", "content": evidence_text},
                ],
            })

            emit("system", "round_ended", f"Round {round_num}/{max_rounds} complete", "debate",
                 structured={"round": round_num, "max_rounds": max_rounds})

        run["debate_rounds"] = debate_rounds
        emit("system", "phase_completed", f"Debate complete: {max_rounds} rounds", "debate")

        # =================================================================
        # PHASE 4: VOTING
        # =================================================================
        run["phase"] = "synthesis"
        emit("system", "phase_started", "Voting phase", "synthesis")

        all_votes: list[dict] = []
        for proposal in proposals:
            vote_prompt = (
                f"You are voting on this proposal for {repo_org}/{repo_name}:\n\n"
                f"Title: {proposal['title']}\nGoal: {proposal['goal']}\n"
                f"Effort: {proposal['effort']}\nDescription: {proposal.get('description', '')}\n\n"
                f"Context from debate:\n- Skeptic: {challenge_text}\n"
                f"- Archaeologist: {evidence_text}\n\n"
                "Vote YES, NO, or ABSTAIN. Include your confidence (0.0-1.0) and a "
                "one-sentence rationale.\n"
                "Format: [VOTE:YES|NO|ABSTAIN] Rationale. Confidence: 0.X"
            )
            for agent in ["archaeologist", "skeptic", "visionary"]:
                try:
                    vote_response = await client.chat.completions.create(
                        model=MODEL_LIGHT,
                        messages=[{
                            "role": "system",
                            "content": f"You are the {agent.capitalize()} agent. {vote_prompt}",
                        }],
                        **_model_kwargs(MODEL_LIGHT, MAX_TOKENS_VOTE),
                        temperature=0.2,
                    )
                    vote_text = vote_response.choices[0].message.content or ""

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

        # =================================================================
        # PHASE 5: SCRIBING — Generate RFC
        # =================================================================
        run["phase"] = "output"
        emit("system", "phase_started", "Scribe generating RFC", "output")
        emit("scribe", "agent_thinking", "Synthesizing council proceedings into RFC", "output")

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

        rfc_prompt = (
            "You are the Scribe — the council's neutral secretary and institutional historian. "
            "Your job is to produce a PREMIUM, publication-ready RFC document. "
            "This is NOT a summary. It is a formal institutional record.\n\n"
            "REQUIREMENTS:\n"
            "- Use proper markdown with ## section headers and ### sub-headers\n"
            "- Write the Executive Summary as a highlighted blockquote (> prefix)\n"
            "- Preserve every agent's voice verbatim — do NOT paraphrase or smooth over disagreements\n"
            "- Quote agents directly using their name (e.g., 'The Skeptic noted: ...')\n"
            "- Make it read like an institutional document, not a bullet-point summary\n"
            "- Every section must be substantive and detailed\n\n"
            f"## REPOSITORY\n"
            f"**{repo_org}/{repo_name}** | {repo_url}\n"
            f"Files: {len(files)} | LOC: {total_loc:,} | Languages: {lang_summary}\n"
            f"Authors: {len(authors)} | Analysis date: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}\n\n"
            "## FULL AGENT ANALYSES\n\n"
            f"### Archaeologist (full)\n{agent_analyses.get('archaeologist', '')}\n\n"
            f"### Skeptic (full)\n{agent_analyses.get('skeptic', '')}\n\n"
            f"### Visionary — Proposals\n{proposal_text}\n\n"
            f"### Skeptic — Challenges\n{challenge_text}\n\n"
            f"### Archaeologist — Debate Evidence\n{evidence_text}\n\n"
            "## FULL FINDINGS\n"
            f"{full_findings_text}\n\n"
            "## FULL VOTE RECORD\n"
            f"{full_vote_details}\n\n"
            "---\n\n"
            "NOW WRITE THE RFC DOCUMENT with EXACTLY these sections:\n\n"
            "## RFC: [Repository Name] — Council Analysis Report\n"
            "*(header block: repo, date, participating agents, consensus score)*\n\n"
            "## Executive Summary\n"
            "> *(3-5 sentences as a blockquote — the single most important takeaway, "
            "overall health assessment, and top recommendation)*\n\n"
            "## Findings\n"
            "*(Organized by severity: CRITICAL first, then HIGH, MEDIUM, INFO. "
            "Each finding gets: severity badge in bold, agent attribution in brackets, "
            "the finding title, and its implication on a new line.)*\n\n"
            "## Proposals & Council Vote\n"
            f"*(All {len(proposals)} proposals. Each proposal gets: full description, "
            "a vote matrix table with columns Agent | Vote | Confidence | Rationale, "
            "outcome (PASSED/FAILED), and a DISSENT block for any NO votes with full rationale.)*\n\n"
            "## Action Items\n"
            "*(Numbered list from PASSED proposals only. Each item: action description, "
            "effort badge [XS/S/M/L/XL], and responsible area. "
            "If a proposal was REJECTED, note it was considered but not adopted.)*\n\n"
            "## Cost Summary\n"
            "*(Table: Phase | Tokens | Estimated Cost USD — plus a total row)*\n\n"
            "Write the complete document now. Be thorough. Every section must be substantive."
        )

        rfc_response = await client.chat.completions.create(
            model=MODEL_HEAVY,
            messages=[{"role": "system", "content": rfc_prompt}],
            **_model_kwargs(MODEL_HEAVY, MAX_TOKENS_RFC),
            temperature=0.1,
        )
        rfc_content = rfc_response.choices[0].message.content or ""

        run["rfc_content"] = rfc_content
        emit(
            "scribe", "agent_response", "RFC synthesis complete", "output",
            metadata={
                "provider": "openai", "model": MODEL_HEAVY,
                "input_tokens": rfc_response.usage.prompt_tokens if rfc_response.usage else 0,
                "output_tokens": rfc_response.usage.completion_tokens if rfc_response.usage else 0,
            },
        )
        emit("system", "phase_completed", "RFC finalized", "output")

        # =================================================================
        # PHASE 6: FINALIZE
        # =================================================================
        run["phase"] = "output"
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

    except Exception as e:
        import traceback
        run["status"] = "failed"
        run["phase"] = "error"
        run["updated_at"] = datetime.now(timezone.utc).isoformat()
        emit("system", "run_failed", f"Pipeline error: {e!s}\n{traceback.format_exc()[:500]}", "error")

    finally:
        # Cleanup temp dir
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
