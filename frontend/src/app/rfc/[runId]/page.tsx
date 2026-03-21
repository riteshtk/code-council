"use client";

import { useState, useEffect } from "react";
import { useParams, useRouter } from "next/navigation";
import { getRun, getRFC } from "@/lib/api";
import type { RunDetail } from "@/lib/types";
import { RFCDocument } from "@/components/rfc/RFCDocument";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Download, FileText, Code, ArrowLeft } from "lucide-react";
import { toast } from "sonner";

const SECTIONS = [
  { id: "summary", label: "Summary" },
  { id: "findings", label: "Findings" },
  { id: "proposals", label: "Proposals" },
  { id: "cost", label: "Cost" },
];

export default function RFCPage() {
  const params = useParams<{ runId: string }>();
  const runId = params.runId;
  const router = useRouter();

  const [run, setRun] = useState<RunDetail | null>(null);
  const [rfcData, setRfcData] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  async function handleExport(format: "json" | "markdown" | "html") {
    try {
      const data = await getRFC(runId, format);
      const content =
        typeof data === "string" ? data : JSON.stringify(data, null, 2);
      const blob = new Blob([content], {
        type: format === "json" ? "application/json" : "text/plain",
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `rfc-${runId}.${format === "markdown" ? "md" : format}`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success(`Exported as ${format.toUpperCase()}`);
    } catch (e) {
      toast.error(`Export failed: ${e}`);
    }
  }

  function scrollToSection(id: string) {
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth" });
  }

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
        <Button onClick={() => router.back()} variant="outline">
          Go Back
        </Button>
      </div>
    );
  }

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Sticky sidebar */}
      <aside
        className="w-48 flex-shrink-0 border-r p-4 flex flex-col gap-4"
        style={{
          backgroundColor: "var(--cc-bg-card)",
          borderColor: "var(--cc-border)",
        }}
      >
        <button
          onClick={() => router.push(`/debate/${runId}`)}
          className="flex items-center gap-2 text-xs hover:opacity-80 transition-opacity"
          style={{ color: "var(--cc-text-muted)" }}
        >
          <ArrowLeft className="w-3 h-3" />
          Back to Debate
        </button>

        <div>
          <div
            className="text-xs font-medium mb-2 uppercase tracking-wide"
            style={{ color: "var(--cc-text-muted)" }}
          >
            Sections
          </div>
          <nav className="space-y-1">
            {SECTIONS.map((s) => (
              <button
                key={s.id}
                onClick={() => scrollToSection(s.id)}
                className="block w-full text-left text-xs px-2 py-1.5 rounded hover:bg-white/5 transition-colors"
                style={{ color: "var(--cc-text)" }}
              >
                {s.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="mt-auto space-y-2">
          <div
            className="text-xs font-medium mb-2 uppercase tracking-wide"
            style={{ color: "var(--cc-text-muted)" }}
          >
            Export
          </div>
          <Button
            size="sm"
            variant="outline"
            className="w-full text-xs"
            onClick={() => handleExport("markdown")}
            style={{ borderColor: "var(--cc-border)", color: "var(--cc-text)" }}
          >
            <FileText className="w-3 h-3 mr-1" />
            Markdown
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="w-full text-xs"
            onClick={() => handleExport("json")}
            style={{ borderColor: "var(--cc-border)", color: "var(--cc-text)" }}
          >
            <Code className="w-3 h-3 mr-1" />
            JSON
          </Button>
          <Button
            size="sm"
            variant="outline"
            className="w-full text-xs"
            onClick={() => handleExport("html")}
            style={{ borderColor: "var(--cc-border)", color: "var(--cc-text)" }}
          >
            <Download className="w-3 h-3 mr-1" />
            HTML
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <ScrollArea className="flex-1">
        <div className="max-w-4xl mx-auto px-8 py-6">
          <RFCDocument run={run} rfcData={rfcData ?? undefined} />
        </div>
      </ScrollArea>
    </div>
  );
}
