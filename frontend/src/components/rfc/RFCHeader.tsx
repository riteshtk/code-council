"use client";

import { useMemo } from "react";
import { Calendar, Landmark, MessageSquare, Timer, DollarSign } from "lucide-react";
import type { RunDetail } from "@/lib/types";
import { getAgentColor } from "@/lib/utils";
import { getAgent } from "@/lib/constants";

const RFC_PHASES = [
  "INGEST",
  "ANALYSE",
  "OPENING",
  "DEBATE",
  "VOTING",
  "SCRIBING",
  "REVIEW",
  "FINALISE",
] as const;

function ConsensusRing({ percent }: { percent: number }) {
  const radius = 20;
  const stroke = 4;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (percent / 100) * circumference;
  const color = percent >= 70 ? "var(--cc-green)" : "var(--cc-yellow)";

  return (
    <svg width={52} height={52} viewBox="0 0 52 52">
      <circle
        cx="26"
        cy="26"
        r={radius}
        fill="none"
        stroke="var(--cc-border)"
        strokeWidth={stroke}
      />
      <circle
        cx="26"
        cy="26"
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth={stroke}
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        strokeLinecap="round"
        transform="rotate(-90 26 26)"
      />
    </svg>
  );
}

interface RFCHeaderProps {
  run: RunDetail;
  rfcData?: Record<string, unknown>;
}

