import React from "react";
import type { Policy, StructuredPolicy } from "./types";
import TreeViewer from "./TreeViewer";

interface PolicyDetailProps {
  policy: Policy;
  structuredData: StructuredPolicy | null;
}

export default function PolicyDetail({
  policy,
  structuredData,
}: PolicyDetailProps) {
  return (
    <div className="space-y-4">
      <div className="bg-white rounded-lg border border-slate-200 p-4">
        <h1 className="text-xl font-bold text-slate-900 mb-2">
          {policy.title}
        </h1>
        <div className="flex gap-4 text-sm">
          <a
            href={policy.source_page_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            Source Page
          </a>
          <a
            href={policy.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-600 hover:underline"
          >
            Download PDF
          </a>
        </div>
        <p className="text-xs text-slate-400 mt-2">
          Discovered {new Date(policy.discovered_at).toLocaleDateString()}
        </p>
      </div>

      {structuredData ? (
        <TreeViewer data={structuredData} />
      ) : (
        <div className="bg-white rounded-lg border border-slate-200 p-8 text-center text-slate-400">
          No structured criteria available for this policy.
        </div>
      )}
    </div>
  );
}
