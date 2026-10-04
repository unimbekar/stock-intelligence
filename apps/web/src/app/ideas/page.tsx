"use client";

import Link from "next/link";
import { useState } from "react";

import { Notice, PageTitle, SignInPrompt, useWorkspace } from "@/components/desk";
import { api, type Idea } from "@/lib/client";
import { money } from "@/lib/format";

export default function IdeasPage() {
  const { workspace, error, reload } = useWorkspace();
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [note, setNote] = useState("");
  const [message, setMessage] = useState("");
  const [category, setCategory] = useState("AI");

  async function run() {
    const result = await api<{ ideas: Idea[]; note: string; disclaimer: string }>("/api/v1/ideas/search", {
      method: "POST",
      body: JSON.stringify({ categories: category === "All" ? [] : [category] }),
    });
    if (!result.ok || !result.body) {
      setMessage(result.detail || "Ideas could not be ranked.");
      return;
    }
    setIdeas(result.body.ideas);
    setNote(`${result.body.note} ${result.body.disclaimer}`);
  }

  async function save(idea: Idea) {
    const result = await api("/api/v1/ideas", {
      method: "POST",
      body: JSON.stringify({ ticker: idea.ticker, title: `${idea.ticker} score ${idea.score}`, payload: idea }),
    });
    setMessage(result.ok ? `${idea.ticker} saved.` : result.detail);
    reload();
  }

  if (error) {
    return (
      <div className="space-y-4">
        <PageTitle kicker="Ideas" title="AI Ideas" />
        <SignInPrompt />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageTitle
        kicker="Ideas"
        title="AI Ideas"
        text="Long-only ranks from the last Nasdaq session and SEC annual facts. Analyst ratings are not part of the score. Five names, or fewer when the filter matches fewer."
      />
      <div className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          Category
          <select className="ml-2 border border-line bg-bg px-2 py-1" value={category} onChange={(event) => setCategory(event.target.value)}>
            {["All", "AI", "Semiconductors", "Technology", "Healthcare", "Financials", "Consumer"].map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <button type="button" className="border border-line bg-muted-surface px-3 py-1.5 text-sm" onClick={run}>
          Rank ideas
        </button>
      </div>
      {note ? <Notice text={note} /> : null}
      {message ? <p className="text-sm">{message}</p> : null}
      <div className="space-y-4">
        {ideas.map((idea) => (
          <article key={idea.ticker} className="border border-line bg-elevated p-4">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 className="text-lg">
                <Link href={`/stocks/${idea.ticker}`} className="num">
                  {idea.ticker}
                </Link>{" "}
                <span className="text-sm text-muted">{idea.company}</span>
              </h2>
              <p className="num text-sm">
                {idea.score} · {idea.confidence} · {money(idea.price)}
              </p>
            </div>
            <p className="mt-2 text-sm text-muted">
              Entry {idea.entryLow}–{idea.entryHigh}. Stop {idea.stop ?? "unavailable"}. Targets {idea.target1 ?? "—"} /{" "}
              {idea.target2 ?? "—"}. Suggested shares {idea.suggestedShares ?? "—"}.
            </p>
            <p className="mt-2 text-sm">{idea.catalyst}</p>
            <ul className="mt-2 list-disc pl-5 text-sm text-muted">
              {idea.bull.map((item) => (
                <li key={item}>{item}</li>
              ))}
              {idea.bear.map((item) => (
                <li key={item}>{item}</li>
              ))}
              {idea.risks.map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-muted">{idea.evidence.items[0]?.disclosure}</p>
            <button type="button" className="mt-3 border border-line px-2 py-1 text-sm" onClick={() => save(idea)}>
              Save idea
            </button>
          </article>
        ))}
      </div>
      {workspace && workspace.savedIdeas.length > 0 ? (
        <section>
          <h2 className="text-sm font-medium">Saved</h2>
          <ul className="mt-2 text-sm">
            {workspace.savedIdeas.map((item) => (
              <SavedIdeaRow key={item.id} item={item} onReload={reload} onMessage={setMessage} />
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  );
}

function SavedIdeaRow({
  item,
  onReload,
  onMessage,
}: {
  item: { id: string; ticker: string; title: string };
  onReload: () => void;
  onMessage: (message: string) => void;
}) {
  const [title, setTitle] = useState(item.title);
  const [editing, setEditing] = useState(false);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    const result = await api(`/api/v1/ideas/${item.id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    });
    onMessage(result.ok ? "Saved idea updated." : result.detail);
    if (result.ok) setEditing(false);
    onReload();
  }

  return (
    <li className="flex items-center justify-between gap-3 border-t border-line py-2">
      {editing ? (
        <form onSubmit={save} className="flex flex-1 gap-2">
          <input className="w-full border border-line bg-bg px-2 py-1" value={title} onChange={(event) => setTitle(event.target.value)} aria-label="Idea title" />
          <button type="submit" className="text-xs">
            Save
          </button>
          <button type="button" className="text-xs text-muted" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </form>
      ) : (
        <Link href={`/stocks/${item.ticker}`}>{item.title}</Link>
      )}
      <span className="flex gap-3">
        <button type="button" className="text-xs" onClick={() => setEditing(true)}>
          Edit
        </button>
        <button type="button" className="text-muted" onClick={() => api(`/api/v1/ideas/${item.id}`, { method: "DELETE" }).then(onReload)}>
          Remove
        </button>
      </span>
    </li>
  );
}
