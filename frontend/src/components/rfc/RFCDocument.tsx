"use client";

import { useState } from "react";
import type { RunDetail } from "@/lib/types";
import { getAgentColor } from "@/lib/utils";
import { VoteMatrix } from "./VoteMatrix";
import { DissentBlock } from "./DissentBlock";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "var(--cc-red)",
  high: "var(--cc-yellow)",
  medium: "var(--cc-accent)",
  low: "var(--cc-blue)",
  info: "var(--cc-text-muted)",
};

const SEVERITY_BG: Record<string, string> = {
  critical: "rgba(255,107,107,0.2)",
  high: "rgba(255,217,61,0.2)",
  medium: "rgba(108,92,231,0.2)",
  low: "rgba(78,205,196,0.2)",
  info: "rgba(136,136,160,0.2)",
};

const SEVERITY_LABELS: Record<string, string> = {
  critical: "CRITICAL",
  high: "HIGH",
  medium: "MEDIUM",
  low: "LOW",
  info: "INFO",
};

const AGENT_DISPLAY_NAMES: Record<string, string> = {
  archaeologist: "Archaeologist",
  skeptic: "Skeptic",
  visionary: "Visionary",
  scribe: "Scribe",
};

function getDisplayName(agentId: string): string {
  const lower = agentId.toLowerCase();
  for (const [key, val] of Object.entries(AGENT_DISPLAY_NAMES)) {
    if (lower.includes(key)) return val;
  }
  return agentId;
}

const EFFORT_STYLES: Record<string, { bg: string; color: string }> = {
  XS: { bg: "rgba(0,214,143,0.15)", color: "var(--cc-green)" },
  S: { bg: "rgba(0,214,143,0.15)", color: "var(--cc-green)" },
  M: { bg: "rgba(255,217,61,0.15)", color: "var(--cc-yellow)" },
  L: { bg: "rgba(255,107,107,0.15)", color: "var(--cc-red)" },
  XL: { bg: "rgba(255,107,107,0.15)", color: "var(--cc-red)" },
};

interface RFCDocumentProps {
  run: RunDetail;
  rfcData?: Record<string, unknown>;
}

