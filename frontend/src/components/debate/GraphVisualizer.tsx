"use client";

import { useMemo } from "react";
import type { Phase, Event } from "@/lib/types";

/* ── Phase pipeline definition ── */
const PIPELINE = [
  { id: "ingestion" as Phase, label: "INGEST",  icon: "📥", color: "#8888a0", glow: "rgba(136,136,160,0.3)" },
  { id: "analysis" as Phase,  label: "ANALYSE", icon: "🔍", color: "#d4a574", glow: "rgba(212,165,116,0.3)" },
  { id: "debate" as Phase,    label: "DEBATE",  icon: "⚔️", color: "#6c5ce7", glow: "rgba(108,92,231,0.3)" },
  { id: "synthesis" as Phase, label: "VOTING",  icon: "🗳️", color: "#00d68f", glow: "rgba(0,214,143,0.3)" },
  { id: "review" as Phase,    label: "SCRIBING",icon: "📝", color: "#4ecdc4", glow: "rgba(78,205,196,0.3)" },
  { id: "output" as Phase,    label: "DONE",    icon: "✅", color: "#00d68f", glow: "rgba(0,214,143,0.3)" },
];

/* ── Determine phase state from events ── */
function computePhaseStates(events: Event[], currentPhase: Phase | null | undefined) {
  // Map backend phase names to our pipeline IDs
  const normalize = (p: string): Phase | null => {
    const map: Record<string, Phase> = {
      ingesting: "ingestion", ingestion: "ingestion",
      analysing: "analysis", analysis: "analysis",
      opening: "debate", debating: "debate", debate: "debate",
      voting: "synthesis", synthesis: "synthesis",
      scribing: "review", review: "review",
      output: "output", done: "output",
    };
    return map[p?.toLowerCase()] || null;
  };

  const completed = new Set<Phase>();
  let active: Phase | null = null;

  // Walk events to determine completed phases
  for (const e of events) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const ea = e as any;
    const eventType = ea.type || ea.event_type || "";
    const phase = ea.phase || "";

    if (eventType === "phase_completed" || eventType === "ingest_completed") {
      const mapped = normalize(phase);
      if (mapped) completed.add(mapped);
      // ingest_completed means ingestion is done
      if (eventType === "ingest_completed") completed.add("ingestion");
    }
    if (eventType === "phase_started") {
      const mapped = normalize(phase);
      if (mapped) active = mapped;
    }
    if (eventType === "run_completed") {
      // All phases done
      PIPELINE.forEach((p) => completed.add(p.id));
      active = null;
    }
  }

  // Override with currentPhase from store if available
  if (currentPhase) {
    active = currentPhase;
  }

  return { completed, active };
}

interface GraphVisualizerProps {
  currentPhase?: Phase | null;
  completedPhases?: Phase[];
  events?: Event[];
}

export function GraphVisualizer({
  currentPhase,
  events = [],
}: GraphVisualizerProps) {
  const { completed, active } = useMemo(
    () => computePhaseStates(events, currentPhase),
    [events, currentPhase]
  );

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-[13px] font-semibold text-[var(--cc-text)]">
          Pipeline Status
        </h3>
      </div>

      <div className="flex-1 rounded-xl border border-[var(--cc-border)] bg-[var(--cc-bg-card)] p-4 flex flex-col justify-between gap-0">
        {PIPELINE.map((phase, i) => {
          const isDone = completed.has(phase.id);
          const isActive = active === phase.id;
          const isPending = !isDone && !isActive;

          // Edge state
          const prevDone = i > 0 && completed.has(PIPELINE[i - 1].id);
          const prevActive = i > 0 && active === PIPELINE[i - 1].id;

          return (
            <div key={phase.id} className="flex flex-col items-center">
              {/* Edge connector (above node, not on first) */}
              {i > 0 && (
                <div className="flex flex-col items-center" style={{ height: "20px" }}>
                  <div
                    className="w-0.5 flex-1 rounded-full transition-all duration-500"
                    style={{
                      backgroundColor: prevDone
                        ? "var(--cc-green)"
                        : prevActive
                        ? phase.color
                        : "var(--cc-border)",
                      opacity: prevDone ? 0.6 : 1,
                      boxShadow: prevActive ? `0 0 8px ${phase.glow}` : "none",
                    }}
                  />
                  {/* Animated dot traveling down the edge when active */}
                  {prevActive && (
                    <div
                      className="w-1.5 h-1.5 rounded-full absolute"
                      style={{
                        backgroundColor: phase.color,
                        boxShadow: `0 0 6px ${phase.glow}`,
                        animation: "edge-flow 1.5s ease-in-out infinite",
                      }}
                    />
                  )}
                </div>
              )}

              {/* Node */}
              <div
                className="relative flex items-center gap-2.5 w-full rounded-lg border-2 px-3 py-2 transition-all duration-500 cursor-default"
                style={{
                  borderColor: isDone
                    ? "var(--cc-green)"
                    : isActive
                    ? phase.color
                    : "var(--cc-border)",
                  backgroundColor: isDone
                    ? "rgba(0,214,143,0.06)"
                    : isActive
                    ? `${phase.color}12`
                    : "transparent",
                  opacity: isPending ? 0.4 : 1,
                  boxShadow: isActive
                    ? `0 0 20px ${phase.glow}, inset 0 0 15px ${phase.glow}`
                    : "none",
                }}
              >
                {/* Status indicator */}
                <div
                  className="w-6 h-6 rounded-md flex items-center justify-center text-[11px] shrink-0 transition-all duration-500"
                  style={{
                    backgroundColor: isDone
                      ? "rgba(0,214,143,0.15)"
                      : isActive
                      ? `${phase.color}20`
                      : "var(--cc-bg-hover)",
                  }}
                >
                  {isDone ? (
                    <span className="text-[var(--cc-green)] text-xs font-bold">✓</span>
                  ) : isActive ? (
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{
                        backgroundColor: phase.color,
                        boxShadow: `0 0 8px ${phase.glow}`,
                        animation: "pulse-glow 1.5s ease-in-out infinite",
                      }}
                    />
                  ) : (
                    <span className="w-1.5 h-1.5 rounded-full bg-[var(--cc-border)]" />
                  )}
                </div>

                {/* Label */}
                <span
                  className="text-[11px] font-bold tracking-wide transition-colors duration-300"
                  style={{
                    color: isDone
                      ? "var(--cc-green)"
                      : isActive
                      ? phase.color
                      : "var(--cc-text-muted)",
                  }}
                >
                  {phase.label}
                </span>

                {/* Active pulse ring */}
                {isActive && (
                  <div
                    className="absolute -inset-[2px] rounded-lg border-2 pointer-events-none"
                    style={{
                      borderColor: phase.color,
                      animation: "ring-pulse 2s ease-out infinite",
                      opacity: 0.4,
                    }}
                  />
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
