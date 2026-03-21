import { Eye, Shield, Brain, PenTool } from "lucide-react";

export const AGENT_HANDLES = ["archaeologist", "skeptic", "visionary", "scribe"] as const;
export type AgentHandle = typeof AGENT_HANDLES[number];

export const AGENTS = {
  archaeologist: {
    handle: "archaeologist",
    name: "The Archaeologist",
    abbr: "AR",
    role: "Historian \u00b7 Evidence Collector",
    shortRole: "Historian",
    color: "#d4a574",
    icon: Eye,
  },
  skeptic: {
    handle: "skeptic",
    name: "The Skeptic",
    abbr: "SK",
    role: "Risk Analyst \u00b7 Challenger",
    shortRole: "Challenger",
    color: "#ff6b6b",
    icon: Shield,
  },
  visionary: {
    handle: "visionary",
    name: "The Visionary",
    abbr: "VI",
    role: "Proposer \u00b7 Domain Reader",
    shortRole: "Proposer",
    color: "#6c5ce7",
    icon: Brain,
  },
  scribe: {
    handle: "scribe",
    name: "The Scribe",
    abbr: "SC",
    role: "Secretary \u00b7 RFC Author",
    shortRole: "Secretary",
    color: "#4ecdc4",
    icon: PenTool,
  },
} as const;

export function getAgent(handle: string) {
  const lower = handle.toLowerCase();
  for (const [key, val] of Object.entries(AGENTS)) {
    if (lower.includes(key)) return val;
  }
  return null;
}

export function getAgentName(handle: string): string {
  return getAgent(handle)?.name || handle;
}

export function getAgentAbbr(handle: string): string {
  return getAgent(handle)?.abbr || handle.slice(0, 2).toUpperCase();
}

export function getAgentColorByHandle(handle: string): string {
  return getAgent(handle)?.color || "#6c5ce7";
}
