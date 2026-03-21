"use client";

import { useEffect, useMemo, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { useRunStore } from "@/stores/runStore";
import { getRun } from "@/lib/api";
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
      {/* ═══════ TOP BAR ═══════ */}
      <div
        className="flex items-center justify-between px-5 py-2.5 border-b shrink-0"
        style={{
          borderColor: "var(--cc-border)",
          backgroundColor: "rgba(8,8,13,0.95)",
          backdropFilter: "blur(20px)",
        }}
      >
        {/* Left: repo + status */}
        <div className="flex items-center gap-4">
          <div className="text-sm" style={{ color: "var(--cc-text-muted)" }}>
            <span className="font-semibold" style={{ color: "var(--cc-text)" }}>
              {run?.repo?.url || run?.repo?.local_path || runId}
            </span>
          </div>
          <span
            className={`px-3 py-1 rounded-xl text-[11px] font-semibold uppercase tracking-wide ${
              run?.status === "running" ? "animate-pulse-glow" : ""
            }`}
            style={{ backgroundColor: statusPill.bg, color: statusPill.color }}
          >
            {statusPill.label}
          </span>
        </div>

        {/* Center: phase indicator + round */}
        <div className="flex items-center gap-5">
          <PhaseIndicator
            currentPhase={phase}
            completedPhases={completedPhases}
          />
          <span
            className="text-[13px] font-semibold"
            style={{ color: "var(--cc-accent)" }}
          >
            Round {currentRound}/{maxRounds}
          </span>
        </div>

        {/* Right: elapsed, cost, providers, WS, RFC link */}
        <div className="flex items-center gap-4">
          <span
            className="text-xs font-mono"
            style={{ color: "var(--cc-text-muted)" }}
          >
            {elapsed}
          </span>
          <CostMeter cost={cost} budgetLimit={undefined} />
          <div className="flex gap-1">
            {providers.map((p) => (
              <span
                key={p}
                className="px-2 py-0.5 rounded text-[10px] border"
                style={{
                  backgroundColor: "var(--cc-bg-card)",
                  borderColor: "var(--cc-border)",
                  color: "var(--cc-text-muted)",
                }}
              >
                {p}
              </span>
            ))}
          </div>
          {/* WS status */}
          <div
            className="flex items-center gap-1 text-xs"
            style={{
              color:
                wsState === "connected"
                  ? "var(--cc-green)"
                  : wsState === "connecting"
                  ? "var(--cc-yellow)"
                  : "var(--cc-text-muted)",
            }}
          >
            {wsState === "connected" ? (
              <Wifi className="w-3.5 h-3.5" />
            ) : wsState === "connecting" ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <WifiOff className="w-3.5 h-3.5" />
            )}
          </div>
          {run?.status === "completed" && (
            <Link
              href={`/rfc/${runId}`}
              className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-semibold text-white transition-all duration-200"
              style={{ backgroundColor: "var(--cc-accent)" }}
            >
              <FileText className="w-3 h-3" />
              View RFC
              <ExternalLink className="w-3 h-3" />
            </Link>
          )}
        </div>
      </div>

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
