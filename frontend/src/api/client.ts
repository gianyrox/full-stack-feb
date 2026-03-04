const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function http<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`);
  if (!res.ok) {
    const msg = await res.text().catch(() => "");
    throw new Error(`HTTP ${res.status} ${res.statusText}${msg ? ` - ${msg}` : ""}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  listPolicies: () => http<import("./types").PolicyListItem[]>("/api/policies"),
  getPolicyDetail: (id: number) => http<import("./types").PolicyDetail>(`/api/policies/${id}`),
  getPolicyTree: (id: number) => http<import("./types").CriteriaTree>(`/api/policies/${id}/tree`),
};
