"use client";

import type { Vote } from "@/lib/types";
import { getAgentColor } from "@/lib/utils";
import { ThumbsUp, ThumbsDown, Minus, Edit3 } from "lucide-react";

const VOTE_ICONS = {
  approve: ThumbsUp,
  reject: ThumbsDown,
  abstain: Minus,
  amend: Edit3,
};

const VOTE_COLORS: Record<string, string> = {
  approve: "var(--cc-green)",
  reject: "var(--cc-red)",
  abstain: "var(--cc-text-muted)",
  amend: "var(--cc-yellow)",
};

interface VoteMatrixProps {
  votes: Vote[];
  agentIds?: string[];
}

export function VoteMatrix({ votes, agentIds }: VoteMatrixProps) {
  const agents = agentIds || [...new Set(votes.map((v) => v.agent_id))];

  return (
    <div className="flex flex-wrap gap-2">
      {agents.map((agentId) => {
        const vote = votes.find((v) => v.agent_id === agentId);
        const agentColor = getAgentColor(agentId);
        const voteType = vote?.vote_type || "abstain";
        const voteColor = VOTE_COLORS[voteType];
        const Icon = VOTE_ICONS[voteType as keyof typeof VOTE_ICONS] || Minus;

        return (
          <div
            key={agentId}
            className="flex items-center gap-2 px-2 py-1.5 rounded border text-xs"
            style={{
              backgroundColor: `${voteColor}11`,
              borderColor: agentColor,
            }}
            title={vote?.reasoning || voteType}
          >
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: agentColor }}
            />
            <span style={{ color: "var(--cc-text)" }}>{agentId}</span>
            <Icon className="w-3 h-3" style={{ color: voteColor }} />
          </div>
        );
      })}
    </div>
  );
}
