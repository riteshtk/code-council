"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Event } from "@/lib/types";
import { getAgentColor } from "@/lib/utils";
import { getAgent } from "@/lib/constants";

function getAgentDisplayName(agentId: string): string {
  const agent = getAgent(agentId);
  return agent ? agent.shortRole : agentId;
}

// Map event types to mockup badge styles
function getEventBadge(type: string): { label: string; bgColor: string; textColor: string } {
  switch (type) {
    case "finding_created":
    case "finding_emitted":
      return { label: "FINDING", bgColor: "var(--cc-red-muted)", textColor: "var(--cc-red)" };
    case "proposal_created":
      return { label: "PROPOSAL", bgColor: "var(--cc-accent-muted)", textColor: "var(--cc-accent)" };
    case "vote_cast":
      return { label: "VOTE", bgColor: "var(--cc-green-muted)", textColor: "var(--cc-green)" };
    case "agent_thinking":
      return { label: "THINKING", bgColor: "var(--cc-yellow-muted)", textColor: "var(--cc-yellow)" };
    case "agent_response":
      return { label: "RESPONSE", bgColor: "var(--cc-blue-muted)", textColor: "var(--cc-blue)" };
    case "phase_started":
    case "phase_completed":
      return { label: "PHASE", bgColor: "var(--cc-bg-hover)", textColor: "var(--cc-text-muted)" };
    case "consensus_reached":
      return { label: "CONSENSUS", bgColor: "var(--cc-green-muted)", textColor: "var(--cc-green)" };
    case "human_review_requested":
      return { label: "REVIEW", bgColor: "var(--cc-yellow-muted)", textColor: "var(--cc-yellow)" };
    case "error":
      return { label: "ERROR", bgColor: "var(--cc-red-muted)", textColor: "var(--cc-red)" };
    default:
      return { label: type.toUpperCase().replace(/_/g, " "), bgColor: "var(--cc-bg-hover)", textColor: "var(--cc-text-muted)" };
  }
}

// Get bubble style based on event type
function getBubbleStyle(type: string): { bg: string; border: string } {
  switch (type) {
    case "finding_created":
    case "finding_emitted":
      return { bg: "rgba(255,107,107,0.04)", border: "rgba(255,107,107,0.2)" };
    case "proposal_created":
      return { bg: "rgba(108,92,231,0.04)", border: "rgba(108,92,231,0.2)" };
    case "agent_response":
      if (type === "agent_response") return { bg: "transparent", border: "var(--cc-border)" };
      return { bg: "transparent", border: "var(--cc-border)" };
    default:
      return { bg: "transparent", border: "var(--cc-border)" };
  }
}

function getEventContent(event: Event): string {
  // Backend sends "content" (string) + "structured" (dict)
  // Frontend Event type supports both "payload" and "content"/"structured"
  const text = event.content || "";
  const p = event.payload || event.structured || {};
  const eventType = event.type || event.event_type || "";

  if (text) return text;

  if (eventType === "agent_thinking") return String(p?.text || p?.content || "Thinking...");
  if (eventType === "agent_response" || eventType === "agent_speaking") return String(p?.content || p?.text || "");
  if (eventType === "finding_created" || eventType === "finding_emitted")
    return `[${(p as Record<string, string>)?.severity?.toUpperCase?.() || "INFO"}] ${(p as Record<string, string>)?.title || (p as Record<string, string>)?.content || ""}`;
  if (eventType === "proposal_created") return String((p as Record<string, string>)?.title || "");
  if (eventType === "vote_cast")
    return `${(p as Record<string, string>)?.vote_type?.toUpperCase?.() || "VOTE"} on proposal`;
  if (eventType === "phase_started" || eventType === "phase_completed")
    return `Phase: ${event.phase || ""}`;

  try {
    const s = JSON.stringify(p);
    return s && s !== "{}" ? s.slice(0, 500) : eventType || "Event";
  } catch {
    return eventType || "Event";
  }
}

const FILTER_BUTTONS = [
  { key: "all", label: "All", types: [] as string[] },
  { key: "findings", label: "Findings", types: ["finding_created", "finding_emitted"] },
  { key: "proposals", label: "Proposals", types: ["proposal_created"] },
  { key: "challenges", label: "Challenges", types: ["agent_response", "agent_speaking"] },
  { key: "votes", label: "Votes", types: ["vote_cast"] },
];

