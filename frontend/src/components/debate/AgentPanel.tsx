"use client";

import { useMemo } from "react";
import { getAgentColor } from "@/lib/utils";
import type { Event, Finding } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Brain, MessageSquare, Search, PenTool, Loader2 } from "lucide-react";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "var(--cc-red)",
  high: "#ff9500",
  medium: "var(--cc-yellow)",
  low: "var(--cc-blue)",
  info: "var(--cc-text-muted)",
};

const AGENT_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  archaeologist: Search,
  skeptic: MessageSquare,
  visionary: Brain,
  scribe: PenTool,
};

function getAgentIcon(agentId: string) {
  const lower = agentId.toLowerCase();
  for (const [key, Icon] of Object.entries(AGENT_ICONS)) {
    if (lower.includes(key)) return Icon;
  }
  return Brain;
}

interface AgentPanelProps {
  agentId: string;
  agentName?: string;
  events: Event[];
  findings: Finding[];
  isActive?: boolean;
}

export function AgentPanel({
  agentId,
  agentName,
  events,
  findings,
  isActive = false,
}: AgentPanelProps) {
  const color = getAgentColor(agentId);
  const Icon = getAgentIcon(agentId);
  const name = agentName || agentId;

  const agentEvents = useMemo(
    () => events.filter((e) => e.agent_id === agentId),
    [events, agentId]
  );

  const agentFindings = useMemo(
    () => findings.filter((f) => f.agent_id === agentId),
    [findings, agentId]
  );

  const lastEvent = agentEvents[agentEvents.length - 1];
  const streamingText =
    lastEvent?.type === "agent_thinking"
      ? String(lastEvent.payload?.text || "")
      : lastEvent?.type === "agent_response"
      ? String(lastEvent.payload?.content || "")
      : null;

  const status = isActive
    ? "thinking"
    : agentEvents.length > 0
    ? "responded"
    : "waiting";

  return (
    <div
      className="rounded-lg border overflow-hidden"
      style={{
        backgroundColor: "var(--cc-bg-card)",
        borderColor: isActive ? color : "var(--cc-border)",
        boxShadow: isActive ? `0 0 12px ${color}33` : "none",
        transition: "all 0.3s ease",
      }}
    >
      {/* Header */}
      <div
        className="flex items-center gap-3 px-3 py-2 border-b"
        style={{
          borderColor: "var(--cc-border)",
          borderLeftWidth: 3,
          borderLeftColor: color,
          borderLeftStyle: "solid",
        }}
      >
        <div
          className="flex items-center justify-center w-8 h-8 rounded-full"
          style={{ backgroundColor: `${color}22` }}
        >
          <Icon className="w-4 h-4" style={{ color }} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm truncate" style={{ color: "var(--cc-text)" }}>
            {name}
          </div>
          <div className="text-xs flex items-center gap-1" style={{ color: "var(--cc-text-muted)" }}>
            {status === "thinking" && (
              <Loader2 className="w-3 h-3 animate-spin" style={{ color }} />
            )}
            <span style={{ color: status === "thinking" ? color : undefined }}>
              {status}
            </span>
          </div>
        </div>
        <div className="text-xs" style={{ color: "var(--cc-text-muted)" }}>
          {agentEvents.length} events
        </div>
      </div>

      {/* Streaming text */}
      {streamingText && (
        <div className="px-3 py-2 border-b" style={{ borderColor: "var(--cc-border)" }}>
          <ScrollArea className="h-20">
            <p
              className="text-xs leading-relaxed"
              style={{ color: "var(--cc-text-muted)", fontFamily: "var(--font-geist-mono)" }}
            >
              {streamingText}
              {status === "thinking" && (
                <span
                  className="inline-block w-1.5 h-3 ml-0.5 animate-pulse"
                  style={{ backgroundColor: color }}
                />
              )}
            </p>
          </ScrollArea>
        </div>
      )}

      {/* Findings */}
      {agentFindings.length > 0 && (
        <div className="px-3 py-2">
          <div
            className="text-xs font-medium mb-2"
            style={{ color: "var(--cc-text-muted)" }}
          >
            Findings ({agentFindings.length})
          </div>
          <div className="flex flex-wrap gap-1">
            {agentFindings.slice(0, 6).map((f) => (
              <Badge
                key={f.id}
                variant="outline"
                className="text-xs px-1.5 py-0.5"
                style={{
                  borderColor: `${SEVERITY_COLORS[f.severity] || "var(--cc-border)"}66`,
                  color: SEVERITY_COLORS[f.severity] || "var(--cc-text-muted)",
                  backgroundColor: `${SEVERITY_COLORS[f.severity] || "var(--cc-border)"}11`,
                }}
              >
                {f.severity[0].toUpperCase()} · {f.title.slice(0, 20)}
                {f.title.length > 20 ? "…" : ""}
              </Badge>
            ))}
            {agentFindings.length > 6 && (
              <Badge
                variant="outline"
                className="text-xs"
                style={{ color: "var(--cc-text-muted)" }}
              >
                +{agentFindings.length - 6}
              </Badge>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
