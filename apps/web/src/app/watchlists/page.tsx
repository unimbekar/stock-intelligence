"use client";

import Link from "next/link";
import { useState } from "react";

import { PageTitle, SignInPrompt, tone, useWorkspace } from "@/components/desk";
import { SymbolField } from "@/components/symbol-field";
import { api } from "@/lib/client";
import { signed } from "@/lib/format";

export default function WatchlistsPage() {
  const { workspace, error, reload } = useWorkspace();
  const [name, setName] = useState("");
  const [message, setMessage] = useState("");

  async function createList(event: React.FormEvent) {
    event.preventDefault();
    const result = await api("/api/v1/watchlists", { method: "POST", body: JSON.stringify({ name }) });
    setMessage(result.ok ? "List created." : result.detail);
    setName("");
    reload();
  }

  if (error) {
    return (
      <div className="space-y-4">
        <PageTitle kicker="Lists" title="Watchlists" />
        <SignInPrompt />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageTitle
        kicker="Lists"
        title="Watchlists"
        text="Search any US company in the SEC ticker file. The price is that symbol's last Nasdaq session."
      />
      <form onSubmit={createList} className="flex gap-2">
        <input
          className="border border-line bg-bg px-2 py-1 text-sm"
          placeholder="New list name"
          value={name}
          onChange={(event) => setName(event.target.value)}
        />
        <button type="submit" className="border border-line px-3 py-1 text-sm">
          Create
        </button>
      </form>
      {message ? <p className="text-sm">{message}</p> : null}
      <div className="space-y-4">
        {workspace?.watchlists.map((list) => (
          <WatchlistCard key={list.id} list={list} onMessage={setMessage} onReload={reload} />
        ))}
      </div>
    </div>
  );
}

function WatchlistCard({
  list,
  onMessage,
  onReload,
}: {
  list: { id: string; name: string; items: { ticker: string; price?: string | null; changePercent?: string | null }[] };
  onMessage: (message: string) => void;
  onReload: () => void;
}) {
  const [ticker, setTicker] = useState("");
  const [name, setName] = useState(list.name);
  const [renaming, setRenaming] = useState(false);

  async function rename(event: React.FormEvent) {
    event.preventDefault();
    const result = await api(`/api/v1/watchlists/${list.id}`, {
      method: "PATCH",
      body: JSON.stringify({ name }),
    });
    onMessage(result.ok ? "List renamed." : result.detail);
    if (result.ok) setRenaming(false);
    onReload();
  }

  async function add(event: React.FormEvent) {
    event.preventDefault();
    const symbol = ticker.trim().toUpperCase();
    if (!symbol) return;
    const result = await api(`/api/v1/watchlists/${list.id}/items`, {
      method: "POST",
      body: JSON.stringify({ ticker: symbol }),
    });
    onMessage(result.ok ? `${symbol} added.` : result.detail);
    if (result.ok) setTicker("");
    onReload();
  }

  return (
    <section className="border border-line bg-elevated">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        {renaming ? (
          <form onSubmit={rename} className="flex gap-2">
            <input className="border border-line bg-bg px-2 py-1 text-sm" value={name} onChange={(event) => setName(event.target.value)} aria-label="List name" />
            <button type="submit" className="text-xs">
              Save
            </button>
            <button type="button" className="text-xs text-muted" onClick={() => setRenaming(false)}>
              Cancel
            </button>
          </form>
        ) : (
          <h2 className="text-sm font-medium">{list.name}</h2>
        )}
        <span className="flex gap-3">
          <button type="button" className="text-xs" onClick={() => setRenaming(true)}>
            Rename
          </button>
          <button
            type="button"
            className="text-xs text-muted"
            onClick={() => api(`/api/v1/watchlists/${list.id}`, { method: "DELETE" }).then(onReload)}
          >
            Delete list
          </button>
        </span>
      </div>
      <ul className="divide-y divide-line text-sm">
        {list.items.length === 0 ? <li className="px-4 py-3 text-muted">Empty.</li> : null}
        {list.items.map((item) => (
          <li key={item.ticker} className="flex items-center justify-between px-4 py-2">
            <Link href={`/stocks/${item.ticker}`} className="num">
              {item.ticker}
            </Link>
            <span className="num">{item.price ?? "—"}</span>
            <span className={tone(item.changePercent ?? "0")}>
              {item.changePercent ? `${signed(item.changePercent)}%` : "—"}
            </span>
            <button
              type="button"
              className="text-xs text-muted"
              onClick={() => api(`/api/v1/watchlists/${list.id}/items/${item.ticker}`, { method: "DELETE" }).then(onReload)}
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
      <form onSubmit={add} className="flex gap-2 border-t border-line px-4 py-3">
        <div className="w-64">
          <SymbolField value={ticker} onChange={setTicker} />
        </div>
        <button type="submit" className="border border-line px-2 py-1 text-sm">
          Add
        </button>
      </form>
    </section>
  );
}
