// Enums
export type EventType =
  | "run_started"
  | "run_completed"
  | "run_failed"
  | "phase_started"
  | "phase_completed"
  | "agent_thinking"
  | "agent_response"
  | "finding_created"
  | "proposal_created"
  | "vote_cast"
  | "consensus_reached"
  | "human_review_requested"
  | "human_review_completed"
  | "cost_update"
  | "error";

export type Phase =
  | "ingestion"
  | "analysis"
  | "debate"
  | "synthesis"
  | "review"
  | "output";

export type Severity = "critical" | "high" | "medium" | "low" | "info";

export type ProposalStatus =
  | "pending"
  | "voting"
  | "accepted"
  | "rejected"
  | "amended";

export type VoteType = "approve" | "reject" | "abstain" | "amend";

// Interfaces
export interface AgentIdentity {
  id: string;
  name: string;
  role: string;
  color?: string;
}

export interface Finding {
  id: string;
  run_id: string;
  agent_id: string;
  phase: Phase;
  severity: Severity;
  title: string;
  description: string;
  file_path?: string;
  line_start?: number;
  line_end?: number;
  code_snippet?: string;
  recommendation?: string;
  tags: string[];
  created_at: string;
}

export interface Vote {
  id: string;
  proposal_id: string;
  agent_id: string;
  vote_type: VoteType;
  reasoning?: string;
  created_at: string;
}

export interface Proposal {
  id: string;
  run_id: string;
  agent_id: string;
  title: string;
  description: string;
  finding_ids: string[];
  status: ProposalStatus;
  votes: Vote[];
  created_at: string;
  updated_at: string;
}

export interface Event {
  id?: string;
  event_id?: string;
  run_id: string;
  type?: EventType;
  event_type?: string;
  phase?: Phase | string;
  agent?: string;
  agent_id?: string;
  content?: string;
  structured?: Record<string, unknown>;
  payload?: Record<string, unknown>;
  timestamp: string;
  sequence: number;
  round?: number | null;
  metadata?: {
    provider?: string;
    model?: string;
    input_tokens?: number;
    output_tokens?: number;
    cost_usd?: number;
    latency_ms?: number;
    cached?: boolean;
    fallback?: boolean;
  };
}

export interface CostReport {
  run_id: string;
  total_cost: number;
  total_tokens: number;
  prompt_tokens: number;
  completion_tokens: number;
  by_agent: Record<string, number>;
  by_phase: Record<string, number>;
  currency: string;
}

export interface RepoContext {
  url?: string;
  local_path?: string;
  branch?: string;
  commit_sha?: string;
  file_count?: number;
  language_breakdown?: Record<string, number>;
}

export interface RunSummary {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  phase?: Phase;
  repo: RepoContext;
  created_at: string;
  updated_at: string;
  completed_at?: string;
  finding_count: number;
  proposal_count: number;
  total_cost: number;
}

export interface RunDetail extends RunSummary {
  events: Event[];
  findings: Finding[];
  proposals: Proposal[];
  cost?: CostReport;
}

export interface ProviderConfig {
  name: string;
  model: string;
  api_key?: string;
  base_url?: string;
  max_tokens?: number;
  temperature?: number;
}

export interface AgentConfig {
  id: string;
  name: string;
  role: string;
  provider: string;
  model?: string;
  enabled: boolean;
  system_prompt?: string;
}

export interface AppConfig {
  providers: Record<string, ProviderConfig>;
  agents: AgentConfig[];
  topology: "round_robin" | "adversarial" | "panel" | "socratic";
  debate_rounds: number;
  hitl_enabled: boolean;
  budget_limit?: number;
  output_formats: string[];
  ingestion: {
    max_file_size: number;
    excluded_patterns: string[];
    chunk_size: number;
  };
}

export interface HealthStatus {
  status: "healthy" | "degraded" | "unhealthy";
  providers: Record<string, boolean>;
  agents: Record<string, boolean>;
  database: boolean;
  version: string;
}
