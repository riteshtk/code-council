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
} from "lucide-react";
import { cn, formatCost, timeAgo, getAgentColor } from "@/lib/utils";
import { toast } from "sonner";

const AGENT_ROLES = ["archaeologist", "skeptic", "visionary", "scribe"];

function StatusIcon({ status }: { status: string }) {
  if (status === "running") return <Loader2 className="w-4 h-4 animate-spin" style={{ color: "var(--cc-yellow)" }} />;
  if (status === "completed") return <CheckCircle2 className="w-4 h-4" style={{ color: "var(--cc-green)" }} />;
  if (status === "failed") return <XCircle className="w-4 h-4" style={{ color: "var(--cc-red)" }} />;
  return <Clock className="w-4 h-4" style={{ color: "var(--cc-text-muted)" }} />;
}

function SeverityBar({ finding_count }: { finding_count: number }) {
  if (finding_count === 0) return <span style={{ color: "var(--cc-text-muted)" }}>—</span>;
  return (
    <div className="flex items-center gap-1">
      <AlertTriangle className="w-3 h-3" style={{ color: "var(--cc-yellow)" }} />
      <span className="text-sm" style={{ color: "var(--cc-text)" }}>{finding_count}</span>
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
    <div className="flex-1 p-6 max-w-7xl mx-auto w-full space-y-6">
      <div>
        <h1 className="text-2xl font-bold" style={{ color: "var(--cc-text)" }}>
          Sessions
        </h1>
        <p className="text-sm" style={{ color: "var(--cc-text-muted)" }}>
          All analysis sessions and their results
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-6 gap-3">
        {[
          { label: "Total", value: stats.total, color: "var(--cc-text)", icon: BarChart3 },
          { label: "Running", value: stats.running, color: "var(--cc-yellow)", icon: Loader2 },
          { label: "Completed", value: stats.completed, color: "var(--cc-green)", icon: CheckCircle2 },
          { label: "Failed", value: stats.failed, color: "var(--cc-red)", icon: XCircle },
          { label: "Findings", value: stats.totalFindings, color: "var(--cc-yellow)", icon: AlertTriangle },
          { label: "Total Cost", value: formatCost(stats.totalCost), color: "var(--cc-green)", icon: null },
        ].map(({ label, value, color, icon: Icon }) => (
          <Card
            key={label}
            style={{ backgroundColor: "var(--cc-bg-card)", borderColor: "var(--cc-border)" }}
          >
            <CardContent className="p-3 text-center">
              {Icon && <Icon className="w-4 h-4 mx-auto mb-1" style={{ color }} />}
              <div className="text-xl font-bold" style={{ color }}>{value}</div>
              <div className="text-xs" style={{ color: "var(--cc-text-muted)" }}>{label}</div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4" style={{ color: "var(--cc-text-muted)" }} />
          <Input
            placeholder="Search sessions…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
              color: "var(--cc-text)",
            }}
          />
        </div>

        <Select value={statusFilter} onValueChange={(v) => v && setStatusFilter(v)}>
          <SelectTrigger
            className="w-36"
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
              color: "var(--cc-text)",
            }}
          >
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

        <Button
          variant="outline"
          size="sm"
          onClick={loadRuns}
          style={{ borderColor: "var(--cc-border)", color: "var(--cc-text)" }}
        >
          Refresh
        </Button>
      </div>

      {/* Table */}
      <Card style={{ backgroundColor: "var(--cc-bg-card)", borderColor: "var(--cc-border)" }}>
        <CardContent className="p-0">
          {loading ? (
            <div className="p-4 space-y-3">
              {[...Array(5)].map((_, i) => (
                <Skeleton key={i} className="h-12 w-full" />
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div
              className="py-12 text-center"
              style={{ color: "var(--cc-text-muted)" }}
            >
              <BarChart3 className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p>No sessions found</p>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow style={{ borderColor: "var(--cc-border)" }}>
                  {["Status", "Repository", "Created", "Phase", "Findings", "Proposals", "Cost", "Actions"].map((h) => (
                    <TableHead
                      key={h}
                      className="text-xs font-medium"
                      style={{ color: "var(--cc-text-muted)" }}
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
                    className="cursor-pointer hover:bg-white/5 transition-colors"
                    style={{ borderColor: "var(--cc-border)" }}
                    onClick={() => router.push(`/debate/${run.id}`)}
                  >
                    <TableCell>
                      <StatusIcon status={run.status} />
                    </TableCell>
                    <TableCell>
                      <div
                        className="text-sm font-medium max-w-xs truncate"
                        style={{ color: "var(--cc-text)" }}
                      >
                        {run.repo?.url || run.repo?.local_path || run.id}
                      </div>
                      <div
                        className="text-xs mt-0.5"
                        style={{
                          color: "var(--cc-text-muted)",
                          fontFamily: "var(--font-geist-mono)",
                        }}
                      >
                        {run.id.slice(0, 8)}…
                      </div>
                    </TableCell>
                    <TableCell>
                      <span className="text-xs" style={{ color: "var(--cc-text-muted)" }}>
                        {timeAgo(run.created_at)}
                      </span>
                    </TableCell>
                    <TableCell>
                      {run.phase ? (
                        <Badge
                          variant="outline"
                          className="text-xs"
                          style={{ color: "var(--cc-accent)", borderColor: "var(--cc-accent)44" }}
                        >
                          {run.phase}
                        </Badge>
                      ) : (
                        <span style={{ color: "var(--cc-text-muted)" }}>—</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <SeverityBar finding_count={run.finding_count} />
                    </TableCell>
                    <TableCell>
                      <span className="text-sm" style={{ color: "var(--cc-text)" }}>
                        {run.proposal_count || 0}
                      </span>
                    </TableCell>
                    <TableCell>
                      <span
                        className="text-sm"
                        style={{
                          color: "var(--cc-green)",
                          fontFamily: "var(--font-geist-mono)",
                        }}
                      >
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
                          className="p-1.5 rounded hover:bg-white/10 transition-colors"
                          title="View debate"
                        >
                          <ExternalLink className="w-3.5 h-3.5" style={{ color: "var(--cc-text-muted)" }} />
                        </button>
                        {run.status === "completed" && (
                          <button
                            onClick={() => router.push(`/rfc/${run.id}`)}
                            className="p-1.5 rounded hover:bg-white/10 transition-colors"
                            title="View RFC"
                          >
                            <FileText className="w-3.5 h-3.5" style={{ color: "var(--cc-accent)" }} />
                          </button>
                        )}
                        <button
                          onClick={(e) => handleDelete(run.id, e)}
                          disabled={deleting === run.id}
                          className="p-1.5 rounded hover:bg-white/10 transition-colors"
                          title="Delete"
                        >
                          {deleting === run.id ? (
                            <Loader2 className="w-3.5 h-3.5 animate-spin" style={{ color: "var(--cc-text-muted)" }} />
                          ) : (
                            <Trash2 className="w-3.5 h-3.5" style={{ color: "var(--cc-red)" }} />
                          )}
                        </button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Agent Memory Cards */}
      <div>
        <h2 className="text-lg font-semibold mb-3" style={{ color: "var(--cc-text)" }}>
          Agent Memory
        </h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {AGENT_ROLES.map((agent) => {
            const color = getAgentColor(agent);
            const agentRuns = runs.filter((r) =>
              r.status === "completed"
            );
            return (
              <Card
                key={agent}
                style={{
                  backgroundColor: "var(--cc-bg-card)",
                  borderColor: `${color}44`,
                }}
              >
                <CardHeader className="pb-2">
                  <CardTitle
                    className="text-sm flex items-center gap-2"
                    style={{ color }}
                  >
                    <div
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: color }}
                    />
                    {agent}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span style={{ color: "var(--cc-text-muted)" }}>Sessions</span>
                      <span style={{ color: "var(--cc-text)" }}>{agentRuns.length}</span>
                    </div>
                    <div className="flex justify-between">
                      <span style={{ color: "var(--cc-text-muted)" }}>Role</span>
                      <span style={{ color }}>
                        {agent === "archaeologist"
                          ? "Historian"
                          : agent === "skeptic"
                          ? "Devil's Advocate"
                          : agent === "visionary"
                          ? "Architect"
                          : "Scribe"}
                      </span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>
    </div>
  );
}
