"use client";

import { useMemo } from "react";
import {
  Background,
  Controls,
  MarkerType,
  ReactFlow,
  type Edge,
  type Node
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import type { DagResponse } from "@/types/api";

const statusColor: Record<string, string> = {
  success: "#0f766e",
  running: "#2563eb",
  failed: "#b42318",
  pending: "#667085",
  skipped: "#98a2b3"
};

export function DAGFlow({ dag }: { dag: DagResponse }) {
  const nodes = useMemo<Node[]>(() => {
    const byId = new Map(dag.nodes.map((node) => [node.id, node]));
    const depth = new Map<string, number>();
    function getDepth(id: string): number {
      if (depth.has(id)) return depth.get(id)!;
      const node = byId.get(id);
      if (!node || !node.depends_on.length) {
        depth.set(id, 0);
        return 0;
      }
      const value = Math.max(...node.depends_on.map(getDepth)) + 1;
      depth.set(id, value);
      return value;
    }
    dag.nodes.forEach((node) => getDepth(node.id));
    const depthCounts = new Map<number, number>();
    return dag.nodes.map((node) => ({
      id: node.id,
      position: (() => {
        const column = depth.get(node.id) ?? 0;
        const row = depthCounts.get(column) ?? 0;
        depthCounts.set(column, row + 1);
        return { x: 80 + column * 245, y: 60 + row * 126 };
      })(),
      data: {
        label: (
          <div className="min-w-40">
            <div className="text-sm font-semibold text-ink">{node.label}</div>
            <div className="mt-1 text-xs text-steel">{node.agent_name}</div>
            <div className="mt-2 inline-flex rounded-full px-2 py-1 text-xs font-medium text-white" style={{ background: statusColor[node.status] ?? "#667085" }}>
              {node.status}
            </div>
          </div>
        )
      },
      style: {
        border: `1px solid ${statusColor[node.status] ?? "#d7dde5"}`,
        borderRadius: 8,
        background: "white",
        padding: 12,
        boxShadow: "0 10px 30px rgba(16,24,40,0.08)"
      }
    }));
  }, [dag.nodes]);

  const edges = useMemo<Edge[]>(() => {
    return dag.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      animated: dag.nodes.find((node) => node.id === edge.target)?.status === "running",
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: "#667085" }
    }));
  }, [dag.edges, dag.nodes]);

  return (
    <div className="h-[560px] rounded-lg border border-line bg-white">
      <ReactFlow nodes={nodes} edges={edges} fitView>
        <Background color="#d7dde5" gap={18} />
        <Controls />
      </ReactFlow>
    </div>
  );
}