export function RFCDocument({ run, rfcData }: RFCDocumentProps) {
  const [appendixOpen, setAppendixOpen] = useState(false);

  const title = (rfcData?.title as string) || `RFC: ${run.repo?.url || run.id} Codebase Analysis`;
  const summary = (rfcData?.summary as string) || "Automated codebase analysis by CodeCouncil multi-agent system.";
  const createdAt = new Date(run.created_at || Date.now()).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  const totalCost = run.total_cost || run.cost?.total_cost || 0;
  const consensusPercent = (rfcData?.consensus_percent as number) ||
    (run.proposals.length > 0
      ? Math.round(
          (run.proposals.filter((p) => p.status === "accepted").length / run.proposals.length) * 100
        )
      : 0);

  // Split proposals into passed, deadlocked, etc
  const deadlockedProposals = run.proposals.filter((p) => p.status === "rejected");
  const passedOrAmended = run.proposals.filter((p) => p.status !== "rejected");

  // Unique agents
  const agentIds = [...new Set([
    ...run.findings.map((f) => f.agent_id),
    ...run.proposals.map((p) => p.agent_id),
  ])];

  return (
    <article style={{ color: "var(--cc-text)" }}>
      {/* ═══════ RFC HEADER ═══════ */}
      <div
        id="header"
        className="mb-10 pb-8 border-b"
        style={{ borderColor: "var(--cc-border)" }}
      >
        <h1
          className="text-[32px] font-bold leading-tight mb-2"
          style={{ color: "var(--cc-text)" }}
        >
          {title}
        </h1>
        <div className="flex flex-wrap gap-4 mb-4 text-[13px]" style={{ color: "var(--cc-text-muted)" }}>
          <span>{createdAt}</span>
          <span>Run #{run.id.slice(0, 4)}</span>
          <span>3 rounds</span>
          <span>Total cost: ${totalCost.toFixed(2)}</span>
        </div>
        {consensusPercent > 0 && (
          <span
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-[13px] font-bold"
            style={{
              backgroundColor: consensusPercent >= 70
                ? "rgba(0,214,143,0.15)"
                : "rgba(255,217,61,0.15)",
              color: consensusPercent >= 70 ? "var(--cc-green)" : "var(--cc-yellow)",
            }}
          >
            Consensus: {consensusPercent}%
          </span>
        )}
        {/* Agent chips */}
        <div className="flex gap-2 mt-3">
          {agentIds.map((agentId) => {
            const color = getAgentColor(agentId);
            return (
              <span
                key={agentId}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs border"
                style={{
                  backgroundColor: "var(--cc-bg-card)",
                  borderColor: "var(--cc-border)",
                }}
              >
                <span
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: color }}
                />
                {getDisplayName(agentId)}
              </span>
            );
          })}
        </div>
      </div>

      {/* ═══════ EXECUTIVE SUMMARY ═══════ */}
      <section className="mb-9" id="summary">
        <h2
          className="text-xl font-bold mb-4 pb-2 border-b"
          style={{ color: "var(--cc-text)", borderColor: "var(--cc-border)" }}
        >
          Executive Summary
        </h2>
        <div
          className="rounded-r-[10px] text-[15px] leading-[1.7]"
          style={{
            padding: "20px 24px",
            backgroundColor: "var(--cc-bg-card)",
            borderLeft: "4px solid var(--cc-accent)",
            color: "var(--cc-text)",
          }}
        >
          {summary}
        </div>
      </section>

      {/* ═══════ CRITICAL FINDINGS ═══════ */}
      <section className="mb-9" id="findings">
        <h2
          className="text-xl font-bold mb-4 pb-2 border-b"
          style={{ color: "var(--cc-text)", borderColor: "var(--cc-border)" }}
        >
          Critical Findings
        </h2>
        {run.findings.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--cc-text-muted)" }}>
            No findings recorded.
          </p>
        ) : (
          <div className="space-y-3">
            {run.findings.map((finding) => {
              const sevColor = SEVERITY_COLORS[finding.severity] || "var(--cc-text-muted)";
              const sevBg = SEVERITY_BG[finding.severity] || "rgba(136,136,160,0.2)";
              const sevLabel = SEVERITY_LABELS[finding.severity] || finding.severity.toUpperCase();
              const agentColor = getAgentColor(finding.agent_id);

              return (
                <div
                  key={finding.id}
                  className="rounded-[10px] border"
                  style={{
                    padding: "16px 20px",
                    backgroundColor: "var(--cc-bg-card)",
                    borderColor: "var(--cc-border)",
                    borderLeftWidth: "4px",
                    borderLeftColor: sevColor,
                  }}
                >
                  <div className="flex items-center gap-2 mb-2">
                    <span
                      className="px-2 py-0.5 rounded text-[10px] font-bold uppercase"
                      style={{ backgroundColor: sevBg, color: sevColor }}
                    >
                      {sevLabel}
                    </span>
                    <span
                      className="text-[11px]"
                      style={{ color: agentColor }}
                    >
                      {getDisplayName(finding.agent_id)}
                    </span>
                  </div>
                  <div
                    className="text-sm leading-relaxed"
                    style={{ color: "var(--cc-text)" }}
                  >
                    <strong>{finding.title}</strong>
                    {finding.description && (
                      <span className="ml-1">{finding.description}</span>
                    )}
                  </div>
                  {finding.recommendation && (
                    <div
                      className="text-[13px] mt-2 italic"
                      style={{ color: "var(--cc-text-muted)" }}
                    >
                      Implication: {finding.recommendation}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* ═══════ PROPOSALS & VOTES ═══════ */}
      <section className="mb-9" id="proposals">
        <h2
          className="text-xl font-bold mb-4 pb-2 border-b"
          style={{ color: "var(--cc-text)", borderColor: "var(--cc-border)" }}
        >
          Proposals &amp; Votes
        </h2>
        {passedOrAmended.length === 0 && deadlockedProposals.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--cc-text-muted)" }}>
            No proposals recorded.
          </p>
        ) : (
          <div className="space-y-4">
            {passedOrAmended.map((proposal) => {
              const isPassed = proposal.status === "accepted";
              const approveCount = proposal.votes.filter((v) => v.vote_type === "approve").length;
              const rejectCount = proposal.votes.filter((v) => v.vote_type === "reject").length;
              const resultLabel = isPassed
                ? `PASSED (${approveCount}-${rejectCount})`
                : proposal.status.toUpperCase();

              return (
                <div
                  key={proposal.id}
                  className="rounded-[10px] border"
                  style={{
                    padding: "20px 24px",
                    backgroundColor: "var(--cc-bg-card)",
                    borderColor: "var(--cc-border)",
                  }}
                >
                  {/* Title row */}
                  <div className="flex items-center justify-between mb-3">
                    <h3
                      className="text-base font-bold"
                      style={{ color: "var(--cc-text)" }}
                    >
                      {proposal.title}
                    </h3>
                    <span
                      className="px-2.5 py-1 rounded-md text-[11px] font-semibold"
                      style={{
                        backgroundColor: "rgba(108,92,231,0.15)",
                        color: "var(--cc-accent)",
                      }}
                    >
                      Effort: {(proposal as unknown as { effort?: string }).effort || "M"}
                    </span>
                  </div>
                  {/* Body */}
                  <div
                    className="text-sm leading-[1.7] mb-4"
                    style={{ color: "var(--cc-text)" }}
                  >
                    {proposal.description}
                  </div>
                  {/* Vote Matrix */}
                  {proposal.votes && proposal.votes.length > 0 && (
                    <>
                      <VoteMatrix votes={proposal.votes} />
                      <span
                        className="inline-block px-3.5 py-1 rounded-md text-xs font-bold uppercase"
                        style={{
                          backgroundColor: isPassed
                            ? "rgba(0,214,143,0.15)"
                            : "rgba(255,107,107,0.15)",
                          color: isPassed ? "var(--cc-green)" : "var(--cc-red)",
                        }}
                      >
                        {resultLabel}
                      </span>
                      <DissentBlock
                        votes={proposal.votes}
                        proposalTitle={proposal.title}
                      />
                    </>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* ═══════ DEADLOCKED ITEMS ═══════ */}
      {deadlockedProposals.length > 0 && (
        <section className="mb-9" id="deadlocked">
          <h2
            className="text-xl font-bold mb-4 pb-2 border-b"
            style={{ color: "var(--cc-text)", borderColor: "var(--cc-border)" }}
          >
            Deadlocked Items
          </h2>
          <div className="space-y-4">
            {deadlockedProposals.map((proposal) => {
              const forVotes = proposal.votes.filter((v) => v.vote_type === "approve");
              const againstVotes = proposal.votes.filter((v) => v.vote_type === "reject");

              return (
                <div
                  key={proposal.id}
                  className="rounded-[10px]"
                  style={{
                    padding: "20px 24px",
                    backgroundColor: "rgba(255,107,107,0.04)",
                    border: "2px solid rgba(255,107,107,0.3)",
                  }}
                >
                  <span
                    className="inline-flex items-center gap-1.5 px-3 py-1 rounded-md text-[11px] font-bold mb-3"
                    style={{
                      backgroundColor: "rgba(255,107,107,0.15)",
                      color: "var(--cc-red)",
                    }}
                  >
                    DEADLOCKED
                  </span>
                  <h3
                    className="text-base font-bold mb-3"
                    style={{ color: "var(--cc-text)" }}
                  >
                    {proposal.title}
                  </h3>
                  {/* Side-by-side positions */}
                  <div className="grid grid-cols-2 gap-3">
                    {forVotes.length > 0 && (
                      <div
                        className="rounded-lg p-3.5"
                        style={{ backgroundColor: "var(--cc-bg)" }}
                      >
                        <div
                          className="text-xs font-bold mb-1.5"
                          style={{ color: "var(--cc-green)" }}
                        >
                          FOR &mdash; {getDisplayName(forVotes[0].agent_id)}
                        </div>
                        <div
                          className="text-[13px] leading-relaxed"
                          style={{ color: "var(--cc-text)" }}
                        >
                          {forVotes[0].reasoning || "No reasoning provided."}
                        </div>
                      </div>
                    )}
                    {againstVotes.length > 0 && (
                      <div
                        className="rounded-lg p-3.5"
                        style={{ backgroundColor: "var(--cc-bg)" }}
                      >
                        <div
                          className="text-xs font-bold mb-1.5"
                          style={{ color: "var(--cc-red)" }}
                        >
                          AGAINST &mdash; {getDisplayName(againstVotes[0].agent_id)}
                        </div>
                        <div
                          className="text-[13px] leading-relaxed"
                          style={{ color: "var(--cc-text)" }}
                        >
                          {againstVotes[0].reasoning || "No reasoning provided."}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      )}

      {/* ═══════ ACTION ITEMS ═══════ */}
      {run.proposals.length > 0 && (
        <section className="mb-9" id="actions">
          <h2
            className="text-xl font-bold mb-4 pb-2 border-b"
            style={{ color: "var(--cc-text)", borderColor: "var(--cc-border)" }}
          >
            Action Items
          </h2>
          <div className="space-y-2">
            {run.proposals
              .filter((p) => p.status === "accepted" || p.status === "amended")
              .map((proposal, i) => (
                <div
                  key={proposal.id}
                  className="flex gap-3 items-start rounded-lg border"
                  style={{
                    padding: "14px 18px",
                    backgroundColor: "var(--cc-bg-card)",
                    borderColor: "var(--cc-border)",
                  }}
                >
                  <div
                    className="w-7 h-7 rounded-md flex items-center justify-center text-[13px] font-bold text-white shrink-0"
                    style={{ backgroundColor: "var(--cc-accent)" }}
                  >
                    {i + 1}
                  </div>
                  <div className="flex-1">
                    <div
                      className="text-sm font-semibold mb-1"
                      style={{ color: "var(--cc-text)" }}
                    >
                      {proposal.title}
                    </div>
                    <div className="flex gap-2">
                      <span
                        className="px-2 py-0.5 rounded text-[10px] font-semibold"
                        style={{
                          backgroundColor: "rgba(108,92,231,0.15)",
                          color: "var(--cc-accent)",
                        }}
                      >
                        From: {proposal.id}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
          </div>
        </section>
      )}

      {/* ═══════ COST SUMMARY ═══════ */}
      {run.cost && (
        <section className="mb-9" id="cost">
          <h2
            className="text-xl font-bold mb-4 pb-2 border-b"
            style={{ color: "var(--cc-text)", borderColor: "var(--cc-border)" }}
          >
            Cost Summary
          </h2>
          <table className="w-full text-[13px]" style={{ borderCollapse: "collapse" }}>
            <thead>
              <tr>
                {["Agent", "Input Tokens", "Output Tokens", "Cost", "Latency"].map((h) => (
                  <th
                    key={h}
                    className="text-left px-3 py-2 text-[11px] uppercase tracking-wide border-b"
                    style={{ color: "var(--cc-text-muted)", borderColor: "var(--cc-border)" }}
                  >
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Object.entries(run.cost.by_agent || {}).map(([agent, agentCost]) => {
                const color = getAgentColor(agent);
                return (
                  <tr key={agent}>
                    <td className="px-3 py-2 border-b" style={{ borderColor: "rgba(30,30,46,0.5)" }}>
                      <span className="flex items-center gap-2">
                        <span
                          className="w-2 h-2 rounded-full"
                          style={{ backgroundColor: color }}
                        />
                        {getDisplayName(agent)}
                      </span>
                    </td>
                    <td className="px-3 py-2 border-b font-mono" style={{ borderColor: "rgba(30,30,46,0.5)" }}>
                      --
                    </td>
                    <td className="px-3 py-2 border-b font-mono" style={{ borderColor: "rgba(30,30,46,0.5)" }}>
                      --
                    </td>
                    <td className="px-3 py-2 border-b font-mono" style={{ borderColor: "rgba(30,30,46,0.5)" }}>
                      ${(agentCost as number).toFixed(2)}
                    </td>
                    <td className="px-3 py-2 border-b font-mono" style={{ borderColor: "rgba(30,30,46,0.5)" }}>
                      --
                    </td>
                  </tr>
                );
              })}
              {/* Total row */}
              <tr className="font-bold" style={{ borderTop: "2px solid var(--cc-border)" }}>
                <td className="px-3 py-2" colSpan={3}>Total</td>
                <td className="px-3 py-2 font-mono">${run.cost.total_cost.toFixed(2)}</td>
                <td className="px-3 py-2 font-mono">--</td>
              </tr>
            </tbody>
          </table>
        </section>
      )}

      {/* ═══════ DEBATE APPENDIX ═══════ */}
      <section className="mb-9" id="appendix">
        <h2
          className="text-xl font-bold mb-4 pb-2 border-b"
          style={{ color: "var(--cc-text)", borderColor: "var(--cc-border)" }}
        >
          Debate Appendix
        </h2>
        <button
          onClick={() => setAppendixOpen(!appendixOpen)}
          className="w-full flex items-center justify-between px-4 py-2.5 rounded-lg text-[13px] cursor-pointer transition-all duration-200"
          style={{
            backgroundColor: "var(--cc-bg-card)",
            border: "1px solid var(--cc-border)",
            color: "var(--cc-text-muted)",
          }}
        >
          <span>View full debate transcript ({run.events?.length || 0} exchanges)</span>
          <span>{appendixOpen ? "\u25B2" : "\u25BC"}</span>
        </button>
        {appendixOpen && (
          <div
            className="px-4 py-4 text-[13px] leading-relaxed font-mono border border-t-0 rounded-b-lg"
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
            }}
          >
            {(run.events || []).map((event) => (
              <div key={event.id} className="mb-2">
                <span style={{ color: "var(--cc-text-muted)" }}>
                  [{new Date(event.timestamp).toLocaleTimeString()}]
                </span>{" "}
                <span style={{ color: event.agent_id ? getAgentColor(event.agent_id) : "var(--cc-text-muted)" }}>
                  {event.agent_id || "System"}
                </span>
                : {JSON.stringify(event.payload).slice(0, 200)}
              </div>
            ))}
          </div>
        )}
      </section>
    </article>
  );
}
