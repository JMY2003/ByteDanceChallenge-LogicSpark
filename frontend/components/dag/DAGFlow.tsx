"use client";

import { useEffect, useMemo } from "react";
import {
  Background,
  Controls,
  MarkerType,
  Position,
  ReactFlow,
  useNodesInitialized,
  useReactFlow,
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

const statusTone: Record<string, string> = {
  success: "成功",
  running: "运行中",
  failed: "失败",
  pending: "等待",
  skipped: "跳过"
};

const nodeWidth = 142;
const columnGap = 180;
const rowGap = 112;
const canvasCenterY = 300;

type LayoutSpec = {
  x: number;
  y: number;
  source?: Position;
  target?: Position;
};

const workflowLayout: Record<string, LayoutSpec> = {
  intent: { x: 28, y: 72, source: Position.Bottom, target: Position.Top },
  planner: { x: 28, y: 234, source: Position.Bottom, target: Position.Top },
  competitor_discovery: { x: 28, y: 396, source: Position.Right, target: Position.Top },

  source_planning: { x: 214, y: 72, source: Position.Bottom, target: Position.Left },
  web_search: { x: 214, y: 234, source: Position.Bottom, target: Position.Top },
  web_crawler: { x: 214, y: 396, source: Position.Right, target: Position.Top },

  document_cleaner: { x: 400, y: 72, source: Position.Bottom, target: Position.Left },
  schema_extraction: { x: 400, y: 234, source: Position.Bottom, target: Position.Top },
  evidence_builder: { x: 400, y: 396, source: Position.Right, target: Position.Top },

  product_positioning: { x: 610, y: 18 },
  feature_matrix: { x: 610, y: 116 },
  pricing_analysis: { x: 610, y: 214 },
  user_voice: { x: 610, y: 312 },
  technology_intelligence: { x: 610, y: 410 },
  gtm: { x: 610, y: 508 },

  swot: { x: 814, y: 116, source: Position.Bottom, target: Position.Left },
  strategic_insight: { x: 814, y: 286, source: Position.Bottom, target: Position.Top },
  analysis: { x: 814, y: 456, source: Position.Right, target: Position.Top },

  fact_check: { x: 1010, y: 50 },
  citation_check: { x: 1010, y: 160 },
  consistency_check: { x: 1010, y: 270 },
  bias_detection: { x: 1010, y: 380 },
  red_team: { x: 1010, y: 490 },

  quality_gate: { x: 1204, y: 190, source: Position.Bottom, target: Position.Left },
  report_writer: { x: 1204, y: 360, source: Position.Right, target: Position.Top }
};

export function DAGFlow({ dag }: { dag: DagResponse }) {
  const fitKey = useMemo(() => dag.nodes.map((node) => `${node.id}:${node.status}`).join("|"), [dag.nodes]);

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
    const byDepth = new Map<number, typeof dag.nodes>();
    for (const node of dag.nodes) {
      const column = depth.get(node.id) ?? 0;
      byDepth.set(column, [...(byDepth.get(column) ?? []), node]);
    }
    const rowById = new Map<string, { row: number; total: number }>();
    for (const items of byDepth.values()) {
      items.forEach((node, row) => rowById.set(node.id, { row, total: items.length }));
    }
    return dag.nodes.map((node) => ({
      id: node.id,
      position: (() => {
        const fixed = workflowLayout[node.id];
        if (fixed) return { x: fixed.x, y: fixed.y };
        const column = depth.get(node.id) ?? 0;
        const rowMeta = rowById.get(node.id) ?? { row: 0, total: 1 };
        return {
          x: 40 + column * columnGap,
          y: canvasCenterY + (rowMeta.row - (rowMeta.total - 1) / 2) * rowGap
        };
      })(),
      sourcePosition: workflowLayout[node.id]?.source ?? Position.Right,
      targetPosition: workflowLayout[node.id]?.target ?? Position.Left,
      data: {
        label: (
          <div className="w-[118px]">
            <div className="truncate text-xs font-semibold text-ink" title={node.label}>
              {node.label}
            </div>
            <div className="mt-1 truncate text-[11px] leading-4 text-steel" title={node.agent_name}>
              {node.agent_name.replace("Agent", "")}
            </div>
            <div className="mt-2 inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium text-white" style={{ background: statusColor[node.status] ?? "#667085" }}>
              {statusTone[node.status] ?? node.status}
            </div>
          </div>
        )
      },
      style: {
        width: nodeWidth,
        border: `1px solid ${statusColor[node.status] ?? "#d7dde5"}`,
        borderRadius: 8,
        background: "white",
        padding: 10,
        boxShadow: "0 8px 22px rgba(16,24,40,0.07)"
      }
    }));
  }, [dag]);

  const edges = useMemo<Edge[]>(() => {
    return dag.edges.map((edge) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: "smoothstep",
      animated: dag.nodes.find((node) => node.id === edge.target)?.status === "running",
      markerEnd: { type: MarkerType.ArrowClosed },
      style: { stroke: "#667085", strokeWidth: 1.2 }
    }));
  }, [dag]);

  return (
    <div className="h-[590px] rounded-lg border border-line bg-white">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.04, maxZoom: 1 }}
        minZoom={0.25}
        maxZoom={1.4}
        nodesConnectable={false}
        nodesDraggable={false}
        proOptions={{ hideAttribution: false }}
      >
        <AutoFit fitKey={fitKey} />
        <Background color="#d7dde5" gap={20} />
        <Controls position="bottom-left" />
      </ReactFlow>
    </div>
  );
}

function AutoFit({ fitKey }: { fitKey: string }) {
  const { fitView } = useReactFlow();
  const nodesInitialized = useNodesInitialized();

  useEffect(() => {
    if (!nodesInitialized) return;
    let timeout: number | undefined;
    const frame = window.requestAnimationFrame(() => {
      timeout = window.setTimeout(() => {
        void fitView({ padding: 0.04, maxZoom: 1, duration: 250 });
      }, 60);
    });
    return () => {
      window.cancelAnimationFrame(frame);
      if (timeout) window.clearTimeout(timeout);
    };
  }, [fitKey, fitView, nodesInitialized]);
  return null;
}
