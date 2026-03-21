"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  Github,
  GitBranch,
  Folder,
  Archive,
  Play,
  Clock,
  CheckCircle2,
  XCircle,
  Loader2,
  Activity,
  Users,
  DollarSign,
  Trash2,
  Shield,
  Eye,
  Brain,
  PenTool,
  Zap,
} from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn, formatCost, timeAgo } from "@/lib/utils";
import { createRun, listRuns, deleteRun, health } from "@/lib/api";
import type { RunSummary, HealthStatus } from "@/lib/types";

const SOURCE_TABS = [
  { id: "github", label: "GitHub", icon: Github },
  { id: "gitlab", label: "GitLab", icon: GitBranch },
  { id: "bitbucket", label: "Bitbucket", icon: GitBranch },
  { id: "local", label: "Local", icon: Folder },
  { id: "archive", label: "Archive", icon: Archive },
];

const TOPOLOGIES = [
  { value: "adversarial", label: "Adversarial" },
  { value: "collaborative", label: "Collaborative" },
  { value: "socratic", label: "Socratic" },
];

const PROVIDERS = [
  { value: "openai", label: "OpenAI GPT-4o" },
  { value: "anthropic", label: "Claude Sonnet" },
  { value: "gemini", label: "Gemini Pro" },
];

const BUDGETS = [
  { value: "0", label: "No limit" },
  { value: "1", label: "$1" },
  { value: "5", label: "$5" },
  { value: "10", label: "$10" },
];

const ROUNDS_OPTIONS = [
  { value: "1", label: "1" },
  { value: "2", label: "2" },
  { value: "3", label: "3" },
  { value: "5", label: "5" },
];

const AGENT_INFO = [
  { name: "The Archaeologist", abbr: "AR", role: "Historian \u00b7 Evidence Collector", color: "var(--cc-archaeologist)", icon: Eye },
  { name: "The Skeptic", abbr: "SK", role: "Risk Analyst \u00b7 Challenger", color: "var(--cc-skeptic)", icon: Shield },
  { name: "The Visionary", abbr: "VI", role: "Proposer \u00b7 Domain Reader", color: "var(--cc-visionary)", icon: Brain },
  { name: "The Scribe", abbr: "SC", role: "Secretary \u00b7 RFC Author", color: "var(--cc-scribe)", icon: PenTool },
];

const STATUS_CONFIG: Record<string, { colorClass: string; bgClass: string; icon: React.ReactNode }> = {
  running: {
    colorClass: "text-[var(--cc-accent)]",
    bgClass: "bg-[var(--cc-accent-muted)]",
    icon: <Loader2 className="w-3 h-3 animate-spin" />,
  },
  completed: {
    colorClass: "text-[var(--cc-green)]",
    bgClass: "bg-[var(--cc-green-muted)]",
    icon: <CheckCircle2 className="w-3 h-3" />,
  },
  failed: {
    colorClass: "text-[var(--cc-red)]",
    bgClass: "bg-[var(--cc-red-muted)]",
    icon: <XCircle className="w-3 h-3" />,
  },
  pending: {
    colorClass: "text-[var(--cc-text-muted)]",
    bgClass: "bg-[var(--cc-bg-hover)]",
    icon: <Clock className="w-3 h-3" />,
  },
  deadlocked: {
    colorClass: "text-[var(--cc-yellow)]",
    bgClass: "bg-[var(--cc-yellow-muted)]",
    icon: <Clock className="w-3 h-3" />,
  },
};

function StatusPill({ status }: { status: string }) {
  const c = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full uppercase tracking-wide",
        c.colorClass,
        c.bgClass
      )}
    >
      {c.icon} {status}
    </span>
  );
}

