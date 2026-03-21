"use client";

import type { CostReport } from "@/lib/types";
import { formatCost } from "@/lib/utils";
import { useRunStore } from "@/stores/runStore";

interface CostMeterProps {
  cost?: CostReport | null;
  budgetLimit?: number;
}

export function CostMeter({ cost }: CostMeterProps) {
  const run = useRunStore((s) => s.run);
  // Prefer cost report total, fall back to accumulated run total_cost
  const totalCost = cost?.total_cost ?? (run as any)?.total_cost ?? 0;

  return (
    <div
      className="flex items-center gap-1.5 px-3 py-1 rounded-lg border font-mono text-sm transition-all duration-200"
      style={{
        backgroundColor: "var(--cc-bg-card)",
        borderColor: "var(--cc-border)",
        color: "var(--cc-green)",
      }}
    >
      <span>$</span>
      <span>{formatCost(totalCost)}</span>
    </div>
  );
}
