"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useRunStore } from "@/stores/runStore";
import { getRun } from "@/lib/api";
import { formatCost } from "@/lib/utils";
import { AgentPanel } from "@/components/debate/AgentPanel";
import { DebateFeed } from "@/components/debate/DebateFeed";
import { GraphVisualizer } from "@/components/debate/GraphVisualizer";
import { ProposalTracker } from "@/components/debate/ProposalTracker";
import { CostMeter } from "@/components/debate/CostMeter";
import { PhaseIndicator } from "@/components/debate/PhaseIndicator";
import { HumanReviewPanel } from "@/components/debate/HumanReviewPanel";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Wifi,
  WifiOff,
  Loader2,
  FileText,
  ExternalLink,
  AlertCircle,
  CheckCircle2,
} from "lucide-react";
import type { Phase } from "@/lib/types";

const KNOWN_AGENTS = ["archaeologist", "skeptic", "visionary", "scribe"];

const STATUS_PILL_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  running: { bg: "rgba(108,92,231,0.2)", color: "var(--cc-accent)", label: "DEBATING" },
  completed: { bg: "rgba(0,214,143,0.2)", color: "var(--cc-green)", label: "COMPLETED" },
  failed: { bg: "rgba(255,107,107,0.2)", color: "var(--cc-red)", label: "FAILED" },
  pending: { bg: "rgba(136,136,160,0.2)", color: "var(--cc-text-muted)", label: "PENDING" },
};

