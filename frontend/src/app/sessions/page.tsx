"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { listRuns, deleteRun } from "@/lib/api";
import type { RunSummary } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Search,
  Trash2,
  ExternalLink,
  FileText,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  BarChart3,
  AlertTriangle,
  Eye,
  Shield,
  Brain,
  PenTool,
  RefreshCw,
  TrendingUp,
  DollarSign,
  Layers,
} from "lucide-react";
import { cn, formatCost, timeAgo, getAgentColor } from "@/lib/utils";
import { toast } from "sonner";

/* ─── Agent metadata ─── */
const AGENTS = [
  { handle: "archaeologist", label: "Archaeologist", role: "Historian", icon: Eye, color: "#d4a574" },
  { handle: "skeptic",       label: "Skeptic",       role: "Challenger", icon: Shield, color: "#ff6b6b" },
  { handle: "visionary",     label: "Visionary",     role: "Proposer", icon: Brain, color: "#6c5ce7" },
  { handle: "scribe",        label: "Scribe",        role: "Secretary", icon: PenTool, color: "#4ecdc4" },
];

/* ─── Status badge ─── */
function StatusBadge({ status }: { status: string }) {
  const map: Record<string, { color: string; bg: string; icon: React.ReactNode }> = {
    running:   { color: "var(--cc-yellow)", bg: "var(--cc-yellow-muted)", icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    completed: { color: "var(--cc-green)",  bg: "var(--cc-green-muted)",  icon: <CheckCircle2 className="w-3 h-3" /> },
    failed:    { color: "var(--cc-red)",    bg: "var(--cc-red-muted)",    icon: <XCircle className="w-3 h-3" /> },
    pending:   { color: "var(--cc-text-muted)", bg: "var(--cc-bg-hover)", icon: <Clock className="w-3 h-3" /> },
  };
  const s = map[status] || map.pending;
  return (
    <span
      className="inline-flex items-center gap-1.5 text-[11px] font-semibold px-2.5 py-1 rounded-full capitalize"
      style={{ color: s.color, backgroundColor: s.bg }}
    >
      {s.icon} {status}
    </span>
  );
}

/* ─── Stat card ─── */
function StatCard({ label, value, icon: Icon, color }: {
  label: string; value: string | number;
  icon: React.ComponentType<{ className?: string }>;
  color: string;
}) {
  return (
    <div className="card-premium p-4 hover-lift group">
      <div className="flex items-center gap-3">
        <div
          className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0 transition-transform duration-300 group-hover:scale-110"
          style={{ backgroundColor: `${color}15` }}
        >
          <span style={{ color }}><Icon className="w-4 h-4" /></span>
        </div>
        <div>
          <div className="text-xl font-bold font-mono" style={{ color }}>{value}</div>
          <div className="text-[11px] text-[var(--cc-text-muted)] font-medium uppercase tracking-wider">{label}</div>
        </div>
      </div>
    </div>
  );
}

/* ─── Main page ─── */
export default function SessionsPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => { loadRuns(); }, []);

  async function loadRuns() {
    setLoading(true);
    try {
      const data = await listRuns({ limit: 100 });
      setRuns(data);
    } catch {
      setRuns([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleDelete(runId: string, e: React.MouseEvent) {
    e.stopPropagation();
    setDeleting(runId);
    try {
      await deleteRun(runId);
      setRuns((prev) => prev.filter((r) => r.id !== runId));
      toast.success("Session deleted");
    } catch {
      toast.error("Failed to delete session");
    } finally {
      setDeleting(null);
    }
  }

  const filtered = useMemo(() => {
    return runs.filter((r) => {
      if (statusFilter !== "all" && r.status !== statusFilter) return false;
      if (search) {
        const s = search.toLowerCase();
        return (
          r.id.toLowerCase().includes(s) ||
          (r.repo?.url || "").toLowerCase().includes(s) ||
          (r.repo?.local_path || "").toLowerCase().includes(s)
        );
      }
      return true;
    });
  }, [runs, search, statusFilter]);

  const stats = useMemo(() => ({
    total: runs.length,
    running: runs.filter((r) => r.status === "running").length,
    completed: runs.filter((r) => r.status === "completed").length,
    failed: runs.filter((r) => r.status === "failed").length,
    totalFindings: runs.reduce((s, r) => s + r.finding_count, 0),
    totalCost: runs.reduce((s, r) => s + r.total_cost, 0),
  }), [runs]);

  return (
    <div className="flex-1 p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--cc-text)] tracking-tight">Sessions</h1>
          <p className="text-sm text-[var(--cc-text-muted)] mt-1">
            Browse and manage all council analysis sessions
          </p>
        </div>
        <Button variant="outline" onClick={loadRuns} className="cursor-pointer rounded-lg gap-2">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </Button>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
        <StatCard label="Total" value={stats.total} icon={Layers} color="var(--cc-text-secondary)" />
        <StatCard label="Running" value={stats.running} icon={Loader2} color="var(--cc-yellow)" />
        <StatCard label="Completed" value={stats.completed} icon={CheckCircle2} color="var(--cc-green)" />
        <StatCard label="Failed" value={stats.failed} icon={XCircle} color="var(--cc-red)" />
        <StatCard label="Findings" value={stats.totalFindings} icon={TrendingUp} color="var(--cc-yellow)" />
        <StatCard label="Total Cost" value={formatCost(stats.totalCost)} icon={DollarSign} color="var(--cc-green)" />
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--cc-text-muted)]" />
          <Input
            placeholder="Search by repo or session ID..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 rounded-lg"
          />
        </div>
        <Select value={statusFilter} onValueChange={(v) => v && setStatusFilter(v)}>
          <SelectTrigger className="w-40 rounded-lg cursor-pointer">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            {[
              { value: "all", label: "All statuses" },
              { value: "running", label: "Running" },
              { value: "completed", label: "Completed" },
              { value: "failed", label: "Failed" },
              { value: "pending", label: "Pending" },
            ].map((opt) => (
              <SelectItem key={opt.value} value={opt.value} className="cursor-pointer">{opt.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Sessions list */}
      <div className="space-y-2">
        {loading ? (
          <div className="space-y-2">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-[72px] w-full rounded-xl" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="card-premium py-20 text-center">
            <BarChart3 className="w-12 h-12 mx-auto mb-4 text-[var(--cc-text-muted)] opacity-30" />
            <p className="text-lg font-medium text-[var(--cc-text-muted)]">No sessions found</p>
            <p className="text-sm text-[var(--cc-text-muted)] mt-1 opacity-60">
              {search || statusFilter !== "all" ? "Try adjusting your filters" : "Run your first analysis from the home page"}
            </p>
          </div>
        ) : (
          filtered.map((run) => (
            <div
              key={run.id}
              className="card-premium group flex items-center gap-4 px-5 py-4 cursor-pointer hover:border-[var(--cc-border-hover)] hover:bg-[var(--cc-bg-elevated)] transition-all duration-200"
              onClick={() => router.push(`/debate/${run.id}`)}
            >
              {/* Status */}
              <div className="shrink-0">
                <StatusBadge status={run.status} />
              </div>

              {/* Repo info */}
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-[var(--cc-text)] truncate group-hover:text-white transition-colors duration-200">
                  {run.repo?.url || run.repo?.local_path || "Unknown repository"}
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-[var(--cc-text-muted)]">
                  <span className="font-mono">{run.id.slice(0, 8)}</span>
                  <span>·</span>
                  <span>{timeAgo(run.created_at)}</span>
                  {run.phase && (
                    <>
                      <span>·</span>
                      <span className="text-[var(--cc-accent)]">{run.phase}</span>
                    </>
                  )}
                </div>
              </div>

              {/* Metrics */}
              <div className="hidden md:flex items-center gap-6 shrink-0 text-xs">
                <div className="text-center">
                  <div className="font-bold font-mono text-[var(--cc-text)]">{run.finding_count}</div>
                  <div className="text-[var(--cc-text-muted)]">findings</div>
                </div>
                <div className="text-center">
                  <div className="font-bold font-mono text-[var(--cc-text)]">{run.proposal_count || 0}</div>
                  <div className="text-[var(--cc-text-muted)]">proposals</div>
                </div>
                <div className="text-center">
                  <div className="font-bold font-mono text-[var(--cc-green)]">{formatCost(run.total_cost)}</div>
                  <div className="text-[var(--cc-text-muted)]">cost</div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200" onClick={(e) => e.stopPropagation()}>
                <button
                  onClick={() => router.push(`/debate/${run.id}`)}
                  className="p-2 rounded-lg cursor-pointer hover:bg-[var(--cc-bg-hover)] transition-colors duration-200"
                  title="View debate"
                >
                  <ExternalLink className="w-4 h-4 text-[var(--cc-text-muted)]" />
                </button>
                {run.status === "completed" && (
                  <button
                    onClick={() => router.push(`/rfc/${run.id}`)}
                    className="p-2 rounded-lg cursor-pointer hover:bg-[var(--cc-accent-muted)] transition-colors duration-200"
                    title="View RFC"
                  >
                    <FileText className="w-4 h-4 text-[var(--cc-accent)]" />
                  </button>
                )}
                <button
                  onClick={(e) => handleDelete(run.id, e)}
                  disabled={deleting === run.id}
                  className="p-2 rounded-lg cursor-pointer hover:bg-[var(--cc-red-muted)] transition-colors duration-200"
                  title="Delete"
                >
                  {deleting === run.id
                    ? <Loader2 className="w-4 h-4 animate-spin text-[var(--cc-text-muted)]" />
                    : <Trash2 className="w-4 h-4 text-[var(--cc-text-muted)] hover:text-[var(--cc-red)]" />
                  }
                </button>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Agent Memory section */}
      <div>
        <h2 className="text-lg font-semibold text-[var(--cc-text)] tracking-tight mb-4">
          Agent Memory
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {AGENTS.map(({ handle, label, role, icon: Icon, color }) => {
            const sessionCount = runs.filter((r) => r.status === "completed").length;
            return (
              <div key={handle} className="card-premium overflow-hidden hover-lift group">
                {/* Colored top accent line */}
                <div className="h-0.5 w-full" style={{ backgroundColor: color }} />

                <div className="p-5">
                  {/* Agent header */}
                  <div className="flex items-center gap-3 mb-4">
                    <div
                      className="w-10 h-10 rounded-xl flex items-center justify-center shrink-0 transition-transform duration-300 group-hover:scale-105"
                      style={{ backgroundColor: `${color}12` }}
                    >
                      <span style={{ color }}><Icon className="w-5 h-5" /></span>
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-[var(--cc-text)]">{label}</div>
                      <div className="text-[11px] font-medium uppercase tracking-wider" style={{ color }}>{role}</div>
                    </div>
                  </div>

                  {/* Stats */}
                  <div className="space-y-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-[var(--cc-text-muted)]">Sessions</span>
                      <span className="text-xs font-bold font-mono text-[var(--cc-text)]">{sessionCount}</span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-[var(--cc-text-muted)]">Memory</span>
                      <span className="text-xs font-medium" style={{ color }}>
                        {sessionCount > 0 ? "Active" : "Empty"}
                      </span>
                    </div>
                    <div className="w-full h-1 rounded-full bg-[var(--cc-bg-active)] mt-1 overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-500"
                        style={{
                          width: sessionCount > 0 ? `${Math.min(sessionCount * 15, 100)}%` : "0%",
                          backgroundColor: color,
                          opacity: 0.7,
                        }}
                      />
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