export function RFCHeader({ run, rfcData }: RFCHeaderProps) {
  // Extract repo name from URL or fallback
  const repoName = useMemo(() => {
    const url = run.repo?.url || "";
    if (url) {
      const match = url.match(/(?:github\.com\/|^)([^/]+\/[^/]+?)(?:\.git)?$/);
      if (match) return match[1];
      const parts = url.replace(/\.git$/, "").split("/").filter(Boolean);
      if (parts.length >= 2) return `${parts[parts.length - 2]}/${parts[parts.length - 1]}`;
      return url;
    }
    return run.id;
  }, [run]);

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

  const deadlockedProposals = run.proposals.filter((p) => p.status === "deadlocked");

  // Unique agents
  const agentIds = [...new Set([
    ...run.findings.map((f) => f.agent_id),
    ...run.proposals.map((p) => p.agent_id),
  ])];

  // Extract agent-to-model mapping from events metadata
  const agentModels = useMemo(() => {
    const models: Record<string, string> = {};
    for (const event of run.events || []) {
      const agentId = event.agent_id || event.agent;
      const model = event.metadata?.model;
      if (agentId && model && !models[agentId]) {
        models[agentId] = model;
      }
    }
    return models;
  }, [run.events]);

  // Compute duration from events
  const duration = useMemo(() => {
    const events = run.events || [];
    if (events.length < 2) return null;
    const timestamps = events.map((e) => new Date(e.timestamp).getTime()).filter((t) => !isNaN(t));
    if (timestamps.length < 2) return null;
    const ms = Math.max(...timestamps) - Math.min(...timestamps);
    const totalSecs = Math.round(ms / 1000);
    const mins = Math.floor(totalSecs / 60);
    const secs = totalSecs % 60;
    return `${mins}m ${secs.toString().padStart(2, "0")}s`;
  }, [run.events]);

  const debateRounds = (run as any).config_overrides?.rounds || 3;

  // Stats
  const criticalCount = run.findings.filter((f) => f.severity === "critical" || f.severity === "high").length;
  const proposalCount = run.proposals.length;
  const passedCount = run.proposals.filter((p) => p.status === "accepted" || p.status === "amended").length;
  const deadlockedCount = deadlockedProposals.length;

  return (
    <div
      id="header"
      className="mb-10 pb-8 border-b"
      style={{ borderColor: "var(--cc-border)" }}
    >
      {/* Repo name + title */}
      <h1
        className="text-[32px] font-bold leading-tight mb-1"
        style={{ color: "var(--cc-text)" }}
      >
        {repoName}
      </h1>
      <h2
        className="text-[24px] font-bold leading-tight mb-5"
        style={{ color: "var(--cc-text)" }}
      >
        Codebase Intelligence Report
      </h2>

      {/* Metadata row with icons */}
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 mb-5 text-[13px]" style={{ color: "var(--cc-text-muted)" }}>
        <span className="flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5" /> {createdAt}
        </span>
        <span style={{ color: "var(--cc-border)" }}>&middot;</span>
        <span className="flex items-center gap-1.5">
          <Landmark className="w-3.5 h-3.5" /> {(run as any).config_overrides?.topology || "Adversarial"} Topology
        </span>
        <span style={{ color: "var(--cc-border)" }}>&middot;</span>
        <span className="flex items-center gap-1.5">
          <MessageSquare className="w-3.5 h-3.5" /> {debateRounds} Debate Rounds
        </span>
        {duration && (
          <>
            <span style={{ color: "var(--cc-border)" }}>&middot;</span>
            <span className="flex items-center gap-1.5">
              <Timer className="w-3.5 h-3.5" /> {duration}
            </span>
          </>
        )}
        <span style={{ color: "var(--cc-border)" }}>&middot;</span>
        <span className="flex items-center gap-1.5">
          <DollarSign className="w-3.5 h-3.5" /> ${totalCost.toFixed(2)} total cost
        </span>
      </div>

      {/* Consensus ring badge */}
      {consensusPercent > 0 && (
        <div
          className="inline-flex items-center gap-2.5 px-4 py-2 rounded-full mb-5"
          style={{
            backgroundColor: consensusPercent >= 70
              ? "rgba(0,214,143,0.1)"
              : "rgba(255,217,61,0.1)",
            border: `1px solid ${consensusPercent >= 70 ? "rgba(0,214,143,0.3)" : "rgba(255,217,61,0.3)"}`,
          }}
        >
          <ConsensusRing percent={consensusPercent} />
          <span
            className="text-[15px] font-bold"
            style={{ color: consensusPercent >= 70 ? "var(--cc-green)" : "var(--cc-yellow)" }}
          >
            {consensusPercent}% Council Consensus
          </span>
        </div>
      )}

      {/* Agent roster with model badges */}
      <div className="flex flex-wrap gap-2 mb-6">
        {agentIds.map((agentId) => {
          const color = getAgentColor(agentId);
          const agent = getAgent(agentId);
          const model = agentModels[agentId];
          return (
            <span
              key={agentId}
              className="flex items-center gap-2 px-3 py-1.5 rounded-full text-[13px] border"
              style={{
                backgroundColor: "var(--cc-bg-card)",
                borderColor: "var(--cc-border)",
              }}
            >
              <span
                className="w-2.5 h-2.5 rounded-full"
                style={{ backgroundColor: color }}
              />
              <span style={{ color: "var(--cc-text)" }}>
                {agent?.name.replace("The ", "") || agentId}
              </span>
              {model && (
                <span
                  className="px-1.5 py-0.5 rounded text-[10px] font-mono"
                  style={{
                    backgroundColor: "var(--cc-bg)",
                    color: "var(--cc-text-muted)",
                  }}
                >
                  {model}
                </span>
              )}
            </span>
          );
        })}
      </div>

      {/* Divider */}
      <div className="h-px mb-6" style={{ backgroundColor: "var(--cc-border)" }} />

      {/* Phase pipeline */}
      <div
        className="rounded-xl p-4 mb-6"
        style={{
          backgroundColor: "var(--cc-bg-card)",
          border: "1px solid var(--cc-border)",
        }}
      >
        <div className="flex items-center gap-1 overflow-x-auto pb-2">
          {RFC_PHASES.map((phase, i) => {
            const label = phase === "DEBATE" ? `DEBATE ×${debateRounds}` : phase;
            return (
              <div key={phase} className="flex items-center shrink-0">
                <span
                  className="px-3 py-1.5 rounded-md text-[11px] font-bold tracking-wide"
                  style={{
                    backgroundColor: "rgba(0,214,143,0.15)",
                    color: "var(--cc-green)",
                  }}
                >
                  {label}
                </span>
                {i < RFC_PHASES.length - 1 && (
                  <span
                    className="mx-1 text-[11px]"
                    style={{ color: "var(--cc-text-muted)" }}
                  >
                    &rarr;
                  </span>
                )}
              </div>
            );
          })}
        </div>
        {/* Progress bar */}
        <div
          className="h-1.5 rounded-full mt-2"
          style={{ backgroundColor: "var(--cc-border)" }}
        >
          <div
            className="h-full rounded-full"
            style={{
              width: "100%",
              background: "linear-gradient(90deg, var(--cc-green), var(--cc-accent))",
            }}
          />
        </div>
      </div>

      {/* Stats cards */}
      <div className="grid grid-cols-4 gap-3">
        {[
          { label: "CRITICAL FINDINGS", value: criticalCount, color: "var(--cc-red)" },
          { label: "PROPOSALS", value: proposalCount, color: "var(--cc-accent)" },
          { label: "PASSED", value: passedCount, color: "var(--cc-green)" },
          { label: "DEADLOCKED", value: deadlockedCount, color: "var(--cc-yellow)" },
        ].map((stat) => (
          <div
            key={stat.label}
            className="rounded-xl p-4 text-center border"
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
            }}
          >
            <div
              className="text-3xl font-bold italic mb-1"
              style={{ color: stat.color }}
            >
              {stat.value}
            </div>
            <div
              className="text-[10px] font-bold tracking-widest uppercase"
              style={{ color: "var(--cc-text-muted)" }}
            >
              {stat.label}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
