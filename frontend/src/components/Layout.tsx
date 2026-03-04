import { Outlet } from "react-router-dom";
import AdminChat from "./AdminChat";

export function Layout() {
  return (
    <div className="min-h-screen bg-slate-100">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-6xl px-4 py-4">
          <div className="text-lg font-semibold text-slate-900">Medical Policy Criteria Explorer</div>
          <div className="text-sm text-slate-600">Discovery &rarr; Downloads &rarr; Structured Trees</div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">
        <Outlet />
      </main>
      <AdminChat />
    </div>
  );
}
