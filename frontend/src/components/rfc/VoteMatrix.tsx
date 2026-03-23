"use client";

import type { Vote } from "@/lib/types";
import { getAgentColor } from "@/lib/utils";

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

interface VoteMatrixProps {
  votes: Vote[];
  agentIds?: string[];
}

export function VoteMatrix({ votes, agentIds }: VoteMatrixProps) {
  const agents = agentIds || [...new Set(votes.map((v) => v.agent_id))];

  return (
    <div className="flex gap-3 mb-3">
      {agents.map((agentId) => {
        const vote = votes.find((v) => v.agent_id === agentId);
        const agentColor = getAgentColor(agentId);
        const voteType = vote?.vote_type || "abstain";
        const isYes = voteType === "approve";
        const isNo = voteType === "reject";
        const displayName = getDisplayName(agentId);
        const confidence = (vote as unknown as { confidence?: number })?.confidence;

        return (
          <div
            key={agentId}
            className={`flex flex-col items-center gap-1 px-4 py-2.5 rounded-lg min-w-[90px] ${
              isYes ? "yes-cell" : isNo ? "no-cell" : ""
            }`}
            style={{ backgroundColor: "var(--cc-bg)" }}
          >
            <span
              className="text-[11px] font-semibold"
              style={{ color: agentColor }}
            >
              {displayName}
            </span>
            <span
              className="text-base font-extrabold"
              style={{
                color: isYes
                  ? "var(--cc-green)"
                  : isNo
                  ? "var(--cc-red)"
                  : "var(--cc-text-muted)",
              }}
            >
              {isYes ? "YES" : isNo ? "NO" : voteType.toUpperCase()}
            </span>
            {confidence != null && (
              <span
                className="text-[10px]"
                style={{ color: "var(--cc-text-muted)" }}
              >
                Confidence: {confidence}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
