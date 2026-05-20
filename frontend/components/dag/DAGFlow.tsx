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
  success: "#34c759",
  running: "#0071e3",
  failed: "#d70015",
  pending: "#8e8e93",
  skipped: "#c7c7cc"
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

  source_planning: { x: 242, y: 72, source: Position.Bottom, target: Position.Left },
  web_search: { x: 242, y: 234, source: Position.Bottom, target: Position.Top },
  web_crawler: { x: 242, y: 396, source: Position.Right, target: Position.Top },

  schema_extraction: { x: 456, y: 150, source: Position.Bottom, target: Position.Left },
  evidence_builder: { x: 456, y: 330, source: Position.Right, target: Position.Top },

  product_positioning: { x: 650, y: 24, source: Position.Right, target: Position.Left },
  feature_matrix: { x: 650, y: 106, source: Position.Right, target: Position.Left },
  pricing_analysis: { x: 650, y: 188, source: Position.Right, target: Position.Left },
  user_voice: { x: 650, y: 270, source: Position.Right, target: Position.Left },
  technology_intelligence: { x: 650, y: 352, source: Position.Right, target: Position.Left },
  gtm: { x: 650, y: 434, source: Position.Right, target: Position.Left },

  swot: { x: 860, y: 170, source: Position.Bottom, target: Position.Left },
  strategic_insight: { x: 860, y: 312, source: Position.Right, target: Position.Top },
  analysis: { x: 1060, y: 242, source: Position.Right, target: Position.Left },

  fact_check: { x: 1260, y: 44, source: Position.Right, target: Position.Left },
  citation_check: { x: 1260, y: 144, source: Position.Right, target: Position.Left },
  consistency_check: { x: 1260, y: 244, source: Position.Right, target: Position.Left },
  bias_detection: { x: 1260, y: 344, source: Position.Right, target: Position.Left },
  red_team: { x: 1260, y: 444, source: Position.Right, target: Position.Left },

  quality_gate: { x: 1460, y: 242, source: Position.Right, target: Position.Left },
  report_writer: { x: 1660, y: 242, source: Position.Right, target: Position.Left }
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
            <div className="mt-2 inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium text-white" style={{ background: statusColor[node.status] ?? "#8e8e93" }}>
              {statusTone[node.status] ?? node.status}
            </div>
          </div>
        )
      },
      style: {
        width: nodeWidth,
        border: `1px solid ${statusColor[node.status] ?? "#d2d2d7"}`,
        borderRadius: 8,
        background: "linear-gradient(180deg, rgba(255,255,255,0.96), rgba(247,250,255,0.92))",
        padding: 10,
        boxShadow: "0 14px 30px rgba(36,49,70,0.08)"
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
      style: { stroke: "#8e8e93", strokeWidth: 1.2 }
    }));
  }, [dag]);

  return (
    <div className="surface h-[620px] overflow-hidden bg-white/70">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        fitViewOptions={{ padding: 0.03, maxZoom: 0.95 }}
        minZoom={0.25}
        maxZoom={1.4}
        nodesConnectable={false}
        nodesDraggable={false}
        panOnDrag={false}
        panOnScroll={false}
        preventScrolling={false}
        zoomOnDoubleClick={false}
        zoomOnPinch={false}
        zoomOnScroll={false}
        proOptions={{ hideAttribution: false }}
      >
        <AutoFit fitKey={fitKey} />
        <Background color="#c7d4e5" gap={20} />
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
        void fitView({ padding: 0.03, maxZoom: 0.95, duration: 250 });
      }, 60);
    });
    return () => {
      window.cancelAnimationFrame(frame);
      if (timeout) window.clearTimeout(timeout);
    };
  }, [fitKey, fitView, nodesInitialized]);
  return null;
}
