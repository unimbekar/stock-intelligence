"use client";

import Link from "next/link";
import { useState } from "react";

import { PageTitle } from "@/components/desk";
import { SymbolField } from "@/components/symbol-field";
import { api } from "@/lib/client";

type Bundle = {
  ticker: string;
  items: {
    id: string;
    title: string;
    summary: string;
    source: string;
    url?: string | null;
    synthetic: boolean;
    disclosure: string;
  }[];
  consensus: { consensus: string; disclosure: string };
};

export default function ResearchPage() {
  const [ticker, setTicker] = useState("AAPL");
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function open(symbol: string) {
    const next = symbol.trim().toUpperCase();
    if (!next) return;
    setLoading(true);
    const result = await api<Bundle>(`/api/v1/research/${next}`);
    setLoading(false);
    if (!result.ok || !result.body) {
      setBundle(null);
      setError(result.detail || "Research could not be loaded.");
      return;
    }
    setError("");
    setBundle(result.body);
  }

  return (
    <div className="space-y-6">
      <PageTitle
        kicker="Research"
        title="Research"
        text="Session figures come from Nasdaq. Annual facts and filing links come from SEC EDGAR. Analyst targets are not estimated."
      />
      <form
        className="flex max-w-xl gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          void open(ticker);
        }}
      >
        <div className="w-72">
          <SymbolField value={ticker} onChange={setTicker} />
        </div>
        <button type="submit" className="border border-line px-3 py-1 text-sm">
          Open
        </button>
      </form>
      {loading ? <p className="text-sm text-muted">Loading the session and the SEC filings.</p> : null}
      {error ? <p className="text-sm text-negative">{error}</p> : null}
      {bundle ? (
        <section className="space-y-3">
          <h2 className="text-sm font-medium">
            <Link href={`/stocks/${bundle.ticker}`}>{bundle.ticker}</Link>
          </h2>
          <p className="text-xs text-muted">{bundle.consensus.disclosure}</p>
          {bundle.items.map((item) => (
            <article key={item.id} className="border border-line p-4 text-sm">
              <p className="text-xs text-muted">{item.source}</p>
              <h3 className="mt-1 font-medium">
                {item.url ? (
                  <a href={item.url} target="_blank" rel="noreferrer">
                    {item.title}
                  </a>
                ) : (
                  item.title
                )}
              </h3>
              <p className="mt-2 leading-6 text-muted">{item.summary}</p>
              <p className="mt-2 text-xs text-muted">{item.disclosure}</p>
            </article>
          ))}
        </section>
      ) : null}
    </div>
  );
}
