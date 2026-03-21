"use client";

import type { Vote } from "@/lib/types";
import { getAgentColor } from "@/lib/utils";
import { AlertTriangle } from "lucide-react";

interface DissentBlockProps {
  votes: Vote[];
  proposalTitle?: string;
}

export function DissentBlock({ votes, proposalTitle }: DissentBlockProps) {
  const dissenters = votes.filter(
    (v) => v.vote_type === "reject" || v.vote_type === "amend"
  );

  if (dissenters.length === 0) return null;

  return (
    <div
      className="rounded-lg border p-4 space-y-3"
      style={{
        backgroundColor: "#ffd93d11",
        borderColor: "#ffd93d44",
      }}
    >
      <div className="flex items-center gap-2">
        <AlertTriangle className="w-4 h-4" style={{ color: "var(--cc-yellow)" }} />
        <h4 className="text-sm font-medium" style={{ color: "var(--cc-yellow)" }}>
          Dissenting Views
          {proposalTitle && (
            <span className="font-normal" style={{ color: "var(--cc-text-muted)" }}>
              {" "}
              — {proposalTitle}
            </span>
          )}
        </h4>
      </div>

      <div className="space-y-2">
        {dissenters.map((vote) => {
          const agentColor = getAgentColor(vote.agent_id);
          return (
            <div
              key={vote.id}
              className="flex gap-3 p-3 rounded"
              style={{ backgroundColor: "var(--cc-bg-card)" }}
            >
              <div
                className="w-3 h-3 rounded-full mt-0.5 shrink-0"
                style={{ backgroundColor: agentColor }}
              />
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-medium" style={{ color: agentColor }}>
                    {vote.agent_id}
                  </span>
                  <span
                    className="text-xs px-1.5 py-0.5 rounded"
                    style={{
                      backgroundColor:
                        vote.vote_type === "reject"
                          ? "var(--cc-red)22"
                          : "var(--cc-yellow)22",
                      color:
                        vote.vote_type === "reject"
                          ? "var(--cc-red)"
                          : "var(--cc-yellow)",
                    }}
                  >
                    {vote.vote_type}
                  </span>
                </div>
                {vote.reasoning && (
                  <p className="text-xs leading-relaxed" style={{ color: "var(--cc-text-muted)" }}>
                    {vote.reasoning}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
