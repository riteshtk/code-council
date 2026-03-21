"use client";

import type { Phase } from "@/lib/types";
import { cn } from "@/lib/utils";

const PHASES: Phase[] = [
  "ingestion",
  "analysis",
  "debate",
  "synthesis",
  "review",
  "output",
];

const PHASE_COLORS: Record<Phase, string> = {
  ingestion: "#4ecdc4",
  analysis: "#d4a574",
  debate: "#6c5ce7",
  synthesis: "#00d68f",
  review: "#ffd93d",
  output: "#ff6b6b",
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
    <div className="flex items-center gap-1">
      {PHASES.map((phase, i) => {
        const isDone = completedPhases.includes(phase);
        const isActive = currentPhase === phase;
        const color = PHASE_COLORS[phase];

        return (
          <div key={phase} className="flex items-center">
            {i > 0 && (
              <div
                className="h-px w-4"
                style={{
                  backgroundColor: isDone || isActive ? color : "var(--cc-border)",
                }}
              />
            )}
            <div className="relative flex items-center justify-center group">
              <div
                className={cn(
                  "w-3 h-3 rounded-full transition-all",
                  isActive && "scale-150"
                )}
                style={{
                  backgroundColor: isActive
                    ? color
                    : isDone
                    ? `${color}88`
                    : "var(--cc-border)",
                  boxShadow: isActive ? `0 0 8px ${color}` : "none",
                }}
              />
              {/* Tooltip */}
              <div
                className="absolute bottom-full mb-1 px-2 py-1 rounded text-xs whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none z-10"
                style={{
                  backgroundColor: "var(--cc-bg-card)",
                  color: isActive ? color : "var(--cc-text-muted)",
                  border: `1px solid var(--cc-border)`,
                }}
              >
                {phase}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
