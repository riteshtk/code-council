"use client";

import { useState, useEffect, useMemo } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { listRuns, deleteRun, clearAgentMemory, getRFC } from "@/lib/api";
import type { RunSummary } from "@/lib/types";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Search,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  BarChart3,
  ChevronRight,
  X,
  GitCompare,
} from "lucide-react";
import { cn, formatCost, timeAgo } from "@/lib/utils";
import { toast } from "sonner";
import { AGENTS, AGENT_HANDLES } from "@/lib/constants";

const AGENTS_LIST = AGENT_HANDLES.map((h) => AGENTS[h]);

/* --- Status pill --- */
function StatusPill({ status }: { status: string }) {
  const map: Record<string, { color: string; bg: string; icon: React.ReactNode }> = {
    running:   { color: "var(--cc-accent)", bg: "var(--cc-accent-muted)", icon: <Loader2 className="w-3 h-3 animate-spin" /> },
    completed: { color: "var(--cc-green)",  bg: "var(--cc-green-muted)",  icon: <CheckCircle2 className="w-3 h-3" /> },
    failed:    { color: "var(--cc-red)",    bg: "var(--cc-red-muted)",    icon: <XCircle className="w-3 h-3" /> },
    pending:   { color: "var(--cc-text-muted)", bg: "var(--cc-bg-hover)", icon: <Clock className="w-3 h-3" /> },
  };
  const s = map[status] || map.pending;
  return (
    <span
      className="inline-flex items-center gap-1 text-[10px] font-semibold px-2.5 py-1 rounded-full uppercase tracking-wide"
      style={{ color: s.color, backgroundColor: s.bg }}
    >
      {s.icon} {status}
    </span>
  );
}

const ITEMS_PER_PAGE = 10;

