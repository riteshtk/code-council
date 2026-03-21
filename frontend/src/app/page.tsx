"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import {
  Github,
  GitBranch,
  Folder,
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
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { cn, formatCost, timeAgo } from "@/lib/utils";
import { createRun, listRuns, deleteRun, health } from "@/lib/api";
import type { RunSummary, HealthStatus } from "@/lib/types";

const SOURCE_TABS = [
  { id: "github", label: "GitHub", icon: Github },
  { id: "gitlab", label: "GitLab", icon: GitBranch },
  { id: "bitbucket", label: "Bitbucket", icon: GitBranch },
  { id: "local", label: "Local", icon: Folder },
];

const TOPOLOGIES = [
  { value: "round_robin", label: "Round Robin" },
  { value: "adversarial", label: "Adversarial" },
  { value: "panel", label: "Panel" },
  { value: "socratic", label: "Socratic" },
];

const PROVIDERS = [
  { value: "openai", label: "OpenAI" },
  { value: "anthropic", label: "Anthropic" },
  { value: "gemini", label: "Google Gemini" },
  { value: "ollama", label: "Ollama (local)" },
];

const STATUS_CONFIG: Record<string, { colorClass: string; bgClass: string; icon: React.ReactNode }> = {
  running: {
    colorClass: "text-[var(--cc-yellow)]",
    bgClass: "bg-[var(--cc-yellow-muted)]",
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
};

const AGENT_INFO = [
  { name: "Archaeologist", icon: Eye, color: "var(--cc-archaeologist)" },
  { name: "Skeptic", icon: Shield, color: "var(--cc-skeptic)" },
  { name: "Visionary", icon: Brain, color: "var(--cc-visionary)" },
  { name: "Scribe", icon: PenTool, color: "var(--cc-scribe)" },
];

function StatusBadge({ status }: { status: string }) {
  const c = STATUS_CONFIG[status] || STATUS_CONFIG.pending;
  return (
    <span
      className={cn(
        "flex items-center gap-1.5 text-xs font-semibold px-2.5 py-1 rounded-full tracking-wide",
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
  const [topology, setTopology] = useState("round_robin");
  const [rounds, setRounds] = useState(3);
  const [hitl, setHitl] = useState(false);
  const [budget, setBudget] = useState("5.00");
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

  return (
    <div className="flex-1 p-6 lg:p-8 max-w-6xl mx-auto w-full animate-fade-in">
      {/* Hero */}
      <div className="mb-10 text-center">
        <h1 className="text-4xl sm:text-5xl font-bold mb-3 tracking-tight">
          <span className="gradient-text-accent">Summon the Council</span>
        </h1>
        <p className="text-base sm:text-lg text-[var(--cc-text-muted)] max-w-xl mx-auto leading-relaxed">
          Multi-agent AI council for deep code analysis and RFC generation
        </p>
        {/* Agent avatars row */}
        <div className="flex items-center justify-center gap-3 mt-5">
          {AGENT_INFO.map(({ name, icon: Icon, color }) => (
            <div key={name} className="flex items-center gap-1.5 group cursor-default">
              <div
                className="w-7 h-7 rounded-full flex items-center justify-center transition-all duration-300 group-hover:scale-110"
                style={{ backgroundColor: `color-mix(in srgb, ${color} 20%, transparent)` }}
              >
                <Icon className="w-3.5 h-3.5" style={{ color }} />
              </div>
              <span className="text-xs font-medium text-[var(--cc-text-muted)] hidden sm:inline group-hover:text-[var(--cc-text-secondary)] transition-colors duration-200">
                {name}
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input Panel */}
        <div className="lg:col-span-2 space-y-4">
          <div className="card-premium p-6 space-y-5">
            <div className="flex items-center gap-2 mb-1">
              <Zap className="w-5 h-5 text-[var(--cc-accent)]" />
              <h2 className="text-lg font-semibold text-[var(--cc-text)]">
                Analyse a Repository
              </h2>
            </div>

            {/* Source tabs */}
            <div className="flex gap-1 p-1 rounded-xl bg-[var(--cc-bg)]">
              {SOURCE_TABS.map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setSourceTab(id)}
                  className={cn(
                    "flex-1 flex items-center justify-center gap-2 py-2.5 px-3 rounded-lg text-sm font-medium cursor-pointer transition-all duration-300",
                    sourceTab === id
                      ? "bg-[var(--cc-accent)] text-white shadow-[0_2px_12px_rgba(108,92,231,0.35)]"
                      : "text-[var(--cc-text-muted)] hover:text-[var(--cc-text)] hover:bg-[var(--cc-bg-hover)]"
                  )}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>

            {/* URL / Path input */}
            {sourceTab === "local" ? (
              <Input
                placeholder="/path/to/your/project"
                value={localPath}
                onChange={(e) => setLocalPath(e.target.value)}
                className="h-12 text-base rounded-xl"
              />
            ) : (
              <Input
                placeholder={`https://${sourceTab}.com/owner/repo`}
                value={repoUrl}
                onChange={(e) => setRepoUrl(e.target.value)}
                className="h-12 text-base rounded-xl"
              />
            )}

            <Separator className="opacity-50" />

            {/* Quick config */}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">
                  Provider
                </label>
                <Select value={provider} onValueChange={(v) => v && setProvider(v)}>
                  <SelectTrigger className="rounded-lg">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {PROVIDERS.map((p) => (
                      <SelectItem key={p.value} value={p.value}>
                        {p.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">
                  Topology
                </label>
                <Select value={topology} onValueChange={(v) => v && setTopology(v)}>
                  <SelectTrigger className="rounded-lg">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TOPOLOGIES.map((t) => (
                      <SelectItem key={t.value} value={t.value}>
                        {t.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">
                  Rounds: <span className="text-[var(--cc-accent)] font-bold">{rounds}</span>
                </label>
                <input
                  type="range"
                  min={1}
                  max={10}
                  value={rounds}
                  onChange={(e) => setRounds(Number(e.target.value))}
                  className="w-full accent-[var(--cc-accent)] cursor-pointer"
                />
              </div>

              <div className="space-y-1.5">
                <label className="text-xs font-medium text-[var(--cc-text-muted)] uppercase tracking-wider">
                  Budget ($)
                </label>
                <Input
                  type="number"
                  min="0"
                  step="0.5"
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  className="rounded-lg"
                />
              </div>
            </div>

            {/* HITL toggle */}
            <div className="flex items-center gap-3">
              <button
                onClick={() => setHitl(!hitl)}
                className={cn(
                  "relative inline-flex h-6 w-11 items-center rounded-full cursor-pointer transition-colors duration-300",
                  hitl ? "bg-[var(--cc-accent)]" : "bg-[var(--cc-bg-active)]"
                )}
              >
                <span
                  className={cn(
                    "inline-block h-4 w-4 transform rounded-full bg-white transition-transform duration-300",
                    hitl ? "translate-x-6" : "translate-x-1"
                  )}
                />
              </button>
              <span className="text-sm text-[var(--cc-text-secondary)]">
                Human-in-the-loop review
              </span>
            </div>

            {/* Submit */}
            <Button
              onClick={handleAnalyse}
              disabled={submitting}
              className="w-full font-semibold h-12 rounded-xl text-base hover-lift cursor-pointer"
            >
              {submitting ? (
                <Loader2 className="w-4 h-4 mr-2 animate-spin" />
              ) : (
                <Play className="w-4 h-4 mr-2" />
              )}
              {submitting ? "Starting analysis..." : "Analyse Repository"}
            </Button>
          </div>
        </div>

        {/* Right panel */}
        <div className="space-y-4">
          {/* Stats */}
          <div className="grid grid-cols-3 gap-3">
            <div className="card-premium p-4 text-center hover-lift">
              <div className="text-2xl font-bold font-mono text-[var(--cc-accent)]">
                {runsLoading ? "-" : runs.length}
              </div>
              <div className="text-xs text-[var(--cc-text-muted)] mt-1">Runs</div>
            </div>
            <div className="card-premium p-4 text-center hover-lift">
              <div className="text-2xl font-bold font-mono text-[var(--cc-green)]">
                {runsLoading ? "-" : runs.filter((r) => r.status === "completed").length}
              </div>
              <div className="text-xs text-[var(--cc-text-muted)] mt-1">Done</div>
            </div>
            <div className="card-premium p-4 text-center hover-lift">
              <div className="text-2xl font-bold font-mono text-[var(--cc-yellow)]">
                {runsLoading ? "-" : runs.reduce((s, r) => s + r.finding_count, 0)}
              </div>
              <div className="text-xs text-[var(--cc-text-muted)] mt-1">Findings</div>
            </div>
          </div>

          {/* Health */}
          <div className="card-premium p-5">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-4 h-4 text-[var(--cc-green)]" />
              <h3 className="text-sm font-semibold text-[var(--cc-text)]">Council Health</h3>
            </div>
            {healthData ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--cc-text-muted)]">Status</span>
                  <span
                    className={cn(
                      "text-xs font-semibold",
                      healthData.status === "healthy"
                        ? "text-[var(--cc-green)]"
                        : healthData.status === "degraded"
                        ? "text-[var(--cc-yellow)]"
                        : "text-[var(--cc-red)]"
                    )}
                  >
                    {healthData.status}
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-xs text-[var(--cc-text-muted)]">Database</span>
                  <span
                    className={cn(
                      "text-xs font-medium",
                      healthData.database ? "text-[var(--cc-green)]" : "text-[var(--cc-red)]"
                    )}
                  >
                    {healthData.database ? "connected" : "error"}
                  </span>
                </div>
                {Object.entries(healthData.providers || {}).map(([name, ok]) => (
                  <div key={name} className="flex items-center justify-between">
                    <span className="text-xs text-[var(--cc-text-muted)]">{name}</span>
                    <div className="flex items-center gap-1.5">
                      <div
                        className={cn(
                          "w-2 h-2 rounded-full transition-colors duration-200",
                          ok ? "bg-[var(--cc-green)]" : "bg-[var(--cc-red)]"
                        )}
                      />
                      <span
                        className={cn(
                          "text-xs font-medium",
                          ok ? "text-[var(--cc-green)]" : "text-[var(--cc-red)]"
                        )}
                      >
                        {ok ? "ok" : "error"}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-2">
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            )}
          </div>

          {/* Agents panel */}
          <div className="card-premium p-5">
            <div className="flex items-center gap-2 mb-4">
              <Users className="w-4 h-4 text-[var(--cc-accent)]" />
              <h3 className="text-sm font-semibold text-[var(--cc-text)]">The Council</h3>
            </div>
            <div className="space-y-2.5">
              {AGENT_INFO.map(({ name, icon: Icon, color }) => (
                <div
                  key={name}
                  className="flex items-center gap-3 px-3 py-2 rounded-lg bg-[var(--cc-bg)] transition-colors duration-200 hover:bg-[var(--cc-bg-hover)]"
                >
                  <div
                    className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
                    style={{ backgroundColor: `color-mix(in srgb, ${color} 18%, transparent)` }}
                  >
                    <Icon className="w-4 h-4" style={{ color }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-[var(--cc-text)]">{name}</div>
                    <div className="text-xs text-[var(--cc-text-muted)]">Ready</div>
                  </div>
                  <div className="w-2 h-2 rounded-full bg-[var(--cc-green)]" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Recent Runs */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold mb-4 text-[var(--cc-text)]">
          Recent Sessions
        </h2>
        <div className="card-premium overflow-hidden">
          {runsLoading ? (
            <div className="p-4 space-y-3">
              {[...Array(3)].map((_, i) => (
                <Skeleton key={i} className="h-14 w-full rounded-lg" />
              ))}
            </div>
          ) : runs.length === 0 ? (
            <div className="py-16 text-center">
              <Activity className="w-10 h-10 mx-auto mb-3 text-[var(--cc-text-muted)] opacity-40" />
              <p className="text-[var(--cc-text-muted)]">No sessions yet. Start your first analysis above.</p>
            </div>
          ) : (
            <div className="divide-y divide-[var(--cc-border)]">
              {runs.map((run) => (
                <div
                  key={run.id}
                  className="flex items-center gap-4 px-5 py-4 cursor-pointer hover:bg-[var(--cc-bg-hover)] transition-all duration-300 group"
                  onClick={() => router.push(`/debate/${run.id}`)}
                >
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium truncate text-[var(--cc-text)] group-hover:text-white transition-colors duration-200">
                      {run.repo?.url || run.repo?.local_path || run.id}
                    </div>
                    <div className="text-xs mt-0.5 text-[var(--cc-text-muted)]">
                      {timeAgo(run.created_at)}
                    </div>
                  </div>
                  <div className="flex items-center gap-3 shrink-0">
                    <div className="flex items-center gap-1 text-xs font-mono text-[var(--cc-text-muted)]">
                      <DollarSign className="w-3 h-3" />
                      {formatCost(run.total_cost)}
                    </div>
                    <Badge
                      variant="outline"
                      className="text-xs border-[var(--cc-border)] text-[var(--cc-text-muted)]"
                    >
                      {run.finding_count} findings
                    </Badge>
                    <StatusBadge status={run.status} />
                    <button
                      onClick={(e) => handleDelete(run.id, e)}
                      className="opacity-0 group-hover:opacity-100 hover:text-[var(--cc-red)] text-[var(--cc-text-muted)] cursor-pointer transition-all duration-200 p-1 rounded-md hover:bg-[var(--cc-red-muted)]"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
