import React from "react";
import type { Policy } from "./types";

interface PolicyListProps {
  policies: Policy[];
  onSelect: (policyId: number) => void;
  selectedId?: number;
}

export default function PolicyList({
  policies,
  onSelect,
  selectedId,
}: PolicyListProps) {
  return (
    <div className="bg-white rounded-lg border border-slate-200 overflow-hidden">
      <div className="px-4 py-3 bg-slate-50 border-b border-slate-200">
        <h2 className="text-sm font-semibold text-slate-700 uppercase tracking-wide">
          Policies
        </h2>
      </div>
      <ul className="divide-y divide-slate-100">
        {policies.map((policy) => {
          const isSelected = policy.id === selectedId;
          return (
            <li
              key={policy.id}
              onClick={() => policy.has_structured && onSelect(policy.id)}
              className={`px-4 py-3 flex items-center justify-between gap-3 text-sm transition-colors ${
                policy.has_structured
                  ? "cursor-pointer hover:bg-slate-50"
                  : "opacity-60"
              } ${isSelected ? "bg-blue-50 border-l-2 border-blue-500" : ""}`}
            >
              <div className="min-w-0 flex-1">
                <p
                  className={`truncate font-medium ${
                    isSelected ? "text-blue-900" : "text-slate-800"
                  }`}
                >
                  {policy.title}
                </p>
                <a
                  href={policy.pdf_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="text-xs text-blue-500 hover:underline"
                >
                  PDF
                </a>
              </div>
              {policy.has_structured && (
                <span className="flex-shrink-0 text-[10px] font-semibold uppercase px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                  Structured
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}