export default function DebatePage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showHumanReview, setShowHumanReview] = useState(false);
  const [elapsed, setElapsed] = useState("00:00");

  const {
    run,
    setRun,
    clearRun,
    addEvent,
    loadFullRun,
    phase,
    events,
    findings,
    proposals,
    cost,
    wsState,
    connectWebSocket,
    disconnectWebSocket,
  } = useRunStore();

  useEffect(() => {
    if (!runId) return;
    // Clear ALL previous run state before loading new one
    clearRun();
    setLoading(true);
    setError(null);
    getRun(runId)
      .then((r) => {
        // Load everything directly into the store — events, findings, proposals, votes
        loadFullRun(r);

        // Connect WebSocket for live updates (only if run is still in progress)
        if (r.status !== "completed" && r.status !== "failed") {
          connectWebSocket(runId);
        }
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));

    return () => {
      disconnectWebSocket();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  // Elapsed timer
  useEffect(() => {
    if (!run?.created_at) return;
    const start = new Date(run.created_at).getTime();
    const interval = setInterval(() => {
      const diff = Math.floor((Date.now() - start) / 1000);
      const m = Math.floor(diff / 60)
        .toString()
        .padStart(2, "0");
      const s = (diff % 60).toString().padStart(2, "0");
      setElapsed(`${m}:${s}`);
    }, 1000);
    return () => clearInterval(interval);
  }, [run?.created_at]);

  // Detect HITL events
  useEffect(() => {
    const hasHITL = events.some((e) => e.type === "human_review_requested");
    if (hasHITL) setShowHumanReview(true);
  }, [events]);

  // Helper to get event type/agent (handles both backend field naming conventions)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const eType = (e: any) => e.type || e.event_type || "";
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const eAgent = (e: any) => e.agent_id || e.agent || "";

  // Is run completed?
  const runCompleted = run?.status === "completed" || run?.status === "failed";

  // Track completed phases
  const completedPhases = useMemo<Phase[]>(() => {
    return events
      .filter((e) => eType(e) === "phase_completed" && e.phase)
      .map((e) => e.phase as Phase);
  }, [events]);

  // Active agents — the most recently speaking agent (not system)
  const activeAgentIds = useMemo(() => {
    if (runCompleted) return new Set<string>();
    const agentSpeaking = events.filter((e) => {
      const t = eType(e);
      const a = eAgent(e);
      return a && a !== "system" && ["agent_thinking", "agent_speaking", "agent_response", "agent_activated"].includes(t);
    });
    if (agentSpeaking.length === 0) return new Set<string>();
    const latest = agentSpeaking[agentSpeaking.length - 1];
    return new Set([eAgent(latest)].filter(Boolean));
  }, [events, runCompleted]);

  // Agent IDs — always show all 4 known agents
  const agentIds = useMemo(() => {
    const fromEvents = new Set(
      events.map((e) => eAgent(e)).filter((a) => a && a !== "system")
    );
    KNOWN_AGENTS.forEach((a) => fromEvents.add(a));
    return KNOWN_AGENTS; // Fixed order
  }, [events]);

  // Unique providers from events
  const providers = useMemo(() => {
    const provs = new Set<string>();
    events.forEach((e) => {
      const model = e.metadata?.model || (e.structured as Record<string, unknown>)?.model as string || (e.payload as Record<string, unknown>)?.model as string;
      if (model) provs.add(model);
    });
    if (provs.size === 0) {
      provs.add("GPT-4o");
    }
    return [...provs];
  }, [events]);

  // Round counter — track round_started/round_ended events from multi-round debate
  const { currentRound, maxRounds } = useMemo(() => {
    const roundEvents = events.filter((e) => eType(e) === "round_started" || eType(e) === "round_ended");
    if (roundEvents.length === 0) return { currentRound: 1, maxRounds: 3 };
    const lastRound = roundEvents[roundEvents.length - 1];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const s = (lastRound as any).structured || {};
    return {
      currentRound: s.round || 1,
      maxRounds: s.max_rounds || 3,
    };
  }, [events]);

  const configOverrides = (run as any)?.config_overrides || {};
  const topologyLabel = (configOverrides.topology || "adversarial").replace("_", " ");

  const statusPill = STATUS_PILL_STYLES[run?.status || "pending"] || STATUS_PILL_STYLES.pending;

  if (loading) {
    return (
      <div className="flex-1 p-6 space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid grid-cols-4 gap-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <Skeleton className="h-64" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4">
        <AlertCircle className="w-12 h-12" style={{ color: "var(--cc-red)" }} />
        <p className="text-lg" style={{ color: "var(--cc-text)" }}>
          {error}
        </p>
        <button
          onClick={() => router.push("/")}
          className="px-4 py-2 rounded-lg border text-sm transition-all duration-200"
          style={{
            borderColor: "var(--cc-border)",
            color: "var(--cc-text)",
            backgroundColor: "var(--cc-bg-card)",
          }}
        >
          Back to Home
        </button>
      </div>
    );
  }

  return (
    <div
      className="flex flex-col overflow-hidden"
      style={{
        backgroundColor: "var(--cc-bg)",
        height: "calc(100vh - 56px)",
      }}
    >
      {/* ═══════ TOP BAR — single row matching mockup ═══════ */}
      <div
        className="flex items-center gap-4 px-4 py-2 border-b shrink-0 overflow-x-auto"
        style={{
          borderColor: "var(--cc-border)",
          backgroundColor: "var(--cc-bg-card)",
        }}
      >
        {/* Repo name */}
        <span className="text-sm font-semibold text-[var(--cc-text)] whitespace-nowrap shrink-0">
          {(() => {
            const url = run?.repo?.url || run?.repo?.local_path || "";
            const match = url.match(/github\.com\/([^/]+\/[^/]+)/);
            return match ? match[1] : url || runId;
          })()}
        </span>

        {/* Status pill */}
        <span
          className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide shrink-0 ${
            run?.status === "running" ? "animate-pulse-glow" : ""
          }`}
          style={{ backgroundColor: statusPill.bg, color: statusPill.color }}
        >
          {statusPill.label}
        </span>

        {/* Phase dots */}
        <div className="flex items-center gap-1 shrink-0">
          {["ingestion","analysis","debate","synthesis","review","output"].map((p) => {
            const isDone = completedPhases.includes(p as any);
            const isActive = phase === p;
            return (
              <div
                key={p}
                className="w-2 h-2 rounded-full transition-all duration-300"
                style={{
                  backgroundColor: isDone ? "var(--cc-green)" : isActive ? "var(--cc-accent)" : "var(--cc-border)",
                  boxShadow: isActive ? "0 0 6px var(--cc-accent-glow)" : "none",
                }}
              />
            );
          })}
        </div>

        {/* Phase labels with arrows */}
        <div className="flex items-center gap-0 text-[11px] shrink-0 whitespace-nowrap">
          {[
            { key: "ingestion", label: "INGESTION" },
            { key: "analysis", label: "ANALYSIS" },
            { key: "debate", label: "DEBATE" },
            { key: "synthesis", label: "VOTING" },
            { key: "review", label: "SCRIBING" },
            { key: "output", label: "DONE" },
          ].map((p, i) => {
            const isDone = completedPhases.includes(p.key as any);
            const isActive = phase === p.key;
            return (
              <span key={p.key} className="flex items-center">
                {i > 0 && <span className="mx-1 text-[var(--cc-text-muted)] opacity-40">→</span>}
                <span
                  className={isActive ? "font-bold" : ""}
                  style={{
                    color: isDone ? "var(--cc-text-muted)" : isActive ? "var(--cc-text)" : "var(--cc-text-muted)",
                    opacity: isDone ? 0.5 : isActive ? 1 : 0.4,
                  }}
                >
                  {p.label}
                </span>
              </span>
            );
          })}
        </div>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Round counter */}
        <span className="text-[13px] font-bold text-[var(--cc-accent)] shrink-0 whitespace-nowrap">
          Round {currentRound}/{maxRounds}
        </span>

        {/* Elapsed */}
        <span className="text-xs font-mono text-[var(--cc-text-muted)] shrink-0">
          {elapsed}
        </span>

        {/* Cost */}
        <CostMeter cost={cost} budgetLimit={undefined} />

        {/* Provider badge */}
        {providers.length > 0 && (
          <span className="px-2 py-0.5 rounded text-[10px] font-medium border shrink-0"
            style={{ backgroundColor: "var(--cc-bg)", borderColor: "var(--cc-border)", color: "var(--cc-text-muted)" }}>
            {providers[0]}
          </span>
        )}

        {/* View RFC — shown when completed */}
        {run?.status === "completed" && (
          <Link
            href={`/rfc/${runId}`}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-[12px] font-bold text-white shrink-0 transition-all duration-200 hover-lift"
            style={{ backgroundColor: "var(--cc-accent)", boxShadow: "0 2px 8px var(--cc-accent-glow)" }}
          >
            <FileText className="w-3.5 h-3.5" />
            View RFC
            <ExternalLink className="w-3 h-3" />
          </Link>
        )}
      </div>

      {/* ═══════ COMPLETION SUMMARY ═══════ */}
      {run?.status === "completed" && (
        <div className="mx-4 mt-3 p-4 rounded-xl bg-[var(--cc-bg-card)] border border-[var(--cc-green)] border-opacity-30 flex items-center justify-between">
          <div>
            <div className="flex items-center gap-3 mb-1">
              <CheckCircle2 className="w-5 h-5 text-[var(--cc-green)]" />
              <span className="text-sm font-semibold text-[var(--cc-text)]">Analysis Complete</span>
            </div>
            <div className="flex gap-6 text-xs text-[var(--cc-text-muted)] ml-8">
              <span>{findings.length} findings</span>
              <span>{proposals.length} proposals ({proposals.filter(p => p.status === "accepted").length} passed)</span>
              <span>Consensus: {(run as any).consensus_score || 0}%</span>
              <span>Cost: {formatCost((run as any).total_cost)}</span>
            </div>
          </div>
          <Link
            href={`/rfc/${runId}`}
            className="flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-bold text-white transition-all duration-200 hover-lift shrink-0"
            style={{ backgroundColor: "var(--cc-accent)", boxShadow: "0 2px 12px var(--cc-accent-glow)" }}
          >
            <FileText className="w-4 h-4" />
            View RFC Report
            <ExternalLink className="w-3.5 h-3.5" />
          </Link>
        </div>
      )}

      {/* ═══════ MAIN 3-COLUMN GRID + BOTTOM ═══════ */}
      <div
        className="flex-1 min-h-0"
        style={{
          display: "grid",
          gridTemplateColumns: "260px 1fr 280px",
          gridTemplateRows: "1fr auto",
        }}
      >
        {/* LEFT: Agent Panels */}
        <div
          className="overflow-y-auto border-r flex flex-col"
          style={{ borderColor: "var(--cc-border)" }}
        >
          {agentIds.map((agentId) => (
            <AgentPanel
              key={agentId}
              agentId={agentId}
              events={events}
              findings={findings}
              isActive={activeAgentIds.has(agentId)}
              runCompleted={runCompleted}
            />
          ))}
        </div>

        {/* CENTER: Debate Feed */}
        <div className="overflow-hidden flex flex-col p-4">
          <DebateFeed events={events} />
        </div>

        {/* RIGHT: Graph Visualizer */}
        <div
          className="border-l p-4 flex flex-col"
          style={{ borderColor: "var(--cc-border)" }}
        >
          <GraphVisualizer
            currentPhase={phase}
            events={events}
          />
        </div>

        {/* BOTTOM: Proposal Tracker (spans all columns) */}
        <ProposalTracker proposals={proposals} />
      </div>

      {/* HITL overlay */}
      {showHumanReview && (
        <div className="fixed bottom-4 right-4 w-96 z-50">
          <HumanReviewPanel
            findings={findings.filter(
              (f) => f.severity === "critical" || f.severity === "high"
            )}
          />
        </div>
      )}
    </div>
  );
}
