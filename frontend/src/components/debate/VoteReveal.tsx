"use client";

import { useEffect, useState } from "react";
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

interface VoteRevealProps {
  votes: Vote[];
  proposalTitle?: string;
}

export function VoteReveal({ votes, proposalTitle }: VoteRevealProps) {
  const [revealed, setRevealed] = useState<number>(0);

  useEffect(() => {
    if (revealed < votes.length) {
      const timer = setTimeout(() => setRevealed((r) => r + 1), 200);
      return () => clearTimeout(timer);
    }
  }, [revealed, votes.length]);

  // Reset when votes change
  useEffect(() => {
    setRevealed(0);
  }, [votes.length]);

  const approvals = votes.filter((v) => v.vote_type === "approve").length;
  const rejections = votes.filter((v) => v.vote_type === "reject").length;
  const total = votes.length;

  return (
    <div className="space-y-3">
      {proposalTitle && (
        <h4 className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>
          {proposalTitle}
        </h4>
      )}

      {/* Vote cards */}
      <div className="flex flex-wrap gap-2">
        {votes.map((vote, i) => {
          const isVisible = i < revealed;
          const agentColor = getAgentColor(vote.agent_id);
          const voteColor = VOTE_COLORS[vote.vote_type] || "var(--cc-text-muted)";
          const Icon = VOTE_ICONS[vote.vote_type as keyof typeof VOTE_ICONS] || Minus;

          return (
            <div
              key={vote.id}
              className="flex items-center gap-2 px-3 py-2 rounded-lg border transition-all"
              style={{
                opacity: isVisible ? 1 : 0,
                transform: isVisible ? "scale(1)" : "scale(0.8)",
                transition: "all 0.3s ease",
                backgroundColor: `${voteColor}11`,
                borderColor: agentColor,
              }}
            >
              <div
                className="w-2 h-2 rounded-full"
                style={{ backgroundColor: agentColor }}
              />
              <span className="text-xs" style={{ color: "var(--cc-text)" }}>
                {vote.agent_id}
              </span>
              <Icon className="w-3 h-3" style={{ color: voteColor }} />
              <span className="text-xs font-medium" style={{ color: voteColor }}>
                {vote.vote_type}
              </span>
            </div>
          );
        })}
      </div>

      {/* Tally */}
      {revealed >= votes.length && votes.length > 0 && (
        <div
          className="flex items-center gap-4 text-sm font-medium"
          style={{
            opacity: revealed >= votes.length ? 1 : 0,
            transition: "opacity 0.5s ease",
          }}
        >
          <span style={{ color: "var(--cc-green)" }}>
            ✓ {approvals} approve
          </span>
          <span style={{ color: "var(--cc-red)" }}>
            ✗ {rejections} reject
          </span>
          <span style={{ color: "var(--cc-text-muted)" }}>
            {total - approvals - rejections} other
          </span>
        </div>
      )}
    </div>
  );
}
