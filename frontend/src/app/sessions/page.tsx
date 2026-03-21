"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import { listRuns, deleteRun } from "@/lib/api";
import type { RunSummary } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
} from "lucide-react";
import { cn, formatCost, timeAgo, getAgentColor } from "@/lib/utils";
import { toast } from "sonner";

const AGENT_ROLES = ["archaeologist", "skeptic", "visionary", "scribe"];

const AGENT_ICONS: Record<string, React.ComponentType<{ className?: string; style?: React.CSSProperties }>> = {
  archaeologist: Eye,
  skeptic: Shield,
  visionary: Brain,
  scribe: PenTool,
};

const AGENT_DESCRIPTIONS: Record<string, string> = {
  archaeologist: "Historian",
  skeptic: "Devil's Advocate",
  visionary: "Architect",
  scribe: "Scribe",
};

function StatusIcon({ status }: { status: string }) {
  if (status === "running") return <Loader2 className="w-4 h-4 animate-spin text-[var(--cc-yellow)]" />;
  if (status === "completed") return <CheckCircle2 className="w-4 h-4 text-[var(--cc-green)]" />;
  if (status === "failed") return <XCircle className="w-4 h-4 text-[var(--cc-red)]" />;
  return <Clock className="w-4 h-4 text-[var(--cc-text-muted)]" />;
}

function SeverityBar({ finding_count }: { finding_count: number }) {
  if (finding_count === 0) return <span className="text-[var(--cc-text-muted)]">--</span>;
  return (
    <div className="flex items-center gap-1.5">
      <AlertTriangle className="w-3 h-3 text-[var(--cc-yellow)]" />
      <span className="text-sm font-medium text-[var(--cc-text)]">{finding_count}</span>
    </div>
  );
}