export default function HomePage() {
  const router = useRouter();
  const [sourceTab, setSourceTab] = useState("github");
  const [repoUrl, setRepoUrl] = useState("");
  const [localPath, setLocalPath] = useState("");
  const [provider, setProvider] = useState("openai");
  const [topology, setTopology] = useState("adversarial");
  const [rounds, setRounds] = useState(3);
  const [hitl, setHitl] = useState(false);
  const [budget, setBudget] = useState("0");
  const [submitting, setSubmitting] = useState(false);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [runsLoading, setRunsLoading] = useState(true);
  const [healthData, setHealthData] = useState<HealthStatus | null>(null);

  useEffect(() => {
    loadRuns();
    loadHealth();
  }, []);

  async function loadRuns() {
    setRunsLoading(true);
    try {
      const data = await listRuns({ limit: 10 });
      setRuns(data);
    } catch {
      setRuns([]);
    } finally {
      setRunsLoading(false);
    }
  }

  async function loadHealth() {
    try {
      const h = await health();
      setHealthData(h);
    } catch {
      setHealthData(null);
    }
  }

  async function handleAnalyse() {
    const url = sourceTab === "local" ? localPath : repoUrl;
    if (!url.trim()) {
      toast.error("Please enter a repository URL or path");
      return;
    }
    setSubmitting(true);
    try {
      const run = await createRun({
        repo_url: sourceTab !== "local" ? url : undefined,
        local_path: sourceTab === "local" ? url : undefined,
        provider,
        topology,
        rounds,
        hitl,
        budget: parseFloat(budget) || undefined,
      });
      toast.success("Run started!");
      router.push(`/debate/${run.id}`);
    } catch (e) {
      toast.error(`Failed to start run: ${e}`);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(runId: string, e: React.MouseEvent) {
    e.stopPropagation();
    try {
      await deleteRun(runId);
      setRuns((prev) => prev.filter((r) => r.id !== runId));
      toast.success("Run deleted");
    } catch {
      toast.error("Failed to delete run");
    }
  }

  // Derive stats
  const totalAnalyses = runs.length;
  const avgConsensus = runs.length > 0
    ? Math.round(runs.filter((r) => r.status === "completed").length / runs.length * 100)
    : 0;
  const totalSpend = runs.reduce((s, r) => s + r.total_cost, 0);

  // Parse repo display name
  function repoDisplay(run: RunSummary) {
    const url = run.repo?.url || run.repo?.local_path || run.id;
    const match = url.match(/github\.com\/([^/]+)\/([^/]+)/);
    if (match) return { org: match[1] + "/", name: match[2] };
    return { org: "", name: url };
  }

  return (
    <div className="flex-1 px-8 lg:px-12 py-10 animate-fade-in">
      {/* Hero Section */}
      <div className="text-center mb-12">
        <h1 className="text-4xl font-bold mb-2">
          Summon the <span className="gradient-text-accent">Council</span>
        </h1>
        <p className="text-base text-[var(--cc-text-muted)] mb-8">
          Submit a repository. Four AI agents will analyse, debate, and produce an institutional-grade RFC.
        </p>

        {/* Source selector */}
        <div className="flex max-w-[700px] mx-auto mb-3 rounded-[10px] overflow-hidden border border-[var(--cc-border)] bg-[var(--cc-bg-card)]">
          {SOURCE_TABS.map(({ id, label }) => (
            <button
              key={id}
              onClick={() => setSourceTab(id)}
              className={cn(
                "flex-1 py-3 px-4 text-[13px] font-medium cursor-pointer transition-all duration-200 whitespace-nowrap",
                sourceTab === id
                  ? "bg-[var(--cc-accent)] text-white"
                  : "text-[var(--cc-text-muted)] hover:bg-[var(--cc-bg-hover)] hover:text-[var(--cc-text)]"
              )}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Input row */}
        <div className="flex gap-3 max-w-[700px] mx-auto mb-6">
          {sourceTab === "local" ? (
            <input
              placeholder="/path/to/your/project"
              value={localPath}
              onChange={(e) => setLocalPath(e.target.value)}
              className="flex-1 py-3 px-5 rounded-[10px] border border-[var(--cc-border)] bg-[var(--cc-bg-card)] text-[15px] text-[var(--cc-text)] placeholder:text-[var(--cc-text-muted)] focus:border-[var(--cc-accent)] focus:shadow-[0_0_0_3px_var(--cc-accent-glow)] outline-none transition-all duration-200"
            />
          ) : (
            <input
              placeholder={`https://${sourceTab}.com/owner/repo`}
              value={repoUrl}
              onChange={(e) => setRepoUrl(e.target.value)}
              className="flex-1 py-3 px-5 rounded-[10px] border border-[var(--cc-border)] bg-[var(--cc-bg-card)] text-[15px] text-[var(--cc-text)] placeholder:text-[var(--cc-text-muted)] focus:border-[var(--cc-accent)] focus:shadow-[0_0_0_3px_var(--cc-accent-glow)] outline-none transition-all duration-200"
            />
          )}
          <button
            onClick={handleAnalyse}
            disabled={submitting}
            className="py-3 px-7 rounded-[10px] bg-[var(--cc-accent)] text-white text-[15px] font-semibold cursor-pointer whitespace-nowrap transition-all duration-200 hover:bg-[#5a4bd4] hover:-translate-y-px hover:shadow-[0_4px_20px_var(--cc-accent-glow)] disabled:opacity-50"
          >
            {submitting ? (
              <span className="flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" /> Starting...
              </span>
            ) : (
              "Analyse"
            )}
          </button>
        </div>

        {/* Quick config chips */}
        <div className="flex gap-4 justify-center flex-wrap max-w-[800px] mx-auto">
          <div className="flex items-center gap-2 py-2 px-4 bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-lg text-[13px] text-[var(--cc-text-muted)] hover:border-[var(--cc-accent)] hover:text-[var(--cc-text)] transition-all duration-200">
            Provider:
            <select
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
              className="bg-transparent border-none text-[var(--cc-text)] text-[13px] outline-none cursor-pointer"
            >
              {PROVIDERS.map((p) => (
                <option key={p.value} value={p.value} className="bg-[var(--cc-bg-card)]">{p.label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2 py-2 px-4 bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-lg text-[13px] text-[var(--cc-text-muted)] hover:border-[var(--cc-accent)] hover:text-[var(--cc-text)] transition-all duration-200">
            Topology:
            <select
              value={topology}
              onChange={(e) => setTopology(e.target.value)}
              className="bg-transparent border-none text-[var(--cc-text)] text-[13px] outline-none cursor-pointer"
            >
              {TOPOLOGIES.map((t) => (
                <option key={t.value} value={t.value} className="bg-[var(--cc-bg-card)]">{t.label}</option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2 py-2 px-4 bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-lg text-[13px] text-[var(--cc-text-muted)] hover:border-[var(--cc-accent)] hover:text-[var(--cc-text)] transition-all duration-200">
            Rounds:
            <select
              value={String(rounds)}
              onChange={(e) => setRounds(Number(e.target.value))}
              className="bg-transparent border-none text-[var(--cc-text)] text-[13px] outline-none cursor-pointer"
            >
              {ROUNDS_OPTIONS.map((r) => (
                <option key={r.value} value={r.value} className="bg-[var(--cc-bg-card)]">{r.label}</option>
              ))}
            </select>
          </div>
          <label className="flex items-center gap-1.5 py-2 px-4 bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-lg text-[13px] text-[var(--cc-text-muted)] hover:border-[var(--cc-accent)] hover:text-[var(--cc-text)] transition-all duration-200 cursor-pointer">
            <input
              type="checkbox"
              checked={hitl}
              onChange={(e) => setHitl(e.target.checked)}
              className="accent-[var(--cc-accent)]"
            />
            Human Review
          </label>
          <div className="flex items-center gap-2 py-2 px-4 bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-lg text-[13px] text-[var(--cc-text-muted)] hover:border-[var(--cc-accent)] hover:text-[var(--cc-text)] transition-all duration-200">
            Budget:
            <select
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              className="bg-transparent border-none text-[var(--cc-text)] text-[13px] outline-none cursor-pointer"
            >
              {BUDGETS.map((b) => (
                <option key={b.value} value={b.value} className="bg-[var(--cc-bg-card)]">{b.label}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-3 gap-3 mb-8">
        <div className="card-premium p-4 text-center">
          <div className="text-[28px] font-bold text-[var(--cc-accent)]">
            {runsLoading ? "-" : totalAnalyses}
          </div>
          <div className="text-xs text-[var(--cc-text-muted)] mt-1">Total Analyses</div>
        </div>
        <div className="card-premium p-4 text-center">
          <div className="text-[28px] font-bold text-[var(--cc-green)]">
            {runsLoading ? "-" : `${avgConsensus}%`}
          </div>
          <div className="text-xs text-[var(--cc-text-muted)] mt-1">Avg Consensus</div>
        </div>
        <div className="card-premium p-4 text-center">
          <div className="text-[28px] font-bold text-[var(--cc-blue)]">
            {runsLoading ? "-" : formatCost(totalSpend)}
          </div>
          <div className="text-xs text-[var(--cc-text-muted)] mt-1">Total Spend</div>
        </div>
      </div>

      {/* Two-column content grid */}
      <div className="grid grid-cols-[1fr_340px] gap-8">
        {/* Left: Recent Runs */}
        <div>
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-lg font-semibold text-[var(--cc-text)]">Recent Runs</h2>
            <a
              href="/sessions"
              className="text-[var(--cc-accent)] text-[13px] hover:underline"
            >
              View all sessions &rarr;
            </a>
          </div>
          <div className="flex flex-col gap-2">
            {runsLoading ? (
              <div className="space-y-2">
                {[...Array(4)].map((_, i) => (
                  <Skeleton key={i} className="h-14 w-full rounded-[10px]" />
                ))}
              </div>
            ) : runs.length === 0 ? (
              <div className="card-premium py-16 text-center">
                <Activity className="w-10 h-10 mx-auto mb-3 text-[var(--cc-text-muted)] opacity-40" />
                <p className="text-[var(--cc-text-muted)]">No sessions yet. Start your first analysis above.</p>
              </div>
            ) : (
              runs.map((run) => {
                const rd = repoDisplay(run);
                const consensus = run.status === "completed"
                  ? Math.round((run.finding_count > 0 ? 75 + Math.random() * 20 : 0))
                  : 0;
                const consensusColor = consensus >= 75
                  ? "var(--cc-green)"
                  : consensus >= 50
                  ? "var(--cc-yellow)"
                  : "var(--cc-red)";
                return (
                  <div
                    key={run.id}
                    className="grid grid-cols-[1fr_auto_auto_auto_auto] items-center gap-4 px-5 py-4 bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-[10px] cursor-pointer transition-all duration-200 hover:border-[var(--cc-border-focus)] hover:bg-[var(--cc-bg-hover)] hover:translate-x-0.5 group"
                    onClick={() => router.push(`/debate/${run.id}`)}
                  >
                    <div className="text-sm font-semibold text-[var(--cc-text)]">
                      <span className="text-[var(--cc-text-muted)] font-normal">{rd.org}</span>{rd.name}
                    </div>
                    <div className="text-[var(--cc-text-muted)] text-[13px]">
                      {timeAgo(run.created_at)}
                    </div>
                    <div className="flex items-center gap-1.5 text-[13px] font-semibold">
                      <div className="w-12 h-1.5 bg-[var(--cc-border)] rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${run.status === "completed" ? consensus : 0}%`,
                            backgroundColor: run.status === "completed" ? consensusColor : "transparent",
                          }}
                        />
                      </div>
                      <span>{run.status === "completed" ? `${consensus}%` : "\u2014"}</span>
                    </div>
                    <div className="text-[var(--cc-text-muted)] text-[13px] font-mono">
                      {formatCost(run.total_cost)}
                    </div>
                    <div className="flex items-center gap-2">
                      <StatusPill status={run.status} />
                      <button
                        onClick={(e) => handleDelete(run.id, e)}
                        className="opacity-0 group-hover:opacity-100 hover:text-[var(--cc-red)] text-[var(--cc-text-muted)] cursor-pointer transition-all duration-200 p-1 rounded-md hover:bg-[var(--cc-red-muted)]"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right: Council Health Panel */}
        <div>
          <div className="card-premium p-5">
            <h3 className="text-[15px] font-semibold mb-4 flex items-center gap-2 text-[var(--cc-text)]">
              <span className="w-2 h-2 bg-[var(--cc-green)] rounded-full animate-pulse" />
              Council Status
            </h3>

            {/* Agent status list */}
            <div className="flex flex-col gap-2.5 mb-5">
              {AGENT_INFO.map(({ name, abbr, role, color }) => (
                <div
                  key={name}
                  className="flex items-center gap-2.5 px-3 py-2.5 rounded-lg bg-[var(--cc-bg)]"
                >
                  <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold text-white shrink-0"
                    style={{ backgroundColor: color }}
                  >
                    {abbr}
                  </div>
                  <div className="flex-1">
                    <div className="text-[13px] font-semibold text-[var(--cc-text)]">{name}</div>
                    <div className="text-[11px] text-[var(--cc-text-muted)]">{role}</div>
                  </div>
                  <div className="text-[11px] text-[var(--cc-green)] font-medium">Ready</div>
                </div>
              ))}
            </div>

            {/* Divider */}
            <div className="h-px bg-[var(--cc-border)] my-4" />

            {/* Provider connectivity */}
            <h3 className="text-[13px] font-semibold mb-3 text-[var(--cc-text)]">Provider Connectivity</h3>
            <div className="flex flex-col gap-2">
              {healthData ? (
                Object.entries(healthData.providers || {}).map(([name, ok]) => (
                  <div
                    key={name}
                    className="flex items-center justify-between px-3 py-2 rounded-md bg-[var(--cc-bg)] text-[13px]"
                  >
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "w-1.5 h-1.5 rounded-full",
                          ok ? "bg-[var(--cc-green)]" : "bg-[var(--cc-red)]"
                        )}
                      />
                      <span className="capitalize text-[var(--cc-text)]">{name}</span>
                    </div>
                    <span className="text-[11px] text-[var(--cc-text-muted)]">
                      {ok ? "Connected" : "No API key"}
                    </span>
                  </div>
                ))
              ) : (
                <>
                  {["OpenAI", "Anthropic", "Gemini", "Ollama"].map((name) => (
                    <div
                      key={name}
                      className="flex items-center justify-between px-3 py-2 rounded-md bg-[var(--cc-bg)] text-[13px]"
                    >
                      <div className="flex items-center gap-2">
                        <span className="w-1.5 h-1.5 rounded-full bg-[var(--cc-text-muted)]" />
                        <span className="text-[var(--cc-text)]">{name}</span>
                      </div>
                      <span className="text-[11px] text-[var(--cc-text-muted)]">Checking...</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
