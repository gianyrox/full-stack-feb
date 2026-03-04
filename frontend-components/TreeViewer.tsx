import React, { useState } from "react";
import type { RuleNode, StructuredPolicy } from "./types";

interface RuleNodeViewProps {
  node: RuleNode;
  depth: number;
}

function RuleNodeView({ node, depth }: RuleNodeViewProps) {
  const isLeaf = !node.rules || node.rules.length === 0;
  const [expanded, setExpanded] = useState(depth < 2);

  if (isLeaf) {
    return (
      <div className="ml-4 py-1.5 pl-3 border-l-2 border-slate-300 text-sm text-slate-700">
        <span className="text-xs font-mono text-slate-400 mr-2">
          {node.rule_id}
        </span>
        {node.rule_text}
      </div>
    );
  }

  const isAnd = node.operator === "AND";
  const badgeColor = isAnd
    ? "bg-emerald-100 text-emerald-700 border-emerald-300"
    : "bg-orange-100 text-orange-700 border-orange-300";

  return (
    <div className="ml-4 my-1">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full text-left group py-1"
      >
        <span className="text-slate-400 text-xs w-4 flex-shrink-0">
          {expanded ? "▾" : "▸"}
        </span>
        <span
          className={`text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded border ${badgeColor}`}
        >
          {node.operator}
        </span>
        <span className="text-xs font-mono text-slate-400 mr-1">
          {node.rule_id}
        </span>
        <span className="text-sm text-slate-800 group-hover:text-slate-600">
          {node.rule_text}
        </span>
      </button>
      {expanded && node.rules && (
        <div className="ml-2 border-l border-slate-200">
          {node.rules.map((child) => (
            <RuleNodeView key={child.rule_id} node={child} depth={depth + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

interface TreeViewerProps {
  data: StructuredPolicy;
}

export default function TreeViewer({ data }: TreeViewerProps) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 p-4">
      <h2 className="text-lg font-semibold text-slate-900 mb-1">
        {data.title}
      </h2>
      <p className="text-xs text-slate-500 mb-4">{data.insurance_name}</p>
      <RuleNodeView node={data.rules} depth={0} />
    </div>
  );
}
