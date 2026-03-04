import { useState } from "react";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface Message {
  role: "user" | "assistant";
  text: string;
}

export default function AdminChat() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);

  const send = async () => {
    const msg = input.trim();
    if (!msg || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: msg }]);
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/api/admin/run`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: msg }),
      });
      const data = await res.json();
      setMessages((m) => [
        ...m,
        { role: "assistant", text: data.error || data.output || "(empty)" },
      ]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: `Error: ${e}` }]);
    } finally {
      setLoading(false);
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-50 h-12 w-12 rounded-full bg-blue-500 text-xl shadow-lg hover:bg-blue-600"
      >
        💬
      </button>
    );
  }

  return (
    <div className="fixed bottom-5 right-5 z-50 flex h-[480px] w-[380px] flex-col rounded-xl border border-slate-700 bg-slate-900 text-white shadow-2xl">
      <div className="flex items-center justify-between border-b border-slate-700 px-3 py-2">
        <span className="font-semibold">Admin</span>
        <button
          onClick={() => setOpen(false)}
          className="text-lg text-slate-400 hover:text-white"
        >
          ×
        </button>
      </div>
      <div className="flex flex-1 flex-col gap-2 overflow-auto p-3">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] whitespace-pre-wrap rounded-lg px-3 py-1.5 text-sm ${
              m.role === "user"
                ? "self-end bg-blue-500"
                : "self-start bg-slate-700"
            }`}
          >
            {m.text}
          </div>
        ))}
        {loading && <div className="text-sm text-slate-400">Running...</div>}
      </div>
      <div className="flex gap-2 border-t border-slate-700 p-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Message claude..."
          className="flex-1 rounded-md border border-slate-600 bg-slate-800 px-3 py-1.5 text-sm text-white placeholder-slate-400"
        />
        <button
          onClick={send}
          disabled={loading}
          className="rounded-md bg-blue-500 px-3 py-1.5 text-sm hover:bg-blue-600 disabled:opacity-50"
        >
          Send
        </button>
      </div>
    </div>
  );
}