/* --- Main page --- */
export default function SessionsPage() {
  const router = useRouter();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [topologyFilter, setTopologyFilter] = useState("all");
  const [sortBy, setSortBy] = useState("newest");
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [page, setPage] = useState(1);
  const [deleting, setDeleting] = useState<string | null>(null);
  const [comparing, setComparing] = useState(false);
  const [compareData, setCompareData] = useState<{ left: { run: RunSummary; rfc: string }; right: { run: RunSummary; rfc: string } } | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);

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

  async function handleCompare() {
    const ids = [...selected];
    if (ids.length !== 2) {
      toast.error("Select exactly 2 sessions to compare");
      return;
    }
    setCompareLoading(true);
    try {
      const [rfc1, rfc2] = await Promise.all([
        getRFC(ids[0], "markdown").then((r) => typeof r === "string" ? r : JSON.stringify(r, null, 2)),
        getRFC(ids[1], "markdown").then((r) => typeof r === "string" ? r : JSON.stringify(r, null, 2)),
      ]);
      const run1 = runs.find((r) => r.id === ids[0])!;
      const run2 = runs.find((r) => r.id === ids[1])!;
      setCompareData({
        left: { run: run1, rfc: rfc1 as string },
        right: { run: run2, rfc: rfc2 as string },
      });
      setComparing(true);
    } catch (e) {
      toast.error(`Failed to load RFCs for comparison: ${e}`);
    } finally {
      setCompareLoading(false);
    }
  }

  async function handleDelete(runId: string, e: React.MouseEvent) {
    e.stopPropagation();
    setDeleting(runId);
    try {
      await deleteRun(runId);
      setRuns((prev) => prev.filter((r) => r.id !== runId));
      setSelected((prev) => { const n = new Set(prev); n.delete(runId); return n; });
      toast.success("Session deleted");
    } catch {
      toast.error("Failed to delete session");
    } finally {
      setDeleting(null);
    }
  }

  function toggleSelect(runId: string) {
    setSelected((prev) => {
      const n = new Set(prev);
      if (n.has(runId)) n.delete(runId);
      else n.add(runId);
      return n;
    });
  }

  const filtered = useMemo(() => {
    let result = runs.filter((r) => {
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

    // Sort
    if (sortBy === "oldest") result = [...result].reverse();
    if (sortBy === "cost") result = [...result].sort((a, b) => b.total_cost - a.total_cost);

    return result;
  }, [runs, search, statusFilter, topologyFilter, sortBy]);

  const totalPages = Math.max(1, Math.ceil(filtered.length / ITEMS_PER_PAGE));
  const paginated = filtered.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE);

  // Derive repo display
  function repoDisplay(run: RunSummary) {
    const url = run.repo?.url || run.repo?.local_path || run.id;
    const match = url.match(/github\.com\/([^/]+)\/([^/]+)/);
    if (match) return { org: match[1] + "/", name: match[2], initial: match[2][0]?.toUpperCase() || "?" };
    const parts = url.split("/");
    const last = parts[parts.length - 1] || url;
    return { org: "", name: last, initial: last[0]?.toUpperCase() || "?" };
  }

  const completedRuns = runs.filter((r) => r.status === "completed").length;

  function formatDuration(start?: string, end?: string): string {
    if (!start || !end) return "--";
    const ms = new Date(end).getTime() - new Date(start).getTime();
    if (ms < 0) return "--";
    const secs = Math.floor(ms / 1000);
    const mins = Math.floor(secs / 60);
    const remainSecs = secs % 60;
    return `${mins}m ${remainSecs}s`;
  }

  return (
    <div className="flex-1 px-8 lg:px-12 py-8 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-[var(--cc-text)]">Council Sessions</h1>
        <button
          disabled={selected.size !== 2 || compareLoading}
          onClick={handleCompare}
          className="py-2 px-4 bg-[var(--cc-bg-card)] border border-[var(--cc-accent)] rounded-lg text-[var(--cc-accent)] text-[13px] font-semibold cursor-pointer hover:bg-[var(--cc-accent-muted)] transition-colors duration-200"
        >
          Compare Selected ({selected.size})
        </button>
      </div>

      {/* Filter bar */}
      <div className="flex gap-3 mb-5 items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--cc-text-muted)]" />
          <input
            placeholder="Search by repository name..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
            className="w-full py-2.5 pl-9 pr-4 bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-lg text-[13px] text-[var(--cc-text)] placeholder:text-[var(--cc-text-muted)] outline-none focus:border-[var(--cc-accent)] transition-all duration-200"
          />
        </div>
        <select
          value={statusFilter}
          onChange={(e) => { setStatusFilter(e.target.value); setPage(1); }}
          className="py-2.5 px-3.5 bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-lg text-[13px] text-[var(--cc-text)] outline-none cursor-pointer"
        >
          <option value="all">All Statuses</option>
          <option value="completed">Completed</option>
          <option value="running">Running</option>
          <option value="failed">Failed</option>
        </select>
        <select
          value={topologyFilter}
          onChange={(e) => { setTopologyFilter(e.target.value); setPage(1); }}
          className="py-2.5 px-3.5 bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-lg text-[13px] text-[var(--cc-text)] outline-none cursor-pointer"
        >
          <option value="all">All Topologies</option>
          <option value="adversarial">Adversarial</option>
          <option value="collaborative">Collaborative</option>
          <option value="socratic">Socratic</option>
        </select>
        <select
          value={sortBy}
          onChange={(e) => setSortBy(e.target.value)}
          className="py-2.5 px-3.5 bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-lg text-[13px] text-[var(--cc-text)] outline-none cursor-pointer"
        >
          <option value="newest">Newest First</option>
          <option value="oldest">Oldest First</option>
          <option value="cost">Most Expensive</option>
        </select>
      </div>

      {/* Sessions Table */}
      {loading ? (
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-14 w-full rounded-lg" />
          ))}
        </div>
      ) : filtered.length === 0 ? (
        <div className="card-premium py-20 text-center">
          <div className="flex justify-center gap-2 mb-5">
            {AGENTS_LIST.map(({ abbr, color }) => (
              <div
                key={abbr}
                className="w-10 h-10 rounded-lg flex items-center justify-center text-xs font-bold text-white opacity-50"
                style={{ backgroundColor: color }}
              >
                {abbr}
              </div>
            ))}
          </div>
          <BarChart3 className="w-12 h-12 mx-auto mb-4 text-[var(--cc-text-muted)] opacity-30" />
          <p className="text-lg font-semibold text-[var(--cc-text)] mb-1">
            {search || statusFilter !== "all" ? "No sessions match your filters" : "No council sessions yet"}
          </p>
          <p className="text-sm text-[var(--cc-text-muted)] mt-1 opacity-60">
            {search || statusFilter !== "all" ? "Try adjusting your filters" : "Start your first analysis from the home page to see sessions here."}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr>
                <th className="w-[30px] text-left py-2.5 px-3.5 text-[11px] uppercase tracking-wide text-[var(--cc-text-muted)] border-b border-[var(--cc-border)]" />
                <th className="text-left py-2.5 px-3.5 text-[11px] uppercase tracking-wide text-[var(--cc-text-muted)] border-b border-[var(--cc-border)]">Repository</th>
                <th className="text-left py-2.5 px-3.5 text-[11px] uppercase tracking-wide text-[var(--cc-text-muted)] border-b border-[var(--cc-border)]">Date</th>
                <th className="text-left py-2.5 px-3.5 text-[11px] uppercase tracking-wide text-[var(--cc-text-muted)] border-b border-[var(--cc-border)]">Agents</th>
                <th className="text-left py-2.5 px-3.5 text-[11px] uppercase tracking-wide text-[var(--cc-text-muted)] border-b border-[var(--cc-border)]">Topology</th>
                <th className="text-left py-2.5 px-3.5 text-[11px] uppercase tracking-wide text-[var(--cc-text-muted)] border-b border-[var(--cc-border)]">Consensus</th>
                <th className="text-left py-2.5 px-3.5 text-[11px] uppercase tracking-wide text-[var(--cc-text-muted)] border-b border-[var(--cc-border)]">Cost</th>
                <th className="text-left py-2.5 px-3.5 text-[11px] uppercase tracking-wide text-[var(--cc-text-muted)] border-b border-[var(--cc-border)]">Duration</th>
                <th className="text-left py-2.5 px-3.5 text-[11px] uppercase tracking-wide text-[var(--cc-text-muted)] border-b border-[var(--cc-border)]">Status</th>
                <th className="text-left py-2.5 px-3.5 text-[11px] uppercase tracking-wide text-[var(--cc-text-muted)] border-b border-[var(--cc-border)]">RFC</th>
              </tr>
            </thead>
            <tbody>
              {paginated.map((run) => {
                const rd = repoDisplay(run);
                const consensus = run.consensus_score || 0;
                const consensusColor = consensus >= 75 ? "var(--cc-green)" : consensus >= 50 ? "var(--cc-yellow)" : "var(--cc-red)";

                return (
                  <tr
                    key={run.id}
                    className="cursor-pointer hover:bg-[var(--cc-bg-hover)] transition-colors duration-200 border-b border-[var(--cc-border)]"
                    onClick={() => router.push(`/debate/${run.id}`)}
                  >
                    <td className="py-3.5 px-3.5" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selected.has(run.id)}
                        onChange={() => toggleSelect(run.id)}
                        className="w-[18px] h-[18px] accent-[var(--cc-accent)] cursor-pointer"
                      />
                    </td>
                    <td className="py-3.5 px-3.5">
                      <div className="flex items-center gap-2.5">
                        <div className="w-8 h-8 rounded-lg bg-[var(--cc-bg-card)] border border-[var(--cc-border)] flex items-center justify-center text-sm font-medium text-[var(--cc-text)]">
                          {rd.initial}
                        </div>
                        <div className="text-sm font-semibold text-[var(--cc-text)]">
                          <span className="text-[var(--cc-text-muted)] font-normal">{rd.org}</span>{rd.name}
                        </div>
                      </div>
                    </td>
                    <td className="py-3.5 px-3.5 text-[var(--cc-text-muted)] text-[13px]">
                      {timeAgo(run.created_at)}
                    </td>
                    <td className="py-3.5 px-3.5">
                      <div className="flex">
                        {AGENTS_LIST.map(({ abbr, color }, i) => (
                          <div
                            key={abbr}
                            className="w-6 h-6 rounded-md flex items-center justify-center text-[9px] font-bold text-white border-2 border-[var(--cc-bg)]"
                            style={{
                              backgroundColor: color,
                              marginLeft: i > 0 ? "-4px" : "0",
                            }}
                          >
                            {abbr}
                          </div>
                        ))}
                      </div>
                    </td>
                    <td className="py-3.5 px-3.5 text-xs text-[var(--cc-text-muted)]">
                      Adversarial
                    </td>
                    <td className="py-3.5 px-3.5">
                      <div className="flex items-center gap-2">
                        <div className="w-[60px] h-1.5 bg-[var(--cc-border)] rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full"
                            style={{
                              width: `${run.status === "completed" ? consensus : 0}%`,
                              backgroundColor: run.status === "completed" ? consensusColor : "transparent",
                            }}
                          />
                        </div>
                        <span className="text-[13px] font-semibold text-[var(--cc-text)]">
                          {run.status === "completed" ? `${consensus}%` : "\u2014"}
                        </span>
                      </div>
                    </td>
                    <td className="py-3.5 px-3.5 font-mono text-[13px] text-[var(--cc-text-muted)]">
                      {formatCost(run.total_cost)}
                    </td>
                    <td className="py-3.5 px-3.5 font-mono text-[12px] text-[var(--cc-text-muted)]">
                      {run.status === "completed" ? formatDuration(run.created_at, run.updated_at) : "\u2014"}
                    </td>
                    <td className="py-3.5 px-3.5">
                      <StatusPill status={run.status} />
                    </td>
                    <td className="py-3.5 px-3.5" onClick={(e) => e.stopPropagation()}>
                      {run.status === "completed" ? (
                        <a
                          href={`/rfc/${run.id}`}
                          className="text-[var(--cc-accent)] text-xs font-semibold hover:underline"
                          onClick={(e) => { e.preventDefault(); router.push(`/rfc/${run.id}`); }}
                        >
                          View RFC
                        </a>
                      ) : (
                        <span className="text-[var(--cc-text-muted)] text-xs">{"\u2014"}</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex justify-center gap-1 mt-6">
          {Array.from({ length: totalPages }, (_, i) => i + 1).map((p) => (
            <button
              key={p}
              onClick={() => setPage(p)}
              className={cn(
                "w-8 h-8 flex items-center justify-center rounded-md text-xs font-medium cursor-pointer transition-all duration-200 border",
                p === page
                  ? "bg-[var(--cc-accent)] border-[var(--cc-accent)] text-white"
                  : "bg-[var(--cc-bg-card)] border-[var(--cc-border)] text-[var(--cc-text-muted)] hover:bg-[var(--cc-bg-hover)]"
              )}
            >
              {p}
            </button>
          ))}
          {page < totalPages && (
            <button
              onClick={() => setPage(page + 1)}
              className="w-8 h-8 flex items-center justify-center rounded-md text-xs bg-[var(--cc-bg-card)] border border-[var(--cc-border)] text-[var(--cc-text-muted)] hover:bg-[var(--cc-bg-hover)] cursor-pointer transition-all duration-200"
            >
              <ChevronRight className="w-3 h-3" />
            </button>
          )}
        </div>
      )}

      {/* Agent Memory Section */}
      <div className="mt-10">
        <h2 className="text-lg font-bold text-[var(--cc-text)] mb-4">Agent Memory</h2>
        <div className="grid grid-cols-4 gap-3">
          {AGENTS_LIST.map(({ handle, name: label, abbr, shortRole: role, icon: Icon, color }) => {
            const sessionCount = completedRuns;
            return (
              <div key={handle} className="bg-[var(--cc-bg-card)] border border-[var(--cc-border)] rounded-[10px] p-4">
                {/* Header */}
                <div className="flex items-center gap-2.5 mb-3">
                  <div
                    className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold text-white shrink-0"
                    style={{ backgroundColor: color }}
                  >
                    {abbr}
                  </div>
                  <div>
                    <div className="text-[13px] font-semibold text-[var(--cc-text)]">{label}</div>
                    <div className="text-[11px] text-[var(--cc-text-muted)]">{sessionCount} sessions</div>
                  </div>
                </div>

                {/* Memory items */}
                <div className="text-xs leading-relaxed text-[var(--cc-text-muted)]">
                  <div className="py-1.5 border-b border-[var(--cc-border)]">
                    {sessionCount > 0 ? "Memory data from previous sessions" : "No memory data yet"}
                  </div>
                  {sessionCount > 0 && (
                    <div className="py-1.5">
                      Pattern recognition active across {sessionCount} sessions
                    </div>
                  )}
                </div>

                <button
                  onClick={async () => {
                    try {
                      await clearAgentMemory(handle);
                      toast.success(`${label} memory cleared`);
                    } catch (e) {
                      toast.error(`Failed to clear ${label} memory: ${e}`);
                    }
                  }}
                  className="mt-2 py-1 px-2.5 bg-transparent border border-[var(--cc-border)] rounded text-[11px] text-[var(--cc-text-muted)] cursor-pointer hover:border-[var(--cc-red)] hover:text-[var(--cc-red)] transition-all duration-200"
                >
                  Clear Memory
                </button>
              </div>
            );
          })}
        </div>
      </div>

      {/* ═══ Compare Modal ═══ */}
      {comparing && compareData && (
        <div className="fixed inset-0 z-50 flex items-start justify-center pt-8 pb-8">
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setComparing(false)}
          />

          {/* Modal */}
          <div className="relative w-[95vw] max-h-[90vh] bg-[var(--cc-bg)] border border-[var(--cc-border)] rounded-2xl shadow-2xl overflow-hidden flex flex-col animate-fade-in">
            {/* Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--cc-border)] shrink-0">
              <div className="flex items-center gap-3">
                <GitCompare className="w-5 h-5 text-[var(--cc-accent)]" />
                <h2 className="text-lg font-bold text-[var(--cc-text)]">RFC Comparison</h2>
              </div>
              <button
                onClick={() => setComparing(false)}
                className="p-2 rounded-lg hover:bg-[var(--cc-bg-hover)] transition-colors cursor-pointer"
              >
                <X className="w-5 h-5 text-[var(--cc-text-muted)]" />
              </button>
            </div>

            {/* Side-by-side content */}
            <div className="flex-1 overflow-hidden grid grid-cols-2 divide-x divide-[var(--cc-border)]">
              {/* Left RFC */}
              <div className="flex flex-col overflow-hidden">
                <div className="px-4 py-3 border-b border-[var(--cc-border)] bg-[var(--cc-bg-card)] shrink-0">
                  <div className="text-sm font-semibold text-[var(--cc-text)]">
                    {compareData.left.run.repo?.url?.split("/").slice(-1)[0] || "Run A"}
                  </div>
                  <div className="text-xs text-[var(--cc-text-muted)]">
                    {timeAgo(compareData.left.run.created_at)} · {formatCost(compareData.left.run.total_cost)} · {compareData.left.run.finding_count} findings
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto p-6 prose-agent text-sm">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {compareData.left.rfc}
                  </ReactMarkdown>
                </div>
              </div>

              {/* Right RFC */}
              <div className="flex flex-col overflow-hidden">
                <div className="px-4 py-3 border-b border-[var(--cc-border)] bg-[var(--cc-bg-card)] shrink-0">
                  <div className="text-sm font-semibold text-[var(--cc-text)]">
                    {compareData.right.run.repo?.url?.split("/").slice(-1)[0] || "Run B"}
                  </div>
                  <div className="text-xs text-[var(--cc-text-muted)]">
                    {timeAgo(compareData.right.run.created_at)} · {formatCost(compareData.right.run.total_cost)} · {compareData.right.run.finding_count} findings
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto p-6 prose-agent text-sm">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {compareData.right.rfc}
                  </ReactMarkdown>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
