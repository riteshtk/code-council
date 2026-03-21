"use client";

import type { Proposal, Vote } from "@/lib/types";
import { getAgentColor } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Badge } from "@/components/ui/badge";
import { ThumbsUp, ThumbsDown, Minus, Edit3 } from "lucide-react";

const STATUS_COLORS: Record<string, string> = {
  pending: "var(--cc-text-muted)",
  voting: "var(--cc-yellow)",
  accepted: "var(--cc-green)",
  rejected: "var(--cc-red)",
  amended: "var(--cc-blue)",
};

const VOTE_ICONS: Record<string, React.ReactNode> = {
  approve: <ThumbsUp className="w-3 h-3" />,
  reject: <ThumbsDown className="w-3 h-3" />,
  abstain: <Minus className="w-3 h-3" />,
  amend: <Edit3 className="w-3 h-3" />,
};

const VOTE_COLORS: Record<string, string> = {
  approve: "var(--cc-green)",
  reject: "var(--cc-red)",
  abstain: "var(--cc-text-muted)",
  amend: "var(--cc-yellow)",
};

function VoteDot({ vote }: { vote: Vote }) {
  const agentColor = getAgentColor(vote.agent_id);
  const voteColor = VOTE_COLORS[vote.vote_type] || "var(--cc-text-muted)";

  return (
    <div
      className="flex items-center justify-center w-6 h-6 rounded-full border"
      style={{
        borderColor: agentColor,
        backgroundColor: `${voteColor}22`,
        color: voteColor,
      }}
      title={`${vote.agent_id}: ${vote.vote_type}`}
    >
      {VOTE_ICONS[vote.vote_type] || <Minus className="w-3 h-3" />}
    </div>
  );
}

function ProposalCard({ proposal }: { proposal: Proposal }) {
  const statusColor = STATUS_COLORS[proposal.status] || "var(--cc-text-muted)";

  return (
    <div
      className="flex-shrink-0 w-64 rounded-lg border p-3 mr-3"
      style={{
        backgroundColor: "var(--cc-bg)",
        borderColor: proposal.status === "accepted"
          ? "var(--cc-green)"
          : proposal.status === "rejected"
          ? "var(--cc-red)"
          : "var(--cc-border)",
      }}
    >
      <div className="flex items-start justify-between gap-2 mb-2">
        <div
          className="text-xs font-medium leading-tight flex-1"
          style={{ color: "var(--cc-text)" }}
        >
          {proposal.title}
        </div>
        <Badge
          variant="outline"
          className="text-xs shrink-0"
          style={{
            borderColor: `${statusColor}66`,
            color: statusColor,
            backgroundColor: `${statusColor}11`,
          }}
        >
          {proposal.status}
        </Badge>
      </div>

      <p
        className="text-xs leading-relaxed mb-2 line-clamp-2"
        style={{ color: "var(--cc-text-muted)" }}
      >
        {proposal.description}
      </p>

      {/* Vote dots */}
      {proposal.votes && proposal.votes.length > 0 && (
        <div className="flex items-center gap-1.5 mt-2">
          <span className="text-xs" style={{ color: "var(--cc-text-muted)" }}>
            Votes:
          </span>
          {proposal.votes.map((v) => (
            <VoteDot key={v.id} vote={v} />
          ))}
        </div>
      )}

      {/* Vote tally */}
      {proposal.votes && proposal.votes.length > 0 && (
        <div className="flex items-center gap-3 mt-2 text-xs" style={{ color: "var(--cc-text-muted)" }}>
          <span style={{ color: "var(--cc-green)" }}>
            ↑{proposal.votes.filter((v) => v.vote_type === "approve").length}
          </span>
          <span style={{ color: "var(--cc-red)" }}>
            ↓{proposal.votes.filter((v) => v.vote_type === "reject").length}
          </span>
          {proposal.votes.filter((v) => v.vote_type === "amend").length > 0 && (
            <span style={{ color: "var(--cc-yellow)" }}>
              ✎{proposal.votes.filter((v) => v.vote_type === "amend").length}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

interface ProposalTrackerProps {
  proposals: Proposal[];
}

export function ProposalTracker({ proposals }: ProposalTrackerProps) {
  return (
    <div
      className="rounded-lg border overflow-hidden"
      style={{
        backgroundColor: "var(--cc-bg-card)",
        borderColor: "var(--cc-border)",
      }}
    >
      <div
        className="flex items-center justify-between px-3 py-2 border-b"
        style={{ borderColor: "var(--cc-border)" }}
      >
        <h3 className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>
          Proposals
        </h3>
        <Badge
          variant="outline"
          className="text-xs"
          style={{ color: "var(--cc-text-muted)", borderColor: "var(--cc-border)" }}
        >
          {proposals.length}
        </Badge>
      </div>

      {proposals.length === 0 ? (
        <div
          className="py-6 text-center text-xs"
          style={{ color: "var(--cc-text-muted)" }}
        >
          No proposals yet…
        </div>
      ) : (
        <div className="p-3 overflow-x-auto">
          <div className="flex">
            {proposals.map((p) => (
              <ProposalCard key={p.id} proposal={p} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
