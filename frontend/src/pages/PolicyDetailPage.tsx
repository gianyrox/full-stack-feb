import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { PolicyDetail } from "../api/types";
import { Badge } from "../components/Badge";
import { Spinner } from "../components/Spinner";
import { ErrorBanner } from "../components/ErrorBanner";
import { TreeViewer } from "../components/TreeViewer";

function downloadBadge(status: PolicyDetail["download_status"]) {
  if (status === "success") return <Badge variant="success">Downloaded</Badge>;
  if (status === "failed") return <Badge variant="error">Failed</Badge>;
  return <Badge variant="warning">Pending</Badge>;
}

export function PolicyDetailPage() {
  const params = useParams();
  const id = Number(params.id);

  const [data, setData] = useState<PolicyDetail | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    api
      .getPolicyDetail(id)
      .then((d) => mounted && setData(d))
      .catch((e) => mounted && setErr(String(e?.message ?? e)));
    return () => {
      mounted = false;
    };
  }, [id]);

  return (
    <div className="space-y-4">
      <div>
        <Link
          to="/"
          className="inline-flex items-center text-sm font-medium text-slate-700 underline decoration-slate-300 underline-offset-2 hover:decoration-slate-500"
        >
          &larr; Back to list
        </Link>
      </div>

      {!data && !err && <Spinner label="Loading policy..." />}
      {err && <ErrorBanner message={err} />}

      {data && (
        <>
          <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <h1 className="text-xl font-semibold text-slate-900">{data.title}</h1>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {downloadBadge(data.download_status)}
                  {data.structured ? <Badge variant="info">Structured</Badge> : <Badge variant="neutral">Unstructured</Badge>}
                  <span className="text-xs text-slate-500">
                    Discovered: {new Date(data.discovered_at).toLocaleString()}
                  </span>
                </div>
              </div>

              <div className="flex flex-col gap-2 text-sm">
                <a
                  href={data.source_page_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sky-700 underline decoration-sky-200 underline-offset-2 hover:decoration-sky-400"
                >
                  Source page
                </a>
                <a
                  href={data.pdf_url}
                  target="_blank"
                  rel="noreferrer"
                  className="text-sky-700 underline decoration-sky-200 underline-offset-2 hover:decoration-sky-400"
                >
                  Open PDF
                </a>
              </div>
            </div>

            {data.latest_download && (
              <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-3 text-xs text-slate-700">
                <div className="font-semibold text-slate-800">Latest download attempt</div>
                <div className="mt-1 grid grid-cols-1 gap-1 sm:grid-cols-2">
                  <div>When: {new Date(data.latest_download.downloaded_at).toLocaleString()}</div>
                  <div>HTTP: {data.latest_download.http_status ?? "\u2014"}</div>
                  <div className="sm:col-span-2 break-words">
                    Stored: <span className="font-mono">{data.latest_download.stored_location}</span>
                  </div>
                  {data.latest_download.error && (
                    <div className="sm:col-span-2 text-rose-700">
                      Error: {data.latest_download.error}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          {data.structured?.structured_json ? (
            <div className="rounded-xl border border-slate-200 bg-white p-5 shadow-sm">
              <TreeViewer tree={data.structured.structured_json} />
            </div>
          ) : (
            <div className="rounded-xl border border-slate-200 bg-white p-5 text-sm text-slate-700 shadow-sm">
              No structured criteria available.
            </div>
          )}
        </>
      )}
    </div>
  );
}
