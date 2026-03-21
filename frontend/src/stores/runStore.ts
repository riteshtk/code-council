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

function parseEventPayload(
  state: Omit<RunState, "setRun" | "clearRun" | "addEvent" | "setWsState" | "connectWebSocket" | "disconnectWebSocket">,
  event: Event
): Partial<RunState> {
  const updates: Partial<RunState> = {};

  const eventType = event.type || event.event_type || "";
  const payload = event.payload || event.structured || {};

  switch (eventType) {
    case "phase_started":
    case "phase_completed":
      if (event.phase) updates.phase = event.phase as Phase;
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
      phase: run.phase || null,
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
