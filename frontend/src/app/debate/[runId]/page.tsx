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
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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

const WS_STATUS_COLOR: Record<string, string> = {
  connecting: "var(--cc-yellow)",
  connected: "var(--cc-green)",
  disconnected: "var(--cc-text-muted)",
  error: "var(--cc-red)",
};

export default function DebatePage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const router = useRouter();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showHumanReview, setShowHumanReview] = useState(false);

  const {
    run,
    setRun,
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
    setLoading(true);
    getRun(runId)
      .then((r) => {
        setRun(r);
        connectWebSocket(runId);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));

    return () => {
      disconnectWebSocket();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId]);

  // Detect HITL events
  useEffect(() => {
    const hasHITL = events.some((e) => e.type === "human_review_requested");
    if (hasHITL) setShowHumanReview(true);
  }, [events]);

  // Track completed phases
  const completedPhases = useMemo<Phase[]>(() => {
    return events
      .filter((e) => e.type === "phase_completed" && e.phase)
      .map((e) => e.phase as Phase);
  }, [events]);

  // Active agents (those currently thinking)
  const activeAgentIds = useMemo(() => {
    const last = events.filter((e) => e.type === "agent_thinking");
    if (last.length === 0) return new Set<string>();
    const latest = last[last.length - 1];
    return new Set([latest.agent_id].filter(Boolean) as string[]);
  }, [events]);

  // Determine displayed agents from events + known agents
  const agentIds = useMemo(() => {
    const fromEvents = new Set(
      events.map((e) => e.agent_id).filter(Boolean) as string[]
    );
    KNOWN_AGENTS.forEach((a) => fromEvents.add(a));
    return [...fromEvents];
  }, [events]);

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
        <Button onClick={() => router.push("/")} variant="outline">
          Back to Home
        </Button>
      </div>
    );
  }

  return (
    <div
      className="flex-1 flex flex-col gap-3 p-3 overflow-hidden"
      style={{ backgroundColor: "var(--cc-bg)" }}
    >
      {/* Top bar */}
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <h1
                className="text-base font-semibold truncate"
                style={{ color: "var(--cc-text)" }}
              >
                {run?.repo?.url || run?.repo?.local_path || runId}
              </h1>
              {run?.status && (
                <Badge
                  variant="outline"
                  className="text-xs shrink-0"
                  style={{
                    color:
                      run.status === "running"
                        ? "var(--cc-yellow)"
                        : run.status === "completed"
                        ? "var(--cc-green)"
                        : run.status === "failed"
                        ? "var(--cc-red)"
                        : "var(--cc-text-muted)",
                  }}
                >
                  {run.status === "running" && (
                    <Loader2 className="w-3 h-3 mr-1 animate-spin" />
                  )}
                  {run.status}
                </Badge>
              )}
            </div>
            <div className="text-xs mt-0.5" style={{ color: "var(--cc-text-muted)" }}>
              Run ID: {runId}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          {/* Phase indicator */}
          <PhaseIndicator
            currentPhase={phase}
            completedPhases={completedPhases}
          />

          {/* WS status */}
          <div
            className="flex items-center gap-1.5 text-xs"
            style={{ color: WS_STATUS_COLOR[wsState] }}
          >
            {wsState === "connected" ? (
              <Wifi className="w-4 h-4" />
            ) : wsState === "connecting" ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <WifiOff className="w-4 h-4" />
            )}
            {wsState}
          </div>

          {/* Cost */}
          <CostMeter cost={cost} budgetLimit={undefined} />

          {/* RFC link */}
          {run?.status === "completed" && (
            <Link href={`/rfc/${runId}`}>
              <Button
                size="sm"
                className="text-xs"
                style={{ backgroundColor: "var(--cc-accent)", color: "white" }}
              >
                <FileText className="w-3 h-3 mr-1" />
                View RFC
                <ExternalLink className="w-3 h-3 ml-1" />
              </Button>
            </Link>
          )}
        </div>
      </div>

      {/* Graph */}
      <GraphVisualizer
        currentPhase={phase}
        completedPhases={completedPhases}
      />

      {/* Main grid */}
      <div className="flex-1 grid grid-cols-12 gap-3 min-h-0 overflow-hidden">
        {/* Left: Agent panels */}
        <div className="col-span-3 flex flex-col gap-2 overflow-y-auto">
          {agentIds.map((agentId) => (
            <AgentPanel
              key={agentId}
              agentId={agentId}
              events={events}
              findings={findings}
              isActive={activeAgentIds.has(agentId)}
            />
          ))}
        </div>

        {/* Center: Debate feed */}
        <div className="col-span-6 flex flex-col min-h-0">
          <DebateFeed events={events} />
        </div>

        {/* Right: Proposals + Stats */}
        <div className="col-span-3 flex flex-col gap-3 overflow-y-auto">
          {/* Finding summary */}
          <div
            className="rounded-lg border p-3"
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
            }}
          >
            <h3
              className="text-xs font-medium mb-2"
              style={{ color: "var(--cc-text-muted)" }}
            >
              Findings
            </h3>
            <div className="grid grid-cols-3 gap-2">
              {(["critical", "high", "medium"] as const).map((sev) => {
                const count = findings.filter((f) => f.severity === sev).length;
                const colors: Record<string, string> = {
                  critical: "var(--cc-red)",
                  high: "#ff9500",
                  medium: "var(--cc-yellow)",
                };
                return (
                  <div key={sev} className="text-center">
                    <div
                      className="text-xl font-bold"
                      style={{ color: colors[sev] }}
                    >
                      {count}
                    </div>
                    <div
                      className="text-xs"
                      style={{ color: "var(--cc-text-muted)" }}
                    >
                      {sev}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* HITL toggle */}
          {showHumanReview && (
            <HumanReviewPanel findings={findings.filter((f) => f.severity === "critical" || f.severity === "high")} />
          )}
        </div>
      </div>

      {/* Bottom: Proposals */}
      <ProposalTracker proposals={proposals} />
    </div>
  );
}
