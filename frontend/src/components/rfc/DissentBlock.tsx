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

interface DissentBlockProps {
  votes: Vote[];
  proposalTitle?: string;
}

export function DissentBlock({ votes }: DissentBlockProps) {
  const dissenters = votes.filter(
    (v) => v.vote_type === "reject" || v.vote_type === "amend"
  );

  if (dissenters.length === 0) return null;

  return (
    <>
      {dissenters.map((vote) => {
        const displayName = getDisplayName(vote.agent_id);
        return (
          <div
            key={vote.id}
            className="rounded-lg mt-3"
            style={{
              padding: "14px 18px",
              backgroundColor: "rgba(255,217,61,0.06)",
              border: "1px solid rgba(255,217,61,0.2)",
            }}
          >
            <div
              className="text-xs font-bold mb-1.5 flex items-center gap-1.5"
              style={{ color: "var(--cc-yellow)" }}
            >
              Preserved Dissent &mdash; {displayName}
            </div>
            {vote.reasoning && (
              <div
                className="text-[13px] leading-relaxed italic"
                style={{ color: "var(--cc-text)" }}
              >
                &ldquo;{vote.reasoning}&rdquo;
              </div>
            )}
          </div>
        );
      })}
    </>
  );
}
