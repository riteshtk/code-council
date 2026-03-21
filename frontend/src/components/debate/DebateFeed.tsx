"use client";

import { useState, useRef, useEffect, useMemo } from "react";
import type { Event } from "@/lib/types";
import { getAgentColor } from "@/lib/utils";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Search, Filter } from "lucide-react";

const EVENT_TYPE_LABELS: Record<string, string> = {
  run_started: "START",
  run_completed: "DONE",
  run_failed: "FAIL",
  phase_started: "PHASE",
  phase_completed: "PHASE",
  agent_thinking: "THINK",
  agent_response: "RESP",
  finding_created: "FIND",
  proposal_created: "PROP",
  vote_cast: "VOTE",
  consensus_reached: "CONS",
  human_review_requested: "HITL",
  human_review_completed: "HITL",
  cost_update: "COST",
  error: "ERR",
};

const EVENT_TYPE_COLORS: Record<string, string> = {
  run_started: "var(--cc-green)",
  run_completed: "var(--cc-green)",
  run_failed: "var(--cc-red)",
  phase_started: "var(--cc-accent)",
  phase_completed: "var(--cc-accent)",
  agent_thinking: "var(--cc-yellow)",
  agent_response: "var(--cc-blue)",
  finding_created: "var(--cc-red)",
  proposal_created: "var(--cc-accent)",
  vote_cast: "var(--cc-yellow)",
  consensus_reached: "var(--cc-green)",
  human_review_requested: "#ff9500",
  human_review_completed: "var(--cc-green)",
  cost_update: "var(--cc-text-muted)",
  error: "var(--cc-red)",
};

function EventItem({ event }: { event: Event }) {
  const agentColor = event.agent_id ? getAgentColor(event.agent_id) : "var(--cc-text-muted)";
  const typeColor = EVENT_TYPE_COLORS[event.type] || "var(--cc-text-muted)";
  const label = EVENT_TYPE_LABELS[event.type] || event.type.toUpperCase();

  const content = useMemo(() => {
    const p = event.payload;
    if (event.type === "agent_thinking") return String(p?.text || p?.content || "");
    if (event.type === "agent_response") return String(p?.content || p?.text || "");
    if (event.type === "finding_created")
      return `[${(p as { severity?: string })?.severity?.toUpperCase()}] ${(p as { title?: string })?.title || ""}`;
    if (event.type === "proposal_created") return String((p as { title?: string })?.title || "");
    if (event.type === "vote_cast")
      return `${(p as { vote_type?: string })?.vote_type?.toUpperCase()} on proposal`;
    if (event.type === "phase_started" || event.type === "phase_completed")
      return `${event.phase || ""}`;
    return JSON.stringify(p).slice(0, 120);
  }, [event]);

  const time = new Date(event.timestamp).toLocaleTimeString("en-US", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });

  return (
    <div
      className="flex gap-2 px-3 py-2 hover:bg-white/5 transition-colors border-l-2 group"
      style={{ borderLeftColor: event.agent_id ? agentColor : "transparent" }}
    >
      {/* Time */}
      <span
        className="text-xs shrink-0 mt-0.5 w-16"
        style={{ color: "var(--cc-text-muted)", fontFamily: "var(--font-geist-mono)" }}
      >
        {time}
      </span>

      {/* Type badge */}
      <span
        className="text-xs font-bold shrink-0 mt-0.5 w-12"
        style={{ color: typeColor, fontFamily: "var(--font-geist-mono)" }}
      >
        {label}
      </span>

      {/* Agent */}
      {event.agent_id && (
        <span
          className="text-xs shrink-0 mt-0.5 w-20 truncate"
          style={{ color: agentColor }}
        >
          {event.agent_id}
        </span>
      )}

      {/* Content */}
      <span
        className="text-xs flex-1 leading-relaxed"
        style={{ color: "var(--cc-text)" }}
      >
        {content}
      </span>
    </div>
  );
}

interface DebateFeedProps {
  events: Event[];
}

const EVENT_TYPES = [
  "all",
  "agent_thinking",
  "agent_response",
  "finding_created",
  "proposal_created",
  "vote_cast",
  "phase_started",
  "error",
];

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
      if (typeFilter !== "all" && e.type !== typeFilter) return false;
      if (search) {
        const s = search.toLowerCase();
        const p = JSON.stringify(e.payload).toLowerCase();
        return (
          e.type.includes(s) ||
          (e.agent_id || "").toLowerCase().includes(s) ||
          p.includes(s)
        );
      }
      return true;
    });
  }, [events, search, typeFilter]);

  return (
    <div
      className="flex flex-col h-full rounded-lg border overflow-hidden"
      style={{
        backgroundColor: "var(--cc-bg-card)",
        borderColor: "var(--cc-border)",
      }}
    >
      {/* Toolbar */}
      <div
        className="flex items-center gap-2 px-3 py-2 border-b"
        style={{ borderColor: "var(--cc-border)" }}
      >
        <div className="relative flex-1">
          <Search
            className="absolute left-2 top-1/2 -translate-y-1/2 w-3 h-3"
            style={{ color: "var(--cc-text-muted)" }}
          />
          <Input
            placeholder="Filter events…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="h-7 pl-7 text-xs"
            style={{
              backgroundColor: "var(--cc-bg)",
              borderColor: "var(--cc-border)",
              color: "var(--cc-text)",
            }}
          />
        </div>
        <div className="flex items-center gap-1">
          <Filter className="w-3 h-3" style={{ color: "var(--cc-text-muted)" }} />
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            className="text-xs h-7 px-2 rounded border outline-none"
            style={{
              backgroundColor: "var(--cc-bg)",
              borderColor: "var(--cc-border)",
              color: "var(--cc-text)",
            }}
          >
            {EVENT_TYPES.map((t) => (
              <option key={t} value={t}>
                {t === "all" ? "All" : EVENT_TYPE_LABELS[t] || t}
              </option>
            ))}
          </select>
        </div>
        <button
          onClick={() => setAutoScroll(!autoScroll)}
          className="text-xs px-2 py-1 rounded transition-colors"
          style={{
            backgroundColor: autoScroll ? "var(--cc-accent)" : "var(--cc-border)",
            color: autoScroll ? "white" : "var(--cc-text-muted)",
          }}
        >
          Auto
        </button>
        <Badge
          variant="outline"
          className="text-xs"
          style={{ color: "var(--cc-text-muted)", borderColor: "var(--cc-border)" }}
        >
          {filtered.length}
        </Badge>
      </div>

      {/* Event list */}
      <ScrollArea className="flex-1">
        {filtered.length === 0 ? (
          <div
            className="py-8 text-center text-sm"
            style={{ color: "var(--cc-text-muted)" }}
          >
            No events yet…
          </div>
        ) : (
          <div className="divide-y" style={{ borderColor: "var(--cc-border)" }}>
            {filtered.map((event) => (
              <EventItem key={event.id} event={event} />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
