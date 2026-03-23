"use client";

import type { Phase } from "@/lib/types";

const PHASES: Phase[] = [
  "ingestion",
  "analysis",
  "debate",
  "synthesis",
  "review",
  "output",
];

const PHASE_LABELS: Record<Phase, string> = {
  ingestion: "INGESTION",
  analysis: "ANALYSIS",
  debate: "DEBATE",
  synthesis: "VOTING",
  review: "SCRIBING",
  output: "DONE",
};

interface PhaseIndicatorProps {
  currentPhase?: Phase | null;
  completedPhases?: Phase[];
}

export function PhaseIndicator({
  currentPhase,
  completedPhases = [],
}: PhaseIndicatorProps) {
  return (
    <div className="flex items-center gap-4">
      {/* Phase dots */}
      <div className="flex gap-1 items-center">
        {PHASES.map((phase) => {
          const isDone = completedPhases.includes(phase);
          const isActive = currentPhase === phase;
          return (
            <div
              key={phase}
              className={`w-2 h-2 rounded-full transition-all duration-300 ${
                isActive ? "animate-pulse-glow" : ""
              }`}
              style={{
                backgroundColor: isDone
                  ? "var(--cc-green)"
                  : isActive
                  ? "var(--cc-accent)"
                  : "var(--cc-border)",
                boxShadow: isActive
                  ? "0 0 8px var(--cc-accent-glow)"
                  : "none",
              }}
            />
          );
        })}
        {/* Phase label text */}
        <span
          className="text-xs ml-2 font-mono"
          style={{ color: "var(--cc-text-muted)" }}
        >
          {PHASES.map((phase) => {
            const isDone = completedPhases.includes(phase);
            const isActive = currentPhase === phase;
            if (isActive) {
              return (
                <span key={phase} className="font-bold" style={{ color: "var(--cc-text)" }}>
                  {PHASE_LABELS[phase]}
                </span>
              );
            }
            if (isDone) {
              return (
                <span key={phase} style={{ color: "var(--cc-text-muted)" }}>
                  {PHASE_LABELS[phase]}
                </span>
              );
            }
            return null;
          }).filter(Boolean).reduce<React.ReactNode[]>((acc, el, i) => {
            if (i > 0) acc.push(<span key={`sep-${i}`}> &rarr; </span>);
            acc.push(el);
            return acc;
          }, [])}
        </span>
      </div>
    </div>
  );
}