export default function SessionsPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    loadRuns();
  }, []);

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
    <div className="flex-1 p-6 lg:p-8 max-w-7xl mx-auto w-full space-y-6 animate-fade-in">
      <div>
        <h1 className="text-2xl font-bold text-[var(--cc-text)] tracking-tight">Sessions</h1>
        <p className="text-sm text-[var(--cc-text-muted)] mt-1">
          All analysis sessions and their results
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {[
          { label: "Total", value: stats.total, colorClass: "text-[var(--cc-text)]", icon: BarChart3 },
          { label: "Running", value: stats.running, colorClass: "text-[var(--cc-yellow)]", icon: Loader2 },
          { label: "Completed", value: stats.completed, colorClass: "text-[var(--cc-green)]", icon: CheckCircle2 },
          { label: "Failed", value: stats.failed, colorClass: "text-[var(--cc-red)]", icon: XCircle },
          { label: "Findings", value: stats.totalFindings, colorClass: "text-[var(--cc-yellow)]", icon: AlertTriangle },
          { label: "Total Cost", value: formatCost(stats.totalCost), colorClass: "text-[var(--cc-green)]", icon: null },
        ].map(({ label, value, colorClass, icon: Icon }) => (
          <div
            key={label}
            className="card-premium p-3 text-center hover-lift"
          >
            {Icon && <Icon className={cn("w-4 h-4 mx-auto mb-1", colorClass)} />}
            <div className={cn("text-xl font-bold font-mono", colorClass)}>{value}</div>
            <div className="text-xs text-[var(--cc-text-muted)] mt-0.5">{label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--cc-text-muted)]" />
          <Input
            placeholder="Search sessions..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 rounded-lg"
          />
        </div>

        <Select value={statusFilter} onValueChange={(v) => v && setStatusFilter(v)}>
          <SelectTrigger className="w-36 rounded-lg">
            <SelectValue placeholder="All statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All statuses</SelectItem>
            <SelectItem value="running">Running</SelectItem>
            <SelectItem value="completed">Completed</SelectItem>
            <SelectItem value="failed">Failed</SelectItem>
            <SelectItem value="pending">Pending</SelectItem>
          </SelectContent>
        </Select>

        <Button variant="outline" size="sm" onClick={loadRuns} className="cursor-pointer rounded-lg">
          Refresh
        </Button>
      </div>

      {/* Table */}
      <div className="card-premium overflow-hidden">
        {loading ? (
          <div className="p-4 space-y-3">
            {[...Array(5)].map((_, i) => (
              <Skeleton key={i} className="h-14 w-full rounded-lg" />
            ))}
          </div>
        ) : filtered.length === 0 ? (
          <div className="py-16 text-center">
            <BarChart3 className="w-10 h-10 mx-auto mb-3 text-[var(--cc-text-muted)] opacity-40" />
            <p className="text-[var(--cc-text-muted)]">No sessions found</p>
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow className="border-[var(--cc-border)]">
                {["Status", "Repository", "Created", "Phase", "Findings", "Proposals", "Cost", "Actions"].map((h) => (
                  <TableHead
                    key={h}
                    className="text-xs font-semibold text-[var(--cc-text-muted)] uppercase tracking-wider"
                  >
                    {h}
                  </TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((run) => (
                <TableRow
                  key={run.id}
                  className="cursor-pointer hover:bg-[var(--cc-bg-hover)] transition-all duration-300 border-[var(--cc-border)] group"
                  onClick={() => router.push(`/debate/${run.id}`)}
                >
                  <TableCell>
                    <StatusIcon status={run.status} />
                  </TableCell>
                  <TableCell>
                    <div className="text-sm font-medium max-w-xs truncate text-[var(--cc-text)] group-hover:text-white transition-colors duration-200">
                      {run.repo?.url || run.repo?.local_path || run.id}
                    </div>
                    <div className="text-xs mt-0.5 font-mono text-[var(--cc-text-muted)]">
                      {run.id.slice(0, 8)}...
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-xs text-[var(--cc-text-muted)]">
                      {timeAgo(run.created_at)}
                    </span>
                  </TableCell>
                  <TableCell>
                    {run.phase ? (
                      <Badge
                        variant="outline"
                        className="text-xs text-[var(--cc-accent)] border-[var(--cc-accent-muted)]"
                      >
                        {run.phase}
                      </Badge>
                    ) : (
                      <span className="text-[var(--cc-text-muted)]">--</span>
                    )}
                  </TableCell>
                  <TableCell>
                    <SeverityBar finding_count={run.finding_count} />
                  </TableCell>
                  <TableCell>
                    <span className="text-sm font-medium text-[var(--cc-text)]">
                      {run.proposal_count || 0}
                    </span>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm font-mono text-[var(--cc-green)]">
                      {formatCost(run.total_cost)}
                    </span>
                  </TableCell>
                  <TableCell>
                    <div
                      className="flex items-center gap-1"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <button
                        onClick={() => router.push(`/debate/${run.id}`)}
                        className="p-1.5 rounded-md cursor-pointer hover:bg-[var(--cc-bg-hover)] transition-colors duration-200"
                        title="View debate"
                      >
                        <ExternalLink className="w-3.5 h-3.5 text-[var(--cc-text-muted)]" />
                      </button>
                      {run.status === "completed" && (
                        <button
                          onClick={() => router.push(`/rfc/${run.id}`)}
                          className="p-1.5 rounded-md cursor-pointer hover:bg-[var(--cc-bg-hover)] transition-colors duration-200"
                          title="View RFC"
                        >
                          <FileText className="w-3.5 h-3.5 text-[var(--cc-accent)]" />
                        </button>
                      )}
                      <button
                        onClick={(e) => handleDelete(run.id, e)}
                        disabled={deleting === run.id}
                        className="p-1.5 rounded-md cursor-pointer hover:bg-[var(--cc-red-muted)] transition-colors duration-200"
                        title="Delete"
                      >
                        {deleting === run.id ? (
                          <Loader2 className="w-3.5 h-3.5 animate-spin text-[var(--cc-text-muted)]" />
                        ) : (
                          <Trash2 className="w-3.5 h-3.5 text-[var(--cc-red)]" />
                        )}
                      </button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </div>

      {/* Agent Memory Cards */}
      <div>
        <h2 className="text-lg font-semibold mb-4 text-[var(--cc-text)] tracking-tight">
          Agent Memory
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {AGENT_ROLES.map((agent) => {
            const color = getAgentColor(agent);
            const agentRuns = runs.filter((r) => r.status === "completed");
            const Icon = AGENT_ICONS[agent] || Eye;
            return (
              <div
                key={agent}
                className="card-premium hover-lift overflow-hidden"
              >
                <div
                  className="h-1 w-full"
                  style={{ backgroundColor: color }}
                />
                <div className="p-4">
                  <div className="flex items-center gap-2 mb-3">
                    <div
                      className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
                      style={{ backgroundColor: `color-mix(in srgb, ${color} 18%, transparent)` }}
                    >
                      <Icon className="w-4 h-4" style={{ color }} />
                    </div>
                    <span className="text-sm font-semibold capitalize" style={{ color }}>
                      {agent}
                    </span>
                  </div>
                  <div className="space-y-2 text-xs">
                    <div className="flex justify-between">
                      <span className="text-[var(--cc-text-muted)]">Sessions</span>
                      <span className="text-[var(--cc-text)] font-mono font-medium">{agentRuns.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--cc-text-muted)]">Role</span>
                      <span className="font-medium" style={{ color }}>
                        {AGENT_DESCRIPTIONS[agent]}
                      </span>
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
