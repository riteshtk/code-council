"use client";

import { useMemo } from "react";
import { getAgentColor } from "@/lib/utils";
import type { Event, Finding } from "@/lib/types";

const AGENT_INITIALS: Record<string, string> = {
  archaeologist: "AR",
  skeptic: "SK",
  visionary: "VI",
  scribe: "SC",
};

const AGENT_DISPLAY_NAMES: Record<string, string> = {
  archaeologist: "The Archaeologist",
  skeptic: "The Skeptic",
  visionary: "The Visionary",
  scribe: "The Scribe",
};

function matchAgent(agentId: string, eventAgent: string | undefined): boolean {
  if (!eventAgent) return false;
  const a = agentId.toLowerCase();
  const b = eventAgent.toLowerCase();
  return a === b || b.includes(a) || a.includes(b);
}

function getInitials(agentId: string): string {
  const lower = agentId.toLowerCase();
  for (const [key, val] of Object.entries(AGENT_INITIALS)) {
    if (lower.includes(key)) return val;
  }
  return agentId.slice(0, 2).toUpperCase();
}

function getDisplayName(agentId: string): string {
  const lower = agentId.toLowerCase();
  for (const [key, val] of Object.entries(AGENT_DISPLAY_NAMES)) {
    if (lower.includes(key)) return val;
  }
  return agentId;
}

interface AgentPanelProps {
  agentId: string;
  agentName?: string;
  events: Event[];
  findings: Finding[];
  isActive?: boolean;
  runCompleted?: boolean;
}

export function AgentPanel({
  agentId,
  events,
  findings,
  isActive = false,
  runCompleted = false,
}: AgentPanelProps) {
  const color = getAgentColor(agentId);
  const initials = getInitials(agentId);
  const displayName = getDisplayName(agentId);

  // Filter events for this agent — handle both agent_id and agent field names
  const agentEvents = useMemo(
    () => events.filter((e) => matchAgent(agentId, e.agent_id || e.agent)),
    [events, agentId]
  );

  // Filter findings for this agent
  const agentFindings = useMemo(
    () => findings.filter((f) => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const fa = f as any; const fAgent = fa.agent_id || fa.agent || "";
      return matchAgent(agentId, fAgent);
    }),
    [findings, agentId]
  );

  // Get last speaking/response event content
  const lastSpeakEvent = useMemo(() => {
    const speaking = agentEvents.filter((e) => {
      const t = e.type || e.event_type || "";
      return ["agent_speaking", "agent_response", "agent_thinking", "finding_emitted", "proposal_created", "vote_cast"].includes(t);
    });
    return speaking[speaking.length - 1] || null;
  }, [agentEvents]);

  const streamingText = lastSpeakEvent
    ? (lastSpeakEvent.content || (lastSpeakEvent.payload as Record<string, unknown>)?.content as string || (lastSpeakEvent.payload as Record<string, unknown>)?.text as string || "")
    : "";

  // Determine status
  const effectiveActive = isActive && !runCompleted;
  const statusLabel = effectiveActive
    ? "Speaking..."
    : runCompleted
    ? `Done · ${agentFindings.length} findings`
    : agentEvents.length > 0
    ? `Done · ${agentFindings.length} findings`
    : "Waiting";

  // Count findings by severity
  const criticalCount = agentFindings.filter((f) => {
    const sev = ((f as unknown as Record<string, unknown>).severity as string || "").toLowerCase();
    return sev === "critical";
  }).length;
  const highCount = agentFindings.filter((f) => {
    const sev = ((f as unknown as Record<string, unknown>).severity as string || "").toLowerCase();
    return sev === "high";
  }).length;
  const medCount = agentFindings.filter((f) => {
    const sev = ((f as unknown as Record<string, unknown>).severity as string || "").toLowerCase();
    return sev === "medium";
  }).length;

  // Vote events
  const voteEvents = agentEvents.filter((e) => {
    const t = e.type || e.event_type || "";
    return t === "vote_cast";
  });

  return (
    <div
      className="relative transition-all duration-300 border-l-[3px]"
      style={{
        borderBottomWidth: 1,
        borderBottomColor: "var(--cc-border)",
        borderLeftColor: color,
        backgroundColor: effectiveActive ? `${color}14` : "transparent",
        opacity: effectiveActive ? 1 : agentEvents.length > 0 ? 0.9 : 0.5,
        padding: "14px",
        minHeight: "130px",
      }}
    >
      {/* Agent header */}
      <div className="flex items-center gap-2.5 mb-2.5">
        <div
          className="relative w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-white shrink-0"
          style={{ backgroundColor: color }}
        >
          {initials}
          {effectiveActive && (
            <div
              className="absolute -inset-1 rounded-xl border-2 opacity-60"
              style={{
                borderColor: color,
                animation: "ring-pulse 2s infinite",
              }}
            />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-semibold" style={{ color }}>
            {displayName}
          </div>
          <div
            className={`text-[11px] ${effectiveActive ? "font-medium" : ""}`}
            style={{ color: effectiveActive ? "var(--cc-accent)" : "var(--cc-text-muted)" }}
          >
            {statusLabel}
          </div>
        </div>
      </div>

      {/* Last content */}
      {streamingText && (
        <div
          className="text-xs leading-relaxed overflow-hidden relative"
          style={{
            color: effectiveActive ? "var(--cc-text)" : "var(--cc-text-muted)",
            maxHeight: "60px",
          }}
        >
          {streamingText.slice(0, 200)}
          {effectiveActive && (
            <span
              className="inline-block w-0.5 h-3.5 align-middle ml-0.5"
              style={{
                backgroundColor: "var(--cc-accent)",
                animation: "blink 1s infinite",
              }}
            />
          )}
        </div>
      )}

      {/* Finding chips */}
      {agentFindings.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {criticalCount > 0 && (
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-[var(--cc-red-muted)] text-[var(--cc-red)]">
              CRITICAL{criticalCount > 1 ? ` ×${criticalCount}` : ""}
            </span>
          )}
          {highCount > 0 && (
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-[var(--cc-yellow-muted)] text-[var(--cc-yellow)]">
              HIGH{highCount > 1 ? ` ×${highCount}` : ""}
            </span>
          )}
          {medCount > 0 && (
            <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-[var(--cc-accent-muted)] text-[var(--cc-accent)]">
              MED{medCount > 1 ? ` ×${medCount}` : ""}
            </span>
          )}
        </div>
      )}

      {/* Mini vote badges */}
      {voteEvents.length > 0 && (
        <div className="flex gap-1 mt-2">
          {voteEvents.map((v, i) => {
            const vote = (v.structured as Record<string, unknown>)?.vote as string
              || (v.payload as Record<string, unknown>)?.vote as string
              || v.content?.includes("YES") ? "YES" : v.content?.includes("NO") ? "NO" : "?";
            const isYes = vote === "YES";
            return (
              <span
                key={v.id || v.event_id || `vote-${i}`}
                className={`px-2 py-0.5 rounded text-[10px] font-bold ${isYes ? "bg-[var(--cc-green-muted)] text-[var(--cc-green)]" : "bg-[var(--cc-red-muted)] text-[var(--cc-red)]"}`}
              >
                {isYes ? "YES" : "NO"}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
