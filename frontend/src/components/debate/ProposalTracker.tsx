"use client";

import type { Proposal } from "@/lib/types";
import { getAgentColor } from "@/lib/utils";

const STATUS_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  pending: { bg: "var(--cc-bg-hover)", color: "var(--cc-text-muted)", label: "PENDING" },
  voting: { bg: "var(--cc-accent-muted)", color: "var(--cc-accent)", label: "VOTING" },
  accepted: { bg: "var(--cc-green-muted)", color: "var(--cc-green)", label: "PASSED" },
  rejected: { bg: "var(--cc-red-muted)", color: "var(--cc-red)", label: "REJECTED" },
  amended: { bg: "var(--cc-yellow-muted)", color: "var(--cc-yellow)", label: "REVISED" },
  proposed: { bg: "var(--cc-accent-muted)", color: "var(--cc-accent)", label: "PROPOSED" },
  revised: { bg: "var(--cc-yellow-muted)", color: "var(--cc-yellow)", label: "REVISED" },
  withdrawn: { bg: "var(--cc-bg-hover)", color: "var(--cc-text-muted)", label: "WITHDRAWN" },
  deadlocked: { bg: "var(--cc-red-muted)", color: "var(--cc-red)", label: "DEADLOCKED" },
};

const EFFORT_STYLES: Record<string, { bg: string; color: string }> = {
  XS: { bg: "var(--cc-green-muted)", color: "var(--cc-green)" },
  S: { bg: "var(--cc-green-muted)", color: "var(--cc-green)" },
  M: { bg: "var(--cc-yellow-muted)", color: "var(--cc-yellow)" },
  L: { bg: "var(--cc-red-muted)", color: "var(--cc-red)" },
  XL: { bg: "var(--cc-red-muted)", color: "var(--cc-red)" },
};

function ProposalCard({ proposal }: { proposal: Proposal }) {
  const status = STATUS_STYLES[proposal.status] || STATUS_STYLES.pending;
  const isDeadlocked = proposal.status === "deadlocked" ||
    (proposal.status === "rejected" && (proposal.votes?.length ?? 0) > 0);
  const effort = proposal.effort ? (EFFORT_STYLES[proposal.effort] || null) : null;
  const author = proposal.author_agent || proposal.agent_id || "unknown";
  const displayId = `P-${proposal.proposal_number ?? "?"}`;

  return (
    <div
      className="shrink-0 rounded-[10px] border transition-all duration-200"
      style={{
        minWidth: "220px",
        padding: "12px 16px",
        backgroundColor: "var(--cc-bg)",
        borderColor: isDeadlocked
          ? "var(--cc-red)"
          : proposal.status === "amended" || proposal.status === "revised"
          ? "var(--cc-yellow)"
          : "var(--cc-border)",
        borderWidth: isDeadlocked ? "2px" : "1px",
      }}
    >
      {/* Header: ID + Status */}
      <div className="flex items-center justify-between mb-1.5">
        <span
          className="text-[11px] font-mono"
          style={{ color: "var(--cc-text-muted)" }}
        >
          {displayId}
        </span>
        <span
          className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase"
          style={{ backgroundColor: status.bg, color: status.color }}
        >
          {status.label}
        </span>
      </div>

      {/* Title + Effort badge */}
      <div className="flex items-start gap-1.5 mb-1">
        <div
          className="text-[13px] font-semibold flex-1"
          style={{ color: "var(--cc-text)" }}
        >
          {proposal.title}
        </div>
        {effort && proposal.effort && (
          <span
            className="shrink-0 px-1.5 py-0.5 rounded text-[10px] font-semibold"
            style={{ backgroundColor: effort.bg, color: effort.color }}
          >
            {proposal.effort}
          </span>
        )}
      </div>

      {/* Author */}
      <div
        className="text-[11px] mb-2"
        style={{ color: "var(--cc-text-muted)" }}
      >
        by {author}
      </div>

      {/* Vote tally dots */}
      {proposal.votes && proposal.votes.length > 0 && (
        <div className="flex gap-1.5 mt-2">
          {proposal.votes.map((v) => {
            const isYes = v.vote_type === "approve" || v.vote === "YES";
            const isNo = v.vote_type === "reject" || v.vote === "NO";
            const isAbstain = !isYes && !isNo;
            return (
              <div
                key={v.id}
                className="w-6 h-6 rounded-md flex items-center justify-center text-[10px] font-bold"
                style={{
                  backgroundColor: isYes
                    ? "var(--cc-green-muted)"
                    : isNo
                    ? "var(--cc-red-muted)"
                    : "var(--cc-bg-hover)",
                  color: isYes
                    ? "var(--cc-green)"
                    : isNo
                    ? "var(--cc-red)"
                    : "var(--cc-text-muted)",
                }}
              >
                {isYes ? "Y" : isNo ? "N" : "-"}
              </div>
            );
          })}
          {/* Show pending dots if less than 3 votes */}
          {proposal.votes.length < 3 &&
            Array.from({ length: 3 - proposal.votes.length }).map((_, i) => (
              <div
                key={`pending-${i}`}
                className="w-6 h-6 rounded-md flex items-center justify-center text-[10px] font-bold border border-dashed"
                style={{
                  backgroundColor: "var(--cc-bg-card)",
                  borderColor: "var(--cc-border)",
                  color: "var(--cc-text-muted)",
                }}
              >
                ?
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

interface ProposalTrackerProps {
  proposals: Proposal[];
}

export function ProposalTracker({ proposals }: ProposalTrackerProps) {
  const passed = proposals.filter((p) => p.status === "accepted").length;
  const rejected = proposals.filter((p) => p.status === "rejected").length;
  const amended = proposals.filter(
    (p) => p.status === "amended" || p.status === "revised"
  ).length;

  return (
    <div
      role="region"
      aria-label="Proposal tracker"
      className="border-t"
      style={{
        gridColumn: "1 / -1",
        padding: "14px 20px",
        backgroundColor: "var(--cc-bg-card)",
        borderColor: "var(--cc-border)",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2.5">
        <h3
          className="text-[13px] font-semibold"
          style={{ color: "var(--cc-text)" }}
        >
          Proposal Tracker
        </h3>
        <div
          className="text-xs"
          style={{ color: "var(--cc-text-muted)" }}
        >
          {proposals.length} proposals
          {passed > 0 && ` \u00b7 ${passed} passed`}
          {amended > 0 && ` \u00b7 ${amended} revised`}
          {rejected > 0 && ` \u00b7 ${rejected} rejected`}
        </div>
      </div>

      {/* Cards - horizontal scroll */}
      {proposals.length === 0 ? (
        <div
          className="py-4 text-center text-xs"
          style={{ color: "var(--cc-text-muted)" }}
        >
          No proposals yet...
        </div>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-1">
          {proposals.map((p) => (
            <ProposalCard key={p.id} proposal={p} />
          ))}
        </div>
      )}
    </div>
  );
}
