import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { PolicyListItem } from "../api/types";
import { Badge } from "../components/Badge";
import { Spinner } from "../components/Spinner";
import { ErrorBanner } from "../components/ErrorBanner";

function downloadBadge(status: PolicyListItem["download_status"]) {
  if (status === "success") return <Badge variant="success">Downloaded</Badge>;
  if (status === "failed") return <Badge variant="error">Failed</Badge>;
  return <Badge variant="warning">Pending</Badge>;
}

export function PolicyListPage() {
  const [items, setItems] = useState<PolicyListItem[] | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [q, setQ] = useState<string>("");

  useEffect(() => {
    let mounted = true;
    api
      .listPolicies()
      .then((data) => {
        if (!mounted) return;
        setItems(data);
      })
      .catch((e) => {
        if (!mounted) return;
        setErr(String(e?.message ?? e));
      });
    return () => {
      mounted = false;
    };
  }, []);

  const filtered = useMemo(() => {
    if (!items) return [];
    const needle = q.trim().toLowerCase();
    if (!needle) return items;
    return items.filter((p) => p.title.toLowerCase().includes(needle));
  }, [items, q]);

  return (
    <div className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Discovered Medical Policies</h1>
          <p className="mt-1 text-sm text-slate-600">
            Click a title to view the structured criteria tree (when available).
          </p>
        </div>

        <div className="w-full sm:w-80">
          <label className="block text-xs font-medium text-slate-700">Search by title</label>
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="e.g., MRI, knee, surgery..."
            className="mt-1 w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm focus:border-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-200"
          />
        </div>
      </div>

      {!items && !err && <Spinner label="Loading policies..." />}
      {err && <ErrorBanner message={err} />}

      {items && (
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200">
              <thead className="bg-slate-50">
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Title
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                    PDF
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Download
                  </th>
                  <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-600">
                    Structured
                  </th>
                </tr>
              </thead>

              <tbody className="divide-y divide-slate-100">
                {filtered.map((p) => (
                  <tr key={p.id} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <Link
                        to={`/policy/${p.id}`}
                        className="font-medium text-slate-900 underline decoration-slate-300 underline-offset-2 hover:decoration-slate-500"
                      >
                        {p.title}
                      </Link>
                      <div className="mt-1 text-xs text-slate-500">
                        Discovered: {new Date(p.discovered_at).toLocaleString()}
                      </div>
                    </td>

                    <td className="px-4 py-3">
                      <a
                        href={p.pdf_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-sm text-sky-700 underline decoration-sky-200 underline-offset-2 hover:decoration-sky-400"
                      >
                        Open PDF
                      </a>
                    </td>

                    <td className="px-4 py-3">{downloadBadge(p.download_status)}</td>

                    <td className="px-4 py-3">
                      {p.has_structured_tree ? (
                        <Link to={`/policy/${p.id}`} className="inline-flex items-center gap-2">
                          <Badge variant="info">Yes</Badge>
                          <span className="text-xs text-slate-500">View tree</span>
                        </Link>
                      ) : (
                        <Badge variant="neutral">No</Badge>
                      )}
                    </td>
                  </tr>
                ))}

                {filtered.length === 0 && (
                  <tr>
                    <td className="px-4 py-8 text-center text-sm text-slate-600" colSpan={4}>
                      No policies match "{q}".
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>

          <div className="border-t border-slate-200 bg-slate-50 px-4 py-3 text-xs text-slate-600">
            Showing {filtered.length} of {items.length} policies
          </div>
        </div>
      )}
    </div>
  );
}
