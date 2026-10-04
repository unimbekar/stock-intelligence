"use client";

import { useState } from "react";

import { PageTitle, SignInPrompt, useWorkspace } from "@/components/desk";
import { SymbolField } from "@/components/symbol-field";
import { api } from "@/lib/client";

export default function JournalPage() {
  const { workspace, error, reload } = useWorkspace();
  const [ticker, setTicker] = useState("NVDA");
  const [entryThesis, setEntryThesis] = useState("");
  const [notes, setNotes] = useState("");
  const [editing, setEditing] = useState("");
  const [message, setMessage] = useState("");

  async function save(event: React.FormEvent) {
    event.preventDefault();
    const payload = { ticker, entryThesis, notes, strategy: workspace?.preference.tradingStyle ?? "swing" };
    const result = editing
      ? await api(`/api/v1/journal/${editing}`, { method: "PATCH", body: JSON.stringify(payload) })
      : await api("/api/v1/journal", { method: "POST", body: JSON.stringify(payload) });
    setMessage(result.ok ? (editing ? "Entry updated." : "Entry saved.") : result.detail);
    if (result.ok) {
      setEditing("");
      setEntryThesis("");
      setNotes("");
    }
    reload();
  }

  if (error) {
    return (
      <div className="space-y-4">
        <PageTitle kicker="Journal" title="Trade Journal" />
        <SignInPrompt />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageTitle kicker="Journal" title="Trade Journal" text="Notes stay on this account. A review only restates the text you wrote." />
      <form onSubmit={save} className="space-y-3 border border-line bg-elevated p-4">
        <SymbolField value={ticker} onChange={setTicker} />
        <textarea className="w-full border border-line bg-bg px-2 py-1 text-sm" rows={3} placeholder="Entry thesis" value={entryThesis} onChange={(event) => setEntryThesis(event.target.value)} />
        <textarea className="w-full border border-line bg-bg px-2 py-1 text-sm" rows={2} placeholder="Notes" value={notes} onChange={(event) => setNotes(event.target.value)} />
        <div className="flex gap-2">
          <button type="submit" className="border border-line px-3 py-1 text-sm">
            {editing ? "Update entry" : "Save entry"}
          </button>
          {editing ? (
            <button
              type="button"
              className="border border-line px-3 py-1 text-sm text-muted"
              onClick={() => {
                setEditing("");
                setEntryThesis("");
                setNotes("");
              }}
            >
              Cancel
            </button>
          ) : null}
        </div>
      </form>
      {message ? <p className="text-sm">{message}</p> : null}
      <ul className="space-y-3">
        {workspace?.journal.map((entry) => (
          <li key={entry.id} className="border border-line p-4 text-sm">
            <div className="flex justify-between gap-3">
              <span className="num">{entry.ticker}</span>
              <span className="flex gap-3">
                <button
                  type="button"
                  className="text-xs"
                  onClick={() => {
                    setEditing(entry.id);
                    setTicker(entry.ticker);
                    setEntryThesis(entry.entryThesis);
                    setNotes(entry.notes);
                  }}
                >
                  Edit
                </button>
                <button type="button" className="text-xs text-muted" onClick={() => api(`/api/v1/journal/${entry.id}`, { method: "DELETE" }).then(reload)}>
                  Delete
                </button>
              </span>
            </div>
            <p className="mt-2">{entry.entryThesis}</p>
            <p className="mt-1 text-muted">{entry.notes}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
