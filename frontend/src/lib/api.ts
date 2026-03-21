import type {
  RunSummary,
  RunDetail,
  AppConfig,
  HealthStatus,
  CostReport,
  Event,
  AgentIdentity,
} from "./types";

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const API_BASE = BASE_URL;

async function apiFetch<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API ${path} failed (${res.status}): ${text}`);
  }
  return res.json() as Promise<T>;
}

// Run endpoints
export async function createRun(params: {
  repo_url?: string;
  local_path?: string;
  provider?: string;
  topology?: string;
  rounds?: number;
  hitl?: boolean;
  budget?: number;
}): Promise<RunSummary> {
  const { repo_url = "", local_path, provider, topology, rounds, hitl, budget } = params;
  const config_overrides: Record<string, unknown> = {};
  if (local_path !== undefined) config_overrides.local_path = local_path;
  if (provider !== undefined) config_overrides.provider = provider;
  if (topology !== undefined) config_overrides.topology = topology;
  if (rounds !== undefined) config_overrides.rounds = rounds;
  if (hitl !== undefined) config_overrides.hitl = hitl;
  if (budget !== undefined) config_overrides.budget = budget;
  return apiFetch<RunSummary>("/api/runs", {
    method: "POST",
    body: JSON.stringify({ repo_url, config_overrides }),
  });
}

export async function getRun(runId: string): Promise<RunDetail> {
  return apiFetch<RunDetail>(`/api/runs/${runId}`);
}

export async function listRuns(params?: {
  limit?: number;
  offset?: number;
  status?: string;
}): Promise<RunSummary[]> {
  const qs = new URLSearchParams(
    Object.entries(params || {})
      .filter(([, v]) => v !== undefined)
      .map(([k, v]) => [k, String(v)])
  ).toString();
  const data = await apiFetch<{ runs: RunSummary[] } | RunSummary[]>(`/api/runs${qs ? "?" + qs : ""}`);
  return Array.isArray(data) ? data : (data.runs || []);
}

export async function deleteRun(runId: string): Promise<void> {
  return apiFetch<void>(`/api/runs/${runId}`, { method: "DELETE" });
}

// RFC
export async function getRFC(
  runId: string,
  format: "json" | "markdown" | "html" = "json"
): Promise<unknown> {
  const url = `${API_BASE}/api/runs/${runId}/rfc?format=${format}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`getRFC failed: ${res.status}`);
  if (format === "json") return res.json();
  return res.text();
}

// Events
export async function getEvents(
  runId: string,
  params?: { offset?: number; limit?: number; agent?: string; event_type?: string }
): Promise<Event[]> {
  const qs = new URLSearchParams(
    Object.entries(params || {})
      .filter(([, v]) => v !== undefined)
      .map(([k, v]) => [k, String(v)])
  ).toString();
  const data = await apiFetch<{ events: Event[] } | Event[]>(
    `/api/runs/${runId}/events${qs ? "?" + qs : ""}`
  );
  return Array.isArray(data) ? data : (data.events || []);
}

// Cost
export async function getCost(runId: string): Promise<CostReport> {
  return apiFetch<CostReport>(`/api/runs/${runId}/cost`);
}

// Config
export async function getConfig(): Promise<AppConfig> {
  return apiFetch<AppConfig>("/api/config");
}

export async function updateConfig(
  config: Partial<AppConfig>
): Promise<AppConfig> {
  return apiFetch<AppConfig>("/api/config", {
    method: "PATCH",
    body: JSON.stringify({ overrides: config }),
  });
}

// Agents
export async function listAgents(): Promise<AgentIdentity[]> {
  const data = await apiFetch<{ agents: AgentIdentity[] } | AgentIdentity[]>("/api/agents");
  return Array.isArray(data) ? data : (data.agents || []);
}

// Providers
export async function listProviders(): Promise<string[]> {
  const data = await apiFetch<{ providers: unknown[] } | unknown[]>("/api/providers");
  const arr = Array.isArray(data) ? data : ((data as { providers?: unknown[] }).providers || []);
  return arr.map((p: unknown) => typeof p === 'string' ? p : (p as Record<string, string>).name || String(p));
}

// Health
export async function health(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>("/api/health");
}

// Review / Rerun
export async function submitReview(runId: string, review: Record<string, unknown>): Promise<unknown> {
  return apiFetch(`/api/runs/${runId}/review`, { method: "POST", body: JSON.stringify(review) });
}

export async function rerunAnalysis(runId: string): Promise<unknown> {
  return apiFetch(`/api/runs/${runId}/rerun`, { method: "POST" });
}

// Config validation
export async function validateConfig(yaml: string): Promise<unknown> {
  return apiFetch("/api/config/validate", { method: "POST", body: JSON.stringify({ yaml }) });
}

// Agent memory
export async function getAgentMemory(handle: string): Promise<unknown> {
  return apiFetch(`/api/agents/${handle}/memory`);
}

export async function clearAgentMemory(handle: string): Promise<void> {
  return apiFetch(`/api/agents/${handle}/memory`, { method: "DELETE" });
}

// Provider test
export async function testProvider(name: string): Promise<unknown> {
  return apiFetch("/api/providers/test", { method: "POST", body: JSON.stringify({ provider: name }) });
}

// Sessions
export async function listSessions(): Promise<unknown[]> {
  const data = await apiFetch<{ sessions: unknown[] } | unknown[]>("/api/sessions");
  return Array.isArray(data) ? data : ((data as Record<string, unknown>).sessions as unknown[] || []);
}

export async function getSession(id: string): Promise<unknown> {
  return apiFetch(`/api/sessions/${id}`);
}

export async function compareSessions(id1: string, id2: string): Promise<unknown> {
  return apiFetch(`/api/sessions/compare?id1=${id1}&id2=${id2}`);
}
