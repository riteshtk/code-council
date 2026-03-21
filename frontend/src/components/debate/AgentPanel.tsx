"use client";

import { useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getAgentColor } from "@/lib/utils";
import type { Event, Finding } from "@/lib/types";

const AGENT_INITIALS: Record<string, string> = {
  archaeologist: "AR", skeptic: "SK", visionary: "VI", scribe: "SC",
};
const AGENT_DISPLAY_NAMES: Record<string, string> = {
  archaeologist: "The Archaeologist", skeptic: "The Skeptic",
  visionary: "The Visionary", scribe: "The Scribe",
};

function matchAgent(agentId: string, eventAgent: string | undefined): boolean {
  if (!eventAgent) return false;
  return agentId.toLowerCase() === eventAgent.toLowerCase()
    || eventAgent.toLowerCase().includes(agentId.toLowerCase());
}

function getInitials(agentId: string): string {
  for (const [key, val] of Object.entries(AGENT_INITIALS))
    if (agentId.toLowerCase().includes(key)) return val;
  return agentId.slice(0, 2).toUpperCase();
}

function getDisplayName(agentId: string): string {
  for (const [key, val] of Object.entries(AGENT_DISPLAY_NAMES))
    if (agentId.toLowerCase().includes(key)) return val;
  return agentId;
}

interface AgentPanelProps {
  agentId: string;
  events: Event[];
  findings: Finding[];
  isActive?: boolean;
  runCompleted?: boolean;
}

export function AgentPanel({ agentId, events, findings, isActive = false, runCompleted = false }: AgentPanelProps) {
  const color = getAgentColor(agentId);
  const initials = getInitials(agentId);
  const displayName = getDisplayName(agentId);
  const [expanded, setExpanded] = useState(false);

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const eAny = (e: any) => ({ type: e.type || e.event_type || "", agent: e.agent_id || e.agent || "" });

  const agentEvents = useMemo(
    () => events.filter((e) => matchAgent(agentId, eAny(e).agent)),
    [events, agentId]
  );

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const agentFindings = useMemo(() => findings.filter((f: any) => matchAgent(agentId, f.agent_id || f.agent || "")), [findings, agentId]);

  // Get the LATEST speaking content for this agent
  const lastContent = useMemo(() => {
    const speaking = agentEvents.filter((e) => {
      const t = eAny(e).type;
      return ["agent_speaking", "agent_response", "agent_thinking"].includes(t);
    });
    if (speaking.length === 0) return "";
    const last = speaking[speaking.length - 1];
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const la = last as any;
    return la.content || la.payload?.content || la.payload?.text || "";
  }, [agentEvents]);

  // Summarize content: first 2 lines as preview
  const contentPreview = useMemo(() => {
    if (!lastContent) return "";
    const lines = lastContent.split("\n").filter((l: string) => l.trim());
    return lines.slice(0, 2).join(" ").slice(0, 200);
  }, [lastContent]);

  const effectiveActive = isActive && !runCompleted;

  const statusLabel = effectiveActive
    ? "Speaking..."
    : agentEvents.length > 0
    ? `Done · ${agentFindings.length} findings`
    : "Waiting";

  // Severity counts
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const sevCount = (sev: string) => agentFindings.filter((f: any) => ((f.severity || "") as string).toLowerCase() === sev).length;
  const criticalCount = sevCount("critical");
  const highCount = sevCount("high");
  const medCount = sevCount("medium");

  // Vote events
  const voteEvents = agentEvents.filter((e) => eAny(e).type === "vote_cast");

  return (
    <div
      className="border-l-[3px] transition-all duration-300 shrink-0"
      style={{
        borderBottomWidth: 1,
        borderBottomColor: "var(--cc-border)",
        borderLeftColor: color,
        backgroundColor: effectiveActive ? `${color}14` : "transparent",
        opacity: effectiveActive ? 1 : agentEvents.length > 0 ? 1 : 0.5,
        padding: "12px 14px",
      }}
    >
      {/* Header row */}
      <div className="flex items-center gap-2.5 mb-2">
        <div
          className="relative w-8 h-8 rounded-lg flex items-center justify-center text-[11px] font-bold text-white shrink-0"
          style={{ backgroundColor: color }}
        >
          {initials}
          {effectiveActive && (
            <div
              className="absolute -inset-1 rounded-xl border-2 opacity-60"
              style={{ borderColor: color, animation: "ring-pulse 2s infinite" }}
            />
          )}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-semibold leading-tight" style={{ color }}>{displayName}</div>
          <div className={`text-[11px] leading-tight ${effectiveActive ? "font-medium" : ""}`}
            style={{ color: effectiveActive ? "var(--cc-accent)" : "var(--cc-text-muted)" }}>
            {statusLabel}
          </div>
        </div>
      </div>

      {/* Content preview — compact summary, click to expand with full markdown */}
      {contentPreview && (
        <div
          className="text-[11px] leading-[1.5] cursor-pointer rounded px-1.5 py-1 -mx-1.5 hover:bg-white/5 transition-colors"
          style={{ color: effectiveActive ? "var(--cc-text)" : "var(--cc-text-muted)" }}
          onClick={() => setExpanded(!expanded)}
        >
          {expanded ? (
            <div className="max-h-[250px] overflow-y-auto prose-agent-sm">
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {lastContent}
              </ReactMarkdown>
            </div>
          ) : (
            <>
              {contentPreview}
              {lastContent.length > 150 && "..."}
              {effectiveActive && (
                <span className="inline-block w-0.5 h-3 align-middle ml-0.5 bg-[var(--cc-accent)]"
                  style={{ animation: "blink 1s infinite" }} />
              )}
            </>
          )}
        </div>
      )}

      {/* Finding chips */}
      {agentFindings.length > 0 && (
        <div className="flex flex-wrap gap-1 mt-1.5">
          {criticalCount > 0 && (
            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-[var(--cc-red-muted)] text-[var(--cc-red)]">
              CRIT{criticalCount > 1 ? ` ×${criticalCount}` : ""}
            </span>
          )}
          {highCount > 0 && (
            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-[var(--cc-yellow-muted)] text-[var(--cc-yellow)]">
              HIGH{highCount > 1 ? ` ×${highCount}` : ""}
            </span>
          )}
          {medCount > 0 && (
            <span className="px-1.5 py-0.5 rounded text-[9px] font-bold uppercase bg-[var(--cc-accent-muted)] text-[var(--cc-accent)]">
              MED{medCount > 1 ? ` ×${medCount}` : ""}
            </span>
          )}
        </div>
      )}

      {/* Vote badges */}
      {voteEvents.length > 0 && (
        <div className="flex gap-1 mt-1.5">
          {voteEvents.map((v, i) => {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const va = v as any;
            const vote = va.structured?.vote || va.payload?.vote || (va.content?.includes("YES") ? "YES" : "NO");
            const isYes = vote === "YES";
            return (
              <span key={va.id || va.event_id || `vote-${i}`}
                className={`px-1.5 py-0.5 rounded text-[9px] font-bold ${isYes ? "bg-[var(--cc-green-muted)] text-[var(--cc-green)]" : "bg-[var(--cc-red-muted)] text-[var(--cc-red)]"}`}>
                {isYes ? "YES" : "NO"}
              </span>
            );
          })}
        </div>
      )}
    </div>
  );
}
