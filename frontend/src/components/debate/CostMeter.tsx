"use client";

import type { CostReport } from "@/lib/types";
import { formatCost, formatTokens } from "@/lib/utils";
import { DollarSign, Zap } from "lucide-react";

interface CostMeterProps {
  cost?: CostReport | null;
  budgetLimit?: number;
}

export function CostMeter({ cost, budgetLimit }: CostMeterProps) {
  const totalCost = cost?.total_cost ?? 0;
  const pct = budgetLimit ? Math.min((totalCost / budgetLimit) * 100, 100) : 0;
  const isWarning = pct > 80;
  const isDanger = pct > 95;

  const color = isDanger
    ? "var(--cc-red)"
    : isWarning
    ? "var(--cc-yellow)"
    : "var(--cc-green)";

  return (
    <div
      className="flex items-center gap-3 px-3 py-1.5 rounded-lg border"
      style={{
        backgroundColor: "var(--cc-bg-card)",
        borderColor: isDanger
          ? "var(--cc-red)"
          : isWarning
          ? "var(--cc-yellow)"
          : "var(--cc-border)",
      }}
    >
      <DollarSign className="w-4 h-4" style={{ color }} />
      <div>
        <div
          className="text-sm font-mono font-bold"
          style={{ color, fontFamily: "var(--font-geist-mono)" }}
        >
          {formatCost(totalCost)}
        </div>
        {budgetLimit && (
          <div className="flex items-center gap-1 mt-0.5">
            <div
              className="h-1 w-16 rounded-full overflow-hidden"
              style={{ backgroundColor: "var(--cc-border)" }}
            >
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${pct}%`, backgroundColor: color }}
              />
            </div>
            <span className="text-xs" style={{ color: "var(--cc-text-muted)" }}>
              / {formatCost(budgetLimit)}
            </span>
          </div>
        )}
      </div>

      {cost?.total_tokens != null && (
        <div
          className="flex items-center gap-1 text-xs border-l pl-3"
          style={{
            borderColor: "var(--cc-border)",
            color: "var(--cc-text-muted)",
          }}
        >
          <Zap className="w-3 h-3" />
          <span style={{ fontFamily: "var(--font-geist-mono)" }}>
            {formatTokens(cost.total_tokens)}
          </span>
        </div>
      )}
    </div>
  );
}
