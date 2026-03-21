"use client";

import { useState, useEffect, useMemo } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getRun, getRFC, rerunAnalysis } from "@/lib/api";
import type { RunDetail } from "@/lib/types";
import { RFCDocument } from "@/components/rfc/RFCDocument";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "sonner";

const SECTIONS = [
  { id: "header", label: "Header" },
  { id: "summary", label: "Executive Summary" },
  { id: "findings", label: "Critical Findings" },
  { id: "proposals", label: "Proposals & Votes" },
  { id: "deadlocked", label: "Deadlocked Items" },
  { id: "actions", label: "Action Items" },
  { id: "cost", label: "Cost Summary" },
  { id: "appendix", label: "Debate Appendix" },
];

function downloadFile(content: string, filename: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export default function RFCPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const router = useRouter();

  const [run, setRun] = useState<RunDetail | null>(null);
  const [rfcData, setRfcData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState("header");
  const [viewMode, setViewMode] = useState<"document" | "structured">("document");

  const hasMarkdown = Boolean(rfcData?.rfc_content);

  useEffect(() => {
    if (!runId) return;
    Promise.all([
      getRun(runId),
      getRFC(runId, "json").catch(() => null),
    ])
      .then(([r, rfc]) => {
        setRun(r as RunDetail);
        setRfcData(rfc as Record<string, unknown> | null);
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, [runId]);

  function handleExportMD() {
    if (!rfcData?.rfc_content) {
      toast.error("No markdown content available");
      return;
    }
    downloadFile(
      rfcData.rfc_content as string,
      `rfc-${runId}.md`,
      "text/markdown"
    );
    toast.success("Exported as MD");
  }

  function handleExportJSON() {
    if (!rfcData) {
      toast.error("No RFC data available");
      return;
    }
    downloadFile(
      JSON.stringify(rfcData, null, 2),
      `rfc-${runId}.json`,
      "application/json"
    );
    toast.success("Exported as JSON");
  }

  async function handleExportHTML() {
    try {
      const data = await getRFC(runId, "html");
      const content =
        typeof data === "string" ? data : JSON.stringify(data, null, 2);
      downloadFile(content, `rfc-${runId}.html`, "text/html");
      toast.success("Exported as HTML");
    } catch (e) {
      toast.error(`Export failed: ${e}`);
    }
  }

  function scrollToSection(id: string) {
    setActiveSection(id);
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  }

  // Proposal sub-sections for sidebar
  const proposalLinks = useMemo(() => {
    if (!run) return [];
    return run.proposals.map((p) => ({
      id: `proposal-${p.id}`,
      label: p.title.length > 25 ? p.title.slice(0, 25) + "..." : p.title,
    }));
  }, [run]);

  if (loading) {
    return (
      <div className="flex-1 p-6 space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (error || !run) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center gap-4">
        <p style={{ color: "var(--cc-red)" }}>{error || "Run not found"}</p>
        <button
          onClick={() => router.back()}
          className="px-4 py-2 rounded-lg border text-sm transition-all duration-200"
          style={{
            borderColor: "var(--cc-border)",
            color: "var(--cc-text)",
            backgroundColor: "var(--cc-bg-card)",
          }}
        >
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden" style={{ backgroundColor: "var(--cc-bg)" }}>
      {/* TOP BAR */}
      <div
        className="flex items-center justify-between px-6 py-3 border-b shrink-0"
        style={{
          borderColor: "var(--cc-border)",
          backgroundColor: "rgba(8,8,13,0.95)",
        }}
      >
        {/* Left: breadcrumb */}
        <div className="flex items-center gap-4">
          <div className="text-[13px]" style={{ color: "var(--cc-text-muted)" }}>
            <Link href="/sessions" className="hover:underline" style={{ color: "var(--cc-text-muted)" }}>
              Sessions
            </Link>
            {" / "}
            <Link href={`/debate/${runId}`} className="hover:underline" style={{ color: "var(--cc-text-muted)" }}>
              {run.repo?.url || runId}
            </Link>
            {" / "}
            <span style={{ color: "var(--cc-text)" }}>RFC</span>
          </div>
        </div>
        {/* Right: view toggle + export buttons */}
        <div className="flex gap-2">
          {/* View toggle (only show when markdown is available) */}
          {hasMarkdown && (
            <div
              className="flex rounded-md border overflow-hidden"
              style={{ borderColor: "var(--cc-border)" }}
            >
              <button
                onClick={() => setViewMode("document")}
                className="px-3 py-1.5 text-xs font-semibold cursor-pointer transition-all duration-200"
                style={{
                  backgroundColor: viewMode === "document" ? "var(--cc-accent)" : "var(--cc-bg-card)",
                  color: viewMode === "document" ? "#fff" : "var(--cc-text-muted)",
                }}
              >
                Document View
              </button>
              <button
                onClick={() => setViewMode("structured")}
                className="px-3 py-1.5 text-xs font-semibold cursor-pointer transition-all duration-200"
                style={{
                  backgroundColor: viewMode === "structured" ? "var(--cc-accent)" : "var(--cc-bg-card)",
                  color: viewMode === "structured" ? "#fff" : "var(--cc-text-muted)",
                }}
              >
                Structured View
              </button>
            </div>
          )}
          <button
            onClick={handleExportMD}
            className="px-3.5 py-1.5 rounded-md text-xs font-semibold border cursor-pointer transition-all duration-200"
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
              color: "var(--cc-text-muted)",
            }}
          >
            Export MD
          </button>
          <button
            onClick={handleExportJSON}
            className="px-3.5 py-1.5 rounded-md text-xs font-semibold border cursor-pointer transition-all duration-200"
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
              color: "var(--cc-text-muted)",
            }}
          >
            Export JSON
          </button>
          <button
            onClick={handleExportHTML}
            className="px-3.5 py-1.5 rounded-md text-xs font-semibold border cursor-pointer transition-all duration-200"
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
              color: "var(--cc-text-muted)",
            }}
          >
            Export HTML
          </button>
          <button
            onClick={() => {
              window.print();
            }}
            className="px-3.5 py-1.5 rounded-md text-xs font-semibold border cursor-pointer transition-all duration-200 no-print"
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
              color: "var(--cc-text-muted)",
            }}
          >
            Print / PDF
          </button>
          <button
            onClick={() => {
              navigator.clipboard.writeText(window.location.href);
              toast.success("Link copied to clipboard");
            }}
            className="px-3.5 py-1.5 rounded-md text-xs font-semibold border cursor-pointer transition-all duration-200 no-print"
            style={{
              backgroundColor: "var(--cc-bg-card)",
              borderColor: "var(--cc-border)",
              color: "var(--cc-text-muted)",
            }}
          >
            Share Link
          </button>
          <button
            onClick={async () => {
              try {
                const result = await rerunAnalysis(runId) as { id?: string };
                const newRunId = result?.id || runId;
                toast.success("Re-analysis started!");
                router.push(`/debate/${newRunId}`);
              } catch (e) {
                toast.error(`Re-analyse failed: ${e}`);
              }
            }}
            className="px-3.5 py-1.5 rounded-md text-xs font-semibold text-white cursor-pointer transition-all duration-200 no-print"
            style={{ backgroundColor: "var(--cc-accent)" }}
          >
            Re-analyse
          </button>
        </div>
      </div>

      {/* MAIN LAYOUT: Sidebar + Content */}
      <div
        className="flex-1 min-h-0"
        style={{
          display: "grid",
          gridTemplateColumns: viewMode === "document" && hasMarkdown ? "1fr" : "220px 1fr",
        }}
      >
        {/* SIDEBAR (only in structured view or when no markdown) */}
        {(viewMode === "structured" || !hasMarkdown) && (
          <aside
            className="border-r overflow-y-auto sticky top-0"
            style={{
              borderColor: "var(--cc-border)",
              padding: "20px 16px",
              height: "calc(100vh - 56px - 49px)",
            }}
          >
            <h4
              className="text-[11px] uppercase tracking-widest mb-3"
              style={{ color: "var(--cc-text-muted)" }}
            >
              Sections
            </h4>
            <nav className="space-y-0.5">
              {SECTIONS.map((s) => (
                <button
                  key={s.id}
                  onClick={() => scrollToSection(s.id)}
                  className={`block w-full text-left px-3 py-1.5 rounded-md text-[13px] cursor-pointer transition-all duration-200 ${
                    activeSection === s.id
                      ? "font-semibold"
                      : ""
                  }`}
                  style={{
                    backgroundColor: activeSection === s.id
                      ? "rgba(108,92,231,0.1)"
                      : "transparent",
                    color: activeSection === s.id
                      ? "var(--cc-accent)"
                      : "var(--cc-text-muted)",
                    borderLeft: activeSection === s.id
                      ? "2px solid var(--cc-accent)"
                      : "2px solid transparent",
                  }}
                >
                  {s.label}
                </button>
              ))}
              {/* Proposal sub-links */}
              {proposalLinks.map((pl) => (
                <button
                  key={pl.id}
                  onClick={() => scrollToSection(pl.id)}
                  className="block w-full text-left pl-7 pr-3 py-1.5 rounded-md text-[13px] cursor-pointer transition-all duration-200"
                  style={{ color: "var(--cc-text-muted)" }}
                >
                  {pl.label}
                </button>
              ))}
            </nav>
          </aside>
        )}

        {/* CONTENT */}
        <div className="overflow-y-auto">
          <div
            className="mx-auto"
            style={{
              maxWidth: "860px",
              padding: "40px 48px 80px",
            }}
          >
            {/* Document View: render markdown RFC */}
            {viewMode === "document" && hasMarkdown ? (
              <article className="prose-agent">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                  {rfcData!.rfc_content as string}
                </ReactMarkdown>
              </article>
            ) : (
              /* Structured View: cards-based fallback */
              <RFCDocument run={run} rfcData={rfcData ?? undefined} />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
