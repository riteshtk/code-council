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

function StatusBadge({ status }: { status: string }) {
  const cfg: Record<string, { color: string; icon: React.ReactNode }> = {
    running: { color: "var(--cc-yellow)", icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    completed: { color: "var(--cc-green)", icon: <CheckCircle2 className="w-3 h-3" /> },
    failed: { color: "var(--cc-red)", icon: <XCircle className="w-3 h-3" /> },
    pending: { color: "var(--cc-text-muted)", icon: <Clock className="w-3 h-3" /> },
  };
  const c = cfg[status] || cfg.pending;
  return (
    <span
      className="flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full"
      style={{ color: c.color, backgroundColor: `${c.color}22` }}
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
    <div
      className="flex-1 p-6 max-w-6xl mx-auto w-full"
      style={{ color: "var(--cc-text)" }}
    >
      {/* Hero */}
      <div className="mb-8 text-center">
        <h1 className="text-4xl font-bold mb-2">
          <span style={{ color: "var(--cc-text)" }}>Code</span>
          <span style={{ color: "var(--cc-accent)" }}>Council</span>
        </h1>
        <p style={{ color: "var(--cc-text-muted)" }} className="text-lg">
          Multi-agent AI council for deep code analysis and RFC generation
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Input Panel */}
        <div className="lg:col-span-2 space-y-4">
          <Card
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
            }}
          >
            <CardHeader>
              <CardTitle style={{ color: "var(--cc-text)" }}>
                Analyse a Repository
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Source tabs */}
              <div
                className="flex gap-1 p-1 rounded-lg"
                style={{ backgroundColor: "var(--cc-bg)" }}
              >
                {SOURCE_TABS.map(({ id, label, icon: Icon }) => (
                  <button
                    key={id}
                    onClick={() => setSourceTab(id)}
                    className={cn(
                      "flex-1 flex items-center justify-center gap-2 py-2 px-3 rounded-md text-sm font-medium transition-all"
                    )}
                    style={{
                      backgroundColor:
                        sourceTab === id ? "var(--cc-accent)" : "transparent",
                      color:
                        sourceTab === id ? "white" : "var(--cc-text-muted)",
                    }}
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
                  style={{
                    backgroundColor: "var(--cc-bg)",
                    borderColor: "var(--cc-border)",
                    color: "var(--cc-text)",
                  }}
                />
              ) : (
                <Input
                  placeholder={`https://${sourceTab}.com/owner/repo`}
                  value={repoUrl}
                  onChange={(e) => setRepoUrl(e.target.value)}
                  style={{
                    backgroundColor: "var(--cc-bg)",
                    borderColor: "var(--cc-border)",
                    color: "var(--cc-text)",
                  }}
                />
              )}

              <Separator style={{ backgroundColor: "var(--cc-border)" }} />

              {/* Quick config */}
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <label
                    className="text-xs font-medium"
                    style={{ color: "var(--cc-text-muted)" }}
                  >
                    Provider
                  </label>
                  <Select value={provider} onValueChange={(v) => v && setProvider(v)}>
                    <SelectTrigger
                      style={{
                        backgroundColor: "var(--cc-bg)",
                        borderColor: "var(--cc-border)",
                        color: "var(--cc-text)",
                      }}
                    >
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

                <div className="space-y-1">
                  <label
                    className="text-xs font-medium"
                    style={{ color: "var(--cc-text-muted)" }}
                  >
                    Topology
                  </label>
                  <Select value={topology} onValueChange={(v) => v && setTopology(v)}>
                    <SelectTrigger
                      style={{
                        backgroundColor: "var(--cc-bg)",
                        borderColor: "var(--cc-border)",
                        color: "var(--cc-text)",
                      }}
                    >
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

                <div className="space-y-1">
                  <label
                    className="text-xs font-medium"
                    style={{ color: "var(--cc-text-muted)" }}
                  >
                    Debate Rounds: {rounds}
                  </label>
                  <input
                    type="range"
                    min={1}
                    max={10}
                    value={rounds}
                    onChange={(e) => setRounds(Number(e.target.value))}
                    className="w-full"
                    style={{ accentColor: "var(--cc-accent)" }}
                  />
                </div>

                <div className="space-y-1">
                  <label
                    className="text-xs font-medium"
                    style={{ color: "var(--cc-text-muted)" }}
                  >
                    Budget Limit ($)
                  </label>
                  <Input
                    type="number"
                    min="0"
                    step="0.5"
                    value={budget}
                    onChange={(e) => setBudget(e.target.value)}
                    style={{
                      backgroundColor: "var(--cc-bg)",
                      borderColor: "var(--cc-border)",
                      color: "var(--cc-text)",
                    }}
                  />
                </div>
              </div>

              {/* HITL toggle */}
              <div className="flex items-center gap-3">
                <button
                  onClick={() => setHitl(!hitl)}
                  className="relative inline-flex h-6 w-11 items-center rounded-full transition-colors"
                  style={{
                    backgroundColor: hitl
                      ? "var(--cc-accent)"
                      : "var(--cc-border)",
                  }}
                >
                  <span
                    className={cn(
                      "inline-block h-4 w-4 transform rounded-full bg-white transition-transform",
                      hitl ? "translate-x-6" : "translate-x-1"
                    )}
                  />
                </button>
                <span
                  className="text-sm"
                  style={{ color: "var(--cc-text-muted)" }}
                >
                  Human-in-the-loop review
                </span>
              </div>

              {/* Submit */}
              <Button
                onClick={handleAnalyse}
                disabled={submitting}
                className="w-full font-semibold"
                style={{
                  backgroundColor: "var(--cc-accent)",
                  color: "white",
                }}
              >
                {submitting ? (
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                ) : (
                  <Play className="w-4 h-4 mr-2" />
                )}
                {submitting ? "Starting analysis…" : "Analyse"}
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Right panel */}
        <div className="space-y-4">
          {/* Health */}
          <Card
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
            }}
          >
            <CardHeader className="pb-3">
              <CardTitle
                className="text-sm flex items-center gap-2"
                style={{ color: "var(--cc-text)" }}
              >
                <Activity className="w-4 h-4" style={{ color: "var(--cc-green)" }} />
                Council Health
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {healthData ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-xs" style={{ color: "var(--cc-text-muted)" }}>
                      Status
                    </span>
                    <span
                      className="text-xs font-medium"
                      style={{
                        color:
                          healthData.status === "healthy"
                            ? "var(--cc-green)"
                            : healthData.status === "degraded"
                            ? "var(--cc-yellow)"
                            : "var(--cc-red)",
                      }}
                    >
                      {healthData.status}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-xs" style={{ color: "var(--cc-text-muted)" }}>
                      Database
                    </span>
                    <span
                      className="text-xs"
                      style={{ color: healthData.database ? "var(--cc-green)" : "var(--cc-red)" }}
                    >
                      {healthData.database ? "connected" : "error"}
                    </span>
                  </div>
                  {Object.entries(healthData.providers || {}).map(([name, ok]) => (
                    <div key={name} className="flex items-center justify-between">
                      <span className="text-xs" style={{ color: "var(--cc-text-muted)" }}>
                        {name}
                      </span>
                      <span
                        className="text-xs"
                        style={{ color: ok ? "var(--cc-green)" : "var(--cc-red)" }}
                      >
                        {ok ? "ok" : "error"}
                      </span>
                    </div>
                  ))}
                </>
              ) : (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-full" />
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                </div>
              )}
            </CardContent>
          </Card>

          {/* Stats */}
          <Card
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
            }}
          >
            <CardHeader className="pb-3">
              <CardTitle
                className="text-sm flex items-center gap-2"
                style={{ color: "var(--cc-text)" }}
              >
                <Users className="w-4 h-4" style={{ color: "var(--cc-accent)" }} />
                Quick Stats
              </CardTitle>
            </CardHeader>
            <CardContent>
              {runsLoading ? (
                <Skeleton className="h-16 w-full" />
              ) : (
                <div className="grid grid-cols-3 gap-2 text-center">
                  <div>
                    <div className="text-2xl font-bold" style={{ color: "var(--cc-accent)" }}>
                      {runs.length}
                    </div>
                    <div className="text-xs" style={{ color: "var(--cc-text-muted)" }}>
                      Runs
                    </div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold" style={{ color: "var(--cc-green)" }}>
                      {runs.filter((r) => r.status === "completed").length}
                    </div>
                    <div className="text-xs" style={{ color: "var(--cc-text-muted)" }}>
                      Done
                    </div>
                  </div>
                  <div>
                    <div className="text-2xl font-bold" style={{ color: "var(--cc-yellow)" }}>
                      {runs.reduce((s, r) => s + r.finding_count, 0)}
                    </div>
                    <div className="text-xs" style={{ color: "var(--cc-text-muted)" }}>
                      Findings
                    </div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Recent Runs */}
      <div className="mt-6">
        <h2 className="text-lg font-semibold mb-3" style={{ color: "var(--cc-text)" }}>
          Recent Sessions
        </h2>
        <Card
          style={{
            backgroundColor: "var(--cc-bg-card)",
            borderColor: "var(--cc-border)",
          }}
        >
          <CardContent className="p-0">
            {runsLoading ? (
              <div className="p-4 space-y-3">
                {[...Array(3)].map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : runs.length === 0 ? (
              <div className="py-12 text-center" style={{ color: "var(--cc-text-muted)" }}>
                <Activity className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No sessions yet. Start your first analysis above.</p>
              </div>
            ) : (
              <div className="divide-y" style={{ borderColor: "var(--cc-border)" }}>
                {runs.map((run) => (
                  <div
                    key={run.id}
                    className="flex items-center gap-4 px-4 py-3 cursor-pointer hover:bg-white/5 transition-colors"
                    onClick={() => router.push(`/debate/${run.id}`)}
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate" style={{ color: "var(--cc-text)" }}>
                        {run.repo?.url || run.repo?.local_path || run.id}
                      </div>
                      <div className="text-xs mt-0.5" style={{ color: "var(--cc-text-muted)" }}>
                        {timeAgo(run.created_at)}
                      </div>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <div
                        className="flex items-center gap-1 text-xs"
                        style={{ color: "var(--cc-text-muted)" }}
                      >
                        <DollarSign className="w-3 h-3" />
                        {formatCost(run.total_cost)}
                      </div>
                      <Badge
                        variant="outline"
                        className="text-xs"
                        style={{ borderColor: "var(--cc-border)", color: "var(--cc-text-muted)" }}
                      >
                        {run.finding_count} findings
                      </Badge>
                      <StatusBadge status={run.status} />
                      <button
                        onClick={(e) => handleDelete(run.id, e)}
                        className="opacity-40 hover:opacity-100 transition-opacity"
                        style={{ color: "var(--cc-red)" }}
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
