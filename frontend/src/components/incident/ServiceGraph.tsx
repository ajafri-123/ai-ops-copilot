"use client";

import {
  Background,
  BackgroundVariant,
  Controls,
  Edge,
  Handle,
  MarkerType,
  Node,
  Position,
  ReactFlow,
  ReactFlowProvider,
  useEdgesState,
  useNodesState,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { clsx } from "clsx";
import { useEffect, useMemo } from "react";
import type { ServiceGraphResponse } from "@/lib/types";

// ── Relationship → edge colour ────────────────────────────────────────────

const EDGE_COLOR: Record<string, string> = {
  depends_on:    "#ef4444", // red   – hard dependency
  calls:         "#6366f1", // indigo – RPC call
  reads_from:    "#22d3ee", // cyan   – DB read
  writes_to:     "#f59e0b", // amber  – DB write
  publishes_to:  "#a855f7", // purple – event pub
  subscribes_to: "#10b981", // green  – event sub
};

const EDGE_LABEL: Record<string, string> = {
  depends_on:    "depends on",
  calls:         "calls",
  reads_from:    "reads",
  writes_to:     "writes",
  publishes_to:  "publishes",
  subscribes_to: "subscribes",
};

// ── Custom service node ───────────────────────────────────────────────────

function ServiceNode({ data }: { data: { label: string; affected: boolean; group: string } }) {
  return (
    <div
      className={clsx(
        "relative flex min-w-[120px] items-center justify-center rounded-xl border px-4 py-3 text-center text-xs font-semibold shadow-lg transition-all",
        data.affected
          ? "border-red-500/60 bg-red-500/10 text-red-300 shadow-red-500/10 ring-1 ring-red-500/30"
          : "border-white/10 bg-[#151526] text-slate-400",
      )}
    >
      {data.affected && (
        <span className="absolute -top-1.5 -right-1.5 flex h-3 w-3">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-400 opacity-60" />
          <span className="relative inline-flex h-3 w-3 rounded-full bg-red-500" />
        </span>
      )}
      <Handle type="target" position={Position.Left} className="!bg-white/20 !border-white/10 !w-2 !h-2" />
      <span className="font-mono">{data.label}</span>
      <Handle type="source" position={Position.Right} className="!bg-white/20 !border-white/10 !w-2 !h-2" />
    </div>
  );
}

const nodeTypes = { serviceNode: ServiceNode };

// ── Layout: simple rank-based left→right positioning ──────────────────────

function computeLayout(
  rawNodes: ServiceGraphResponse["nodes"],
  rawEdges: ServiceGraphResponse["edges"],
): { nodes: Node[]; edges: Edge[] } {
  // Build adjacency for rank assignment
  const outgoing = new Map<string, Set<string>>();
  rawEdges.forEach((e) => {
    if (!outgoing.has(e.source)) outgoing.set(e.source, new Set());
    outgoing.get(e.source)!.add(e.target);
  });

  // BFS rank from root nodes (no incoming edges among affected)
  const incomingCount = new Map<string, number>();
  rawNodes.forEach((n) => incomingCount.set(n.id, 0));
  rawEdges.forEach((e) => {
    incomingCount.set(e.target, (incomingCount.get(e.target) ?? 0) + 1);
  });

  const rank = new Map<string, number>();
  const queue: string[] = [];

  // Seed with affected nodes first (they're the "root" of the incident)
  rawNodes.filter((n) => n.affected).forEach((n) => {
    rank.set(n.id, 0);
    queue.push(n.id);
  });
  rawNodes.filter((n) => !n.affected && (incomingCount.get(n.id) ?? 0) === 0).forEach((n) => {
    if (!rank.has(n.id)) {
      rank.set(n.id, 0);
      queue.push(n.id);
    }
  });
  if (queue.length === 0) rawNodes.forEach((n) => { if (!rank.has(n.id)) { rank.set(n.id, 0); queue.push(n.id); } });

  while (queue.length) {
    const curr = queue.shift()!;
    const currRank = rank.get(curr) ?? 0;
    (outgoing.get(curr) ?? new Set()).forEach((next) => {
      if (!rank.has(next)) {
        rank.set(next, currRank + 1);
        queue.push(next);
      }
    });
  }
  rawNodes.forEach((n) => { if (!rank.has(n.id)) rank.set(n.id, 0); });

  // Group by rank
  const byRank = new Map<number, string[]>();
  rank.forEach((r, id) => {
    if (!byRank.has(r)) byRank.set(r, []);
    byRank.get(r)!.push(id);
  });

  const COL_WIDTH = 200;
  const ROW_HEIGHT = 90;

  const posMap = new Map<string, { x: number; y: number }>();
  byRank.forEach((ids, r) => {
    ids.forEach((id, idx) => {
      const colCount = ids.length;
      posMap.set(id, {
        x: r * COL_WIDTH,
        y: idx * ROW_HEIGHT - ((colCount - 1) * ROW_HEIGHT) / 2,
      });
    });
  });

  const nodes: Node[] = rawNodes.map((n) => ({
    id: n.id,
    type: "serviceNode",
    position: posMap.get(n.id) ?? { x: 0, y: 0 },
    data: { label: n.label, affected: n.affected, group: n.group },
  }));

  const edges: Edge[] = rawEdges.map((e) => ({
    id: e.id,
    source: e.source,
    target: e.target,
    label: EDGE_LABEL[e.relationship] ?? e.relationship,
    labelStyle: { fill: "#64748b", fontSize: 10 },
    labelBgStyle: { fill: "#0d0d1e", fillOpacity: 0.8 },
    style: { stroke: EDGE_COLOR[e.relationship] ?? "#6366f1", strokeWidth: 1.5 },
    markerEnd: { type: MarkerType.ArrowClosed, color: EDGE_COLOR[e.relationship] ?? "#6366f1", width: 12, height: 12 },
    animated: e.relationship === "depends_on",
  }));

  return { nodes, edges };
}

// ── Main component ────────────────────────────────────────────────────────

interface Props {
  graph: ServiceGraphResponse;
}

function GraphInner({ graph }: Props) {
  const { nodes: layoutNodes, edges: layoutEdges } = useMemo(
    () => computeLayout(graph.nodes, graph.edges),
    [graph],
  );

  const [nodes, , onNodesChange] = useNodesState(layoutNodes);
  const [edges, , onEdgesChange] = useEdgesState(layoutEdges);

  // Legend data
  const usedRelationships = [...new Set(graph.edges.map((e) => e.relationship))];

  return (
    <div className="relative h-full w-full">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        minZoom={0.3}
        maxZoom={2}
        proOptions={{ hideAttribution: true }}
        className="rounded-xl"
        style={{ background: "transparent" }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1}
          color="#ffffff08"
        />
        <Controls
          className="!border-white/10 !bg-[#0d0d1e] !shadow-none [&>button]:!border-white/10 [&>button]:!bg-white/[0.04] [&>button]:!text-slate-400 [&>button:hover]:!bg-white/[0.08]"
          showInteractive={false}
        />
      </ReactFlow>

      {/* Legend */}
      {usedRelationships.length > 0 && (
        <div className="absolute bottom-3 left-3 flex flex-wrap gap-2">
          {usedRelationships.map((rel) => (
            <span
              key={rel}
              className="inline-flex items-center gap-1.5 rounded-md border border-white/[0.08] bg-[#0d0d1e]/90 px-2 py-1 text-[10px] backdrop-blur"
            >
              <span
                className="h-2 w-3 rounded-sm"
                style={{ background: EDGE_COLOR[rel] ?? "#6366f1" }}
              />
              <span className="text-slate-400">{EDGE_LABEL[rel] ?? rel}</span>
            </span>
          ))}
          <span className="inline-flex items-center gap-1.5 rounded-md border border-red-500/20 bg-red-500/10 px-2 py-1 text-[10px]">
            <span className="h-2 w-2 animate-ping rounded-full bg-red-500 opacity-75" />
            <span className="text-red-400">affected</span>
          </span>
        </div>
      )}
    </div>
  );
}

export function ServiceGraph({ graph }: Props) {
  if (graph.nodes.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-sm text-slate-600">
        No dependency data available
      </div>
    );
  }
  return (
    <ReactFlowProvider>
      <GraphInner graph={graph} />
    </ReactFlowProvider>
  );
}
