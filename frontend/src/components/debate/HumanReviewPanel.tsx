"use client";

import { useState } from "react";
import type { Finding } from "@/lib/types";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { CheckCircle2, XCircle, AlertTriangle } from "lucide-react";
import { toast } from "sonner";

const SEVERITY_COLORS: Record<string, string> = {
  critical: "var(--cc-red)",
  high: "#ff9500",
  medium: "var(--cc-yellow)",
  low: "var(--cc-blue)",
  info: "var(--cc-text-muted)",
};

interface HumanReviewPanelProps {
  findings: Finding[];
  onApprove?: (findingId: string, note: string) => void;
  onOverride?: (findingId: string, note: string) => void;
}

export function HumanReviewPanel({
  findings,
  onApprove,
  onOverride,
}: HumanReviewPanelProps) {
  const [notes, setNotes] = useState<Record<string, string>>({});
  const [reviewed, setReviewed] = useState<Record<string, "approved" | "overridden">>({});

  function handleApprove(findingId: string) {
    onApprove?.(findingId, notes[findingId] || "");
    setReviewed((r) => ({ ...r, [findingId]: "approved" }));
    toast.success("Finding approved");
  }

  function handleOverride(findingId: string) {
    onOverride?.(findingId, notes[findingId] || "");
    setReviewed((r) => ({ ...r, [findingId]: "overridden" }));
    toast.success("Finding overridden");
  }

  const pendingFindings = findings.filter((f) => !reviewed[f.id]);
  const reviewedCount = Object.keys(reviewed).length;

  return (
    <div
      className="rounded-lg border overflow-hidden"
      style={{
        backgroundColor: "var(--cc-bg-card)",
        borderColor: "#ff950066",
      }}
    >
      <div
        className="flex items-center justify-between px-4 py-3 border-b"
        style={{ borderColor: "var(--cc-border)" }}
      >
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" style={{ color: "#ff9500" }} />
          <h3 className="text-sm font-medium" style={{ color: "var(--cc-text)" }}>
            Human Review Required
          </h3>
        </div>
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            style={{ color: "var(--cc-green)", borderColor: "var(--cc-green)44" }}
          >
            {reviewedCount} reviewed
          </Badge>
          <Badge
            variant="outline"
            style={{ color: "#ff9500", borderColor: "#ff950044" }}
          >
            {pendingFindings.length} pending
          </Badge>
        </div>
      </div>

      <ScrollArea className="max-h-96">
        <div className="p-4 space-y-4">
          {pendingFindings.length === 0 ? (
            <div
              className="text-center py-6 text-sm"
              style={{ color: "var(--cc-green)" }}
            >
              <CheckCircle2 className="w-8 h-8 mx-auto mb-2" />
              All findings reviewed!
            </div>
          ) : (
            pendingFindings.map((finding) => {
              const sevColor = SEVERITY_COLORS[finding.severity] || "var(--cc-text-muted)";
              return (
                <div
                  key={finding.id}
                  className="rounded-lg p-3 space-y-2"
                  style={{ backgroundColor: "var(--cc-bg)", border: `1px solid var(--cc-border)` }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div
                        className="text-sm font-medium"
                        style={{ color: "var(--cc-text)" }}
                      >
                        {finding.title}
                      </div>
                      {finding.file_path && (
                        <div
                          className="text-xs mt-0.5"
                          style={{
                            color: "var(--cc-text-muted)",
                            fontFamily: "var(--font-geist-mono)",
                          }}
                        >
                          {finding.file_path}
                          {finding.line_start && `:${finding.line_start}`}
                        </div>
                      )}
                    </div>
                    <Badge
                      variant="outline"
                      className="shrink-0"
                      style={{
                        borderColor: `${sevColor}66`,
                        color: sevColor,
                        backgroundColor: `${sevColor}11`,
                      }}
                    >
                      {finding.severity}
                    </Badge>
                  </div>

                  <p
                    className="text-xs leading-relaxed"
                    style={{ color: "var(--cc-text-muted)" }}
                  >
                    {finding.description}
                  </p>

                  {finding.recommendation && (
                    <div
                      className="text-xs px-2 py-1.5 rounded border"
                      style={{
                        borderColor: "var(--cc-accent)44",
                        backgroundColor: "var(--cc-accent)11",
                        color: "var(--cc-accent)",
                      }}
                    >
                      Rec: {finding.recommendation}
                    </div>
                  )}

                  <div className="flex gap-2">
                    <Input
                      placeholder="Add note (optional)…"
                      value={notes[finding.id] || ""}
                      onChange={(e) =>
                        setNotes((n) => ({ ...n, [finding.id]: e.target.value }))
                      }
                      className="h-7 text-xs flex-1"
                      style={{
                        backgroundColor: "var(--cc-bg-card)",
                        borderColor: "var(--cc-border)",
                        color: "var(--cc-text)",
                      }}
                    />
                    <Button
                      size="sm"
                      onClick={() => handleApprove(finding.id)}
                      className="h-7 text-xs px-3"
                      style={{ backgroundColor: "var(--cc-green)", color: "black" }}
                    >
                      <CheckCircle2 className="w-3 h-3 mr-1" />
                      Approve
                    </Button>
                    <Button
                      size="sm"
                      onClick={() => handleOverride(finding.id)}
                      variant="outline"
                      className="h-7 text-xs px-3"
                      style={{
                        borderColor: "var(--cc-red)",
                        color: "var(--cc-red)",
                      }}
                    >
                      <XCircle className="w-3 h-3 mr-1" />
                      Override
                    </Button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
