"use client";

import { useMemo } from "react";
import type { Phase } from "@/lib/types";
import {
  ReactFlow,
  Node,
  Edge,
  Background,
  Controls,
  BackgroundVariant,
  Handle,
  Position,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

const PHASES: Phase[] = [
  "ingestion",
  "analysis",
  "debate",
  "synthesis",
  "review",
  "output",
];

const PHASE_COLORS: Record<Phase, string> = {
  ingestion: "#4ecdc4",
  analysis: "#d4a574",
  debate: "#6c5ce7",
  synthesis: "#00d68f",
  review: "#ffd93d",
  output: "#ff6b6b",
};

const PHASE_LABELS: Record<Phase, string> = {
  ingestion: "Ingest",
  analysis: "Analyse",
  debate: "Debate",
  synthesis: "Synthesise",
  review: "Review",
  output: "Output",
};

function PhaseNode({
  data,
}: {
  data: { label: string; phase: Phase; status: "completed" | "active" | "pending" };
}) {
  const color = PHASE_COLORS[data.phase] || "#888";
  const isActive = data.status === "active";
  const isDone = data.status === "completed";

  return (
    <div
      className="px-3 py-2 rounded-lg border text-center min-w-[80px] transition-all"
      style={{
        backgroundColor: isActive ? `${color}33` : isDone ? `${color}11` : "var(--cc-bg-card)",
        borderColor: isActive ? color : isDone ? `${color}66` : "var(--cc-border)",
        boxShadow: isActive ? `0 0 16px ${color}55` : "none",
        color: isActive ? color : isDone ? `${color}cc` : "var(--cc-text-muted)",
      }}
    >
      <Handle type="target" position={Position.Left} style={{ background: color, border: "none" }} />
      <div className="text-xs font-semibold">{data.label}</div>
      <div
        className="text-xs mt-0.5"
        style={{ opacity: 0.7 }}
      >
        {isActive ? "●" : isDone ? "✓" : "○"}
      </div>
      <Handle type="source" position={Position.Right} style={{ background: color, border: "none" }} />
    </div>
  );
}

const nodeTypes = { phaseNode: PhaseNode };

interface GraphVisualizerProps {
  currentPhase?: Phase | null;
  completedPhases?: Phase[];
}

export function GraphVisualizer({
  currentPhase,
  completedPhases = [],
}: GraphVisualizerProps) {
  const nodes: Node[] = useMemo(
    () =>
      PHASES.map((phase, i) => ({
        id: phase,
        type: "phaseNode",
        position: { x: i * 130, y: 60 },
        data: {
          label: PHASE_LABELS[phase],
          phase,
          status: completedPhases.includes(phase)
            ? "completed"
            : currentPhase === phase
            ? "active"
            : "pending",
        },
      })),
    [currentPhase, completedPhases]
  );

  const edges: Edge[] = useMemo(
    () =>
      PHASES.slice(0, -1).map((phase, i) => {
        const isDone = completedPhases.includes(phase);
        const color = isDone ? PHASE_COLORS[phase] : "var(--cc-border)";
        return {
          id: `${phase}-${PHASES[i + 1]}`,
          source: phase,
          target: PHASES[i + 1],
          animated: currentPhase === phase,
          style: { stroke: color, strokeWidth: 2 },
        };
      }),
    [currentPhase, completedPhases]
  );

  return (
    <div
      className="rounded-lg border overflow-hidden"
      style={{
        backgroundColor: "var(--cc-bg-card)",
        borderColor: "var(--cc-border)",
        height: "180px",
      }}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        zoomOnScroll={false}
        panOnDrag={false}
        style={{ background: "transparent" }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={16}
          size={1}
          color="var(--cc-border)"
        />
        <Controls
          showInteractive={false}
          className="bg-transparent"
          style={{ filter: "invert(0.8)" }}
        />
      </ReactFlow>
    </div>
  );
}
