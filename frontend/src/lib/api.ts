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
  return apiFetch<RunSummary>("/api/runs", {
    method: "POST",
    body: JSON.stringify(params),
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
  return apiFetch<unknown>(`/api/runs/${runId}/rfc?format=${format}`);
}

// Events
export async function getEvents(
  runId: string,
  params?: { after?: number; limit?: number }
): Promise<Event[]> {
  const qs = new URLSearchParams(
    Object.entries(params || {})
      .filter(([, v]) => v !== undefined)
      .map(([k, v]) => [k, String(v)])
  ).toString();
  return apiFetch<Event[]>(
    `/api/runs/${runId}/events${qs ? "?" + qs : ""}`
  );
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
  const data = await apiFetch<{ providers: string[] } | string[]>("/api/providers");
  return Array.isArray(data) ? data : (data.providers || []);
}

// Health
export async function health(): Promise<HealthStatus> {
  return apiFetch<HealthStatus>("/api/health");
}