function EventBubble({ event }: { event: Event }) {
  const agentKey = event.agent_id || event.agent || "";
  const eventType = event.type || event.event_type || "";
  const agentColor = agentKey && agentKey !== "system" ? getAgentColor(agentKey) : "var(--cc-text-muted)";
  const agentName = agentKey && agentKey !== "system" ? getAgentDisplayName(agentKey) : "System";
  const badge = getEventBadge(eventType);
  const bubbleStyle = getBubbleStyle(eventType);
  const content = getEventContent(event);

  const time = new Date(event.timestamp).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
  });

  return (
    <div
      className="flex gap-3 rounded-[10px] border transition-all duration-200 animate-fade-in"
      style={{
        backgroundColor: bubbleStyle.bg || "var(--cc-bg-card)",
        borderColor: bubbleStyle.border,
        padding: "12px 16px",
      }}
    >
      {/* Color bar */}
      <div
        className="w-[3px] rounded-sm shrink-0 self-stretch"
        style={{
          backgroundColor: agentKey && agentKey !== "system" ? agentColor : "var(--cc-text-muted)",
        }}
      />

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center gap-2 mb-1.5">
          <span
            className="text-xs font-semibold"
            style={{ color: agentKey && agentKey !== "system" ? agentColor : "var(--cc-text-muted)" }}
          >
            {agentName}
          </span>
          <span
            className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase"
            style={{
              backgroundColor: badge.bgColor,
              color: badge.textColor,
            }}
          >
            {badge.label}
          </span>
          <span
            className="text-[10px] font-mono ml-auto"
            style={{ color: "var(--cc-text-muted)" }}
          >
            {time}
          </span>
        </div>
        {/* Event text — rendered as markdown */}
        <div className="text-[13px] leading-relaxed prose-agent" style={{ color: "var(--cc-text)" }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
}

interface DebateFeedProps {
  events: Event[];
}

export function DebateFeed({ events }: DebateFeedProps) {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const [autoScroll, setAutoScroll] = useState(true);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [events, autoScroll]);

  const filtered = useMemo(() => {
    return events.filter((e) => {
      const eType = e.type || e.event_type || "";
      if (typeFilter !== "all") {
        const filterDef = FILTER_BUTTONS.find((b) => b.key === typeFilter);
        if (filterDef && filterDef.types.length > 0 && !filterDef.types.includes(eType)) return false;
      }
      if (search) {
        const s = search.toLowerCase();
        const contentStr = (e.content || JSON.stringify(e.payload || e.structured || "") || "").toLowerCase();
        return (
          eType.includes(s) ||
          (e.agent_id || e.agent || "").toLowerCase().includes(s) ||
          contentStr.includes(s)
        );
      }
      return true;
    });
  }, [events, search, typeFilter]);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Search + filter bar (sticky) */}
      <div
        className="flex items-center gap-3 p-2 rounded-lg mb-1 sticky top-0 z-10"
        style={{ backgroundColor: "var(--cc-bg-card)" }}
      >
        <input
          className="flex-1 px-3 py-1.5 text-xs rounded-md border outline-none transition-all duration-200"
          style={{
            backgroundColor: "var(--cc-bg)",
            borderColor: "var(--cc-border)",
            color: "var(--cc-text)",
          }}
          placeholder="Search debate events..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {FILTER_BUTTONS.map((btn) => (
          <button
            key={btn.key}
            aria-pressed={typeFilter === btn.key}
            onClick={() => setTypeFilter(btn.key)}
            className="px-2.5 py-1 text-[11px] rounded-md border cursor-pointer transition-all duration-200"
            style={{
              backgroundColor: "var(--cc-bg)",
              borderColor: typeFilter === btn.key ? "var(--cc-accent)" : "var(--cc-border)",
              color: typeFilter === btn.key ? "var(--cc-accent)" : "var(--cc-text-muted)",
            }}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* Events list */}
      <div aria-live="polite" aria-label="Debate events" className="flex-1 overflow-y-auto flex flex-col gap-3 pr-1">
        {filtered.length === 0 ? (
          <div
            className="py-8 text-center text-sm"
            style={{ color: "var(--cc-text-muted)" }}
          >
            No events yet...
          </div>
        ) : (
          filtered.map((event, idx) => (
            <EventBubble key={event.id || event.event_id || `event-${idx}`} event={event} />
          ))
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
