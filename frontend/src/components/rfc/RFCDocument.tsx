"use client";

import type { RunDetail } from "@/lib/types";
import { VoteMatrix } from "./VoteMatrix";
import { DissentBlock } from "./DissentBlock";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "var(--cc-red)",
  high: "#ff9500",
  medium: "var(--cc-yellow)",
  low: "var(--cc-blue)",
  info: "var(--cc-text-muted)",
};

interface RFCDocumentProps {
  run: RunDetail;
  rfcData?: Record<string, unknown>;
}

export function RFCDocument({ run, rfcData }: RFCDocumentProps) {
  const title = (rfcData?.title as string) || `Security RFC — ${run.repo?.url || run.id}`;
  const summary = (rfcData?.summary as string) || "Automated security analysis by CodeCouncil multi-agent system.";
  const createdAt = new Date(run.created_at).toLocaleDateString("en-US", {
    year: "numeric",
    month: "long",
    day: "numeric",
  });

  return (
    <article
      className="max-w-none prose prose-invert"
      style={{ color: "var(--cc-text)" }}
    >
      {/* RFC Header */}
      <div className="mb-8 pb-6 border-b" style={{ borderColor: "var(--cc-border)" }}>
        <div className="flex items-center gap-2 mb-2">
          <Badge
            variant="outline"
            style={{ borderColor: "var(--cc-accent)44", color: "var(--cc-accent)" }}
          >
            RFC
          </Badge>
          <Badge
            variant="outline"
            style={{
              borderColor:
                run.status === "completed" ? "var(--cc-green)44" : "var(--cc-border)",
              color: run.status === "completed" ? "var(--cc-green)" : "var(--cc-text-muted)",
            }}
          >
            {run.status}
          </Badge>
        </div>
        <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--cc-text)" }}>
          {title}
        </h1>
        <div className="flex flex-wrap gap-4 text-sm" style={{ color: "var(--cc-text-muted)" }}>
          <span>Repository: <span style={{ color: "var(--cc-text)" }}>{run.repo?.url || run.repo?.local_path || "—"}</span></span>
          <span>Date: <span style={{ color: "var(--cc-text)" }}>{createdAt}</span></span>
          <span>Run: <code style={{ color: "var(--cc-blue)" }}>{run.id}</code></span>
        </div>
      </div>

      {/* Executive Summary */}
      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-3" style={{ color: "var(--cc-text)" }} id="summary">
          Executive Summary
        </h2>
        <p className="text-sm leading-relaxed" style={{ color: "var(--cc-text-muted)" }}>
          {summary}
        </p>

        {/* Stats grid */}
        <div className="grid grid-cols-4 gap-3 mt-4">
          {[
            { label: "Total Findings", value: run.findings.length, color: "var(--cc-text)" },
            { label: "Critical", value: run.findings.filter((f) => f.severity === "critical").length, color: "var(--cc-red)" },
            { label: "Proposals", value: run.proposals.length, color: "var(--cc-accent)" },
            { label: "Cost", value: `$${(run.total_cost || 0).toFixed(4)}`, color: "var(--cc-green)" },
          ].map(({ label, value, color }) => (
            <div
              key={label}
              className="rounded-lg p-3 text-center border"
              style={{ backgroundColor: "var(--cc-bg)", borderColor: "var(--cc-border)" }}
            >
              <div className="text-xl font-bold" style={{ color }}>{value}</div>
              <div className="text-xs" style={{ color: "var(--cc-text-muted)" }}>{label}</div>
            </div>
          ))}
        </div>
      </section>

      <Separator style={{ backgroundColor: "var(--cc-border)" }} className="my-6" />

      {/* Findings */}
      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-4" style={{ color: "var(--cc-text)" }} id="findings">
          Findings
        </h2>
        {run.findings.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--cc-text-muted)" }}>
            No findings recorded.
          </p>
        ) : (
          <div className="space-y-4">
            {(["critical", "high", "medium", "low", "info"] as const).map((sev) => {
              const sevFindings = run.findings.filter((f) => f.severity === sev);
              if (sevFindings.length === 0) return null;
              return (
                <div key={sev}>
                  <h3
                    className="text-sm font-medium mb-2 uppercase tracking-wide"
                    style={{ color: SEVERITY_COLORS[sev] }}
                  >
                    {sev} ({sevFindings.length})
                  </h3>
                  <div className="space-y-3">
                    {sevFindings.map((finding) => (
                      <div
                        key={finding.id}
                        className="rounded-lg p-4 border"
                        style={{
                          backgroundColor: "var(--cc-bg)",
                          borderColor: `${SEVERITY_COLORS[sev]}44`,
                          borderLeftWidth: 3,
                          borderLeftColor: SEVERITY_COLORS[sev],
                        }}
                      >
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <h4 className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>
                            {finding.title}
                          </h4>
                          {finding.file_path && (
                            <code
                              className="text-xs px-1.5 py-0.5 rounded shrink-0"
                              style={{
                                backgroundColor: "var(--cc-bg-card)",
                                color: "var(--cc-blue)",
                                fontFamily: "var(--font-geist-mono)",
                              }}
                            >
                              {finding.file_path}
                              {finding.line_start && `:${finding.line_start}`}
                            </code>
                          )}
                        </div>
                        <p className="text-xs leading-relaxed mb-2" style={{ color: "var(--cc-text-muted)" }}>
                          {finding.description}
                        </p>
                        {finding.code_snippet && (
                          <pre
                            className="text-xs p-3 rounded overflow-x-auto mb-2"
                            style={{
                              backgroundColor: "var(--cc-bg-card)",
                              color: "var(--cc-text)",
                              fontFamily: "var(--font-geist-mono)",
                              border: `1px solid var(--cc-border)`,
                            }}
                          >
                            {finding.code_snippet}
                          </pre>
                        )}
                        {finding.recommendation && (
                          <div
                            className="text-xs p-2 rounded"
                            style={{
                              backgroundColor: "var(--cc-accent)11",
                              color: "var(--cc-accent)",
                              border: `1px solid var(--cc-accent)33`,
                            }}
                          >
                            Recommendation: {finding.recommendation}
                          </div>
                        )}
                        {finding.tags && finding.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1 mt-2">
                            {finding.tags.map((tag) => (
                              <span
                                key={tag}
                                className="text-xs px-1.5 py-0.5 rounded"
                                style={{
                                  backgroundColor: "var(--cc-border)",
                                  color: "var(--cc-text-muted)",
                                }}
                              >
                                {tag}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      <Separator style={{ backgroundColor: "var(--cc-border)" }} className="my-6" />

      {/* Proposals */}
      <section className="mb-6">
        <h2 className="text-lg font-semibold mb-4" style={{ color: "var(--cc-text)" }} id="proposals">
          Proposals & Consensus
        </h2>
        {run.proposals.length === 0 ? (
          <p className="text-sm" style={{ color: "var(--cc-text-muted)" }}>
            No proposals recorded.
          </p>
        ) : (
          <div className="space-y-6">
            {run.proposals.map((proposal) => (
              <div
                key={proposal.id}
                className="rounded-lg border p-4"
                style={{
                  backgroundColor: "var(--cc-bg)",
                  borderColor:
                    proposal.status === "accepted"
                      ? "var(--cc-green)44"
                      : proposal.status === "rejected"
                      ? "var(--cc-red)44"
                      : "var(--cc-border)",
                }}
              >
                <div className="flex items-start justify-between gap-2 mb-3">
                  <h3 className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>
                    {proposal.title}
                  </h3>
                  <Badge
                    variant="outline"
                    style={{
                      borderColor:
                        proposal.status === "accepted"
                          ? "var(--cc-green)44"
                          : proposal.status === "rejected"
                          ? "var(--cc-red)44"
                          : "var(--cc-border)",
                      color:
                        proposal.status === "accepted"
                          ? "var(--cc-green)"
                          : proposal.status === "rejected"
                          ? "var(--cc-red)"
                          : "var(--cc-text-muted)",
                    }}
                  >
                    {proposal.status}
                  </Badge>
                </div>
                <p className="text-xs leading-relaxed mb-4" style={{ color: "var(--cc-text-muted)" }}>
                  {proposal.description}
                </p>

                {proposal.votes && proposal.votes.length > 0 && (
                  <>
                    <div className="mb-3">
                      <h4 className="text-xs font-medium mb-2" style={{ color: "var(--cc-text-muted)" }}>
                        Vote Matrix
                      </h4>
                      <VoteMatrix votes={proposal.votes} />
                    </div>
                    <DissentBlock
                      votes={proposal.votes}
                      proposalTitle={proposal.title}
                    />
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </section>

      <Separator style={{ backgroundColor: "var(--cc-border)" }} className="my-6" />

      {/* Cost */}
      {run.cost && (
        <section className="mb-6">
          <h2 className="text-lg font-semibold mb-4" style={{ color: "var(--cc-text)" }} id="cost">
            Cost Report
          </h2>
          <div className="grid grid-cols-2 gap-4">
            <div
              className="rounded-lg p-4 border space-y-2"
              style={{ backgroundColor: "var(--cc-bg)", borderColor: "var(--cc-border)" }}
            >
              <div className="flex justify-between text-sm">
                <span style={{ color: "var(--cc-text-muted)" }}>Total Cost</span>
                <span style={{ color: "var(--cc-green)", fontFamily: "var(--font-geist-mono)" }}>
                  ${run.cost.total_cost.toFixed(6)}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span style={{ color: "var(--cc-text-muted)" }}>Total Tokens</span>
                <span style={{ color: "var(--cc-text)", fontFamily: "var(--font-geist-mono)" }}>
                  {run.cost.total_tokens.toLocaleString()}
                </span>
              </div>
            </div>
            {Object.keys(run.cost.by_agent || {}).length > 0 && (
              <div
                className="rounded-lg p-4 border space-y-2"
                style={{ backgroundColor: "var(--cc-bg)", borderColor: "var(--cc-border)" }}
              >
                <h4 className="text-xs font-medium mb-2" style={{ color: "var(--cc-text-muted)" }}>
                  By Agent
                </h4>
                {Object.entries(run.cost.by_agent).map(([agent, cost]) => (
                  <div key={agent} className="flex justify-between text-xs">
                    <span style={{ color: "var(--cc-text-muted)" }}>{agent}</span>
                    <span style={{ color: "var(--cc-green)", fontFamily: "var(--font-geist-mono)" }}>
                      ${(cost as number).toFixed(6)}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        </section>
      )}
    </article>
  );
}
