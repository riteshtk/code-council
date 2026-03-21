import { create } from "zustand";
import type { Event, Phase, Finding, Proposal, Vote, CostReport, RunSummary } from "@/lib/types";
import { WebSocketManager, WSState } from "./websocketManager";

interface RunState {
  runId: string | null;
  run: RunSummary | null;
  phase: Phase | null;
  events: Event[];
  findings: Finding[];
  proposals: Proposal[];
  votes: Vote[];
  cost: CostReport | null;
  wsState: WSState;
  wsManager: WebSocketManager | null;

  // Actions
  setRun: (run: RunSummary) => void;
  clearRun: () => void;
  addEvent: (event: Event) => void;
  setWsState: (state: WSState) => void;
  connectWebSocket: (runId: string) => void;
  disconnectWebSocket: () => void;
}

// Map backend phase names to frontend Phase type
function normalizePhase(phase: string | undefined): Phase | null {
  if (!phase) return null;
  const map: Record<string, Phase> = {
    ingesting: "ingestion", ingestion: "ingestion",
    analysing: "analysis", analysis: "analysis", analyzing: "analysis",
    opening: "debate", debating: "debate", debate: "debate",
    voting: "synthesis", synthesis: "synthesis",
    scribing: "review", review: "review",
    output: "output", done: "output", finalise: "output",
    init: "ingestion", error: "output",
  };
  return map[phase.toLowerCase()] || (phase as Phase);
}

function parseEventPayload(
  state: Omit<RunState, "setRun" | "clearRun" | "addEvent" | "setWsState" | "connectWebSocket" | "disconnectWebSocket">,
  event: Event
): Partial<RunState> {
  const updates: Partial<RunState> = {};

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const e = event as any;
  const eventType = e.type || e.event_type || "";
  const payload = e.payload || e.structured || {};

  switch (eventType) {
    case "phase_started":
    case "phase_completed": {
      const mapped = normalizePhase(e.phase);
      if (mapped) updates.phase = mapped;
      break;
    }
    case "run_completed":
      // Update run status so UI knows it's done
      if (state.run) {
        updates.run = { ...state.run, status: "completed" } as RunSummary;
      }
      break;
    case "run_failed":
      if (state.run) {
        updates.run = { ...state.run, status: "failed" } as RunSummary;
      }
      break;
    case "finding_created":
    case "finding_emitted": {
      const finding = payload as unknown as Finding;
      if (finding?.id) {
        const exists = state.findings.some((f) => f.id === finding.id);
        if (!exists) updates.findings = [...state.findings, finding];
      }
      break;
    }
    case "proposal_created": {
      const proposal = payload as unknown as Proposal;
      if (proposal?.id) {
        const exists = state.proposals.some((p) => p.id === proposal.id);
        if (!exists) updates.proposals = [...state.proposals, proposal];
      }
      break;
    }
    case "vote_cast": {
      const vote = payload as unknown as Vote;
      if (vote?.id) {
        const exists = state.votes.some((v) => v.id === vote.id);
        if (!exists) updates.votes = [...state.votes, vote];
        if (vote.proposal_id) {
          updates.proposals = state.proposals.map((p) =>
            p.id === vote.proposal_id
              ? { ...p, votes: [...(p.votes || []).filter(v2 => v2.id !== vote.id), vote] }
              : p
          );
        }
      }
      break;
    }
    case "cost_update":
    case "budget_warning": {
      const costData = payload as unknown as CostReport;
      if (costData) updates.cost = costData;
      break;
    }
  }

  return updates;
}

export const useRunStore = create<RunState>((set, get) => ({
  runId: null,
  run: null,
  phase: null,
  events: [],
  findings: [],
  proposals: [],
  votes: [],
  cost: null,
  wsState: "disconnected",
  wsManager: null,

  setRun: (run: RunSummary) =>
    set({
      run,
      runId: run.id,
      phase: (run.phase as Phase) || null,
    }),

  clearRun: () => {
    const { wsManager } = get();
    wsManager?.disconnect();
    set({
      runId: null,
      run: null,
      phase: null,
      events: [],
      findings: [],
      proposals: [],
      votes: [],
      cost: null,
      wsState: "disconnected",
      wsManager: null,
    });
  },

  addEvent: (event: Event) => {
    const state = get();
    // Deduplicate by id
    if (state.events.some((e) => e.id === event.id)) return;
    const eventUpdates = parseEventPayload(state, event);
    set({
      events: [...state.events, event].sort((a, b) => a.sequence - b.sequence),
      ...eventUpdates,
    });
  },

  setWsState: (wsState: WSState) => set({ wsState }),

  connectWebSocket: (runId: string) => {
    const { wsManager } = get();
    if (wsManager) wsManager.disconnect();

    const manager = new WebSocketManager(
      runId,
      (event) => get().addEvent(event),
      (state) => get().setWsState(state)
    );
    manager.connect();
    set({ wsManager: manager, runId });
  },

  disconnectWebSocket: () => {
    const { wsManager } = get();
    wsManager?.disconnect();
    set({ wsManager: null, wsState: "disconnected" });
  },
}));
