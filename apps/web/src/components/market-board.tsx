"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { compact, money, signed } from "@/lib/format";
import type { Quote } from "@/lib/market";

type SortKey = "ticker" | "price" | "changePercent" | "volume" | "marketCap";

export function MarketBoard({ quotes, live = false }: { quotes: Quote[]; live?: boolean }) {
  const [query, setQuery] = useState("");
  const [sector, setSector] = useState("All");
  const [sortKey, setSortKey] = useState<SortKey>("ticker");
  const [ascending, setAscending] = useState(true);
  const [matches, setMatches] = useState<{ ticker: string; name: string }[]>([]);
  const sectors = useMemo(
    () => ["All", ...Array.from(new Set(quotes.map((quote) => quote.sector))).sort()],
    [quotes],
  );

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    const filtered = quotes.filter((quote) => {
      const matchesSector = sector === "All" || quote.sector === sector;
      const matchesQuery =
        needle.length === 0 ||
        quote.ticker.toLowerCase().includes(needle) ||
        quote.name.toLowerCase().includes(needle);
      return matchesSector && matchesQuery;
    });
    const direction = ascending ? 1 : -1;
    return filtered.sort((left, right) => {
      const a = sortValue(left, sortKey);
      const b = sortValue(right, sortKey);
      if (typeof a === "string" && typeof b === "string") return a.localeCompare(b) * direction;
      return (Number(a) - Number(b)) * direction;
    });
  }, [ascending, query, quotes, sector, sortKey]);

  useEffect(() => {
    const needle = query.trim();
    if (needle.length < 1) {
      setMatches([]);
      return;
    }
    const handle = window.setTimeout(() => {
      fetch(`/api/v1/symbols?q=${encodeURIComponent(needle)}`)
        .then((response) => (response.ok ? response.json() : { matches: [] }))
        .then((body: { matches?: { ticker: string; name: string }[] }) => setMatches(body.matches ?? []))
        .catch(() => setMatches([]));
    }, 180);
    return () => window.clearTimeout(handle);
  }, [query]);

  function chooseSort(next: SortKey) {
    if (next === sortKey) {
      setAscending((value) => !value);
      return;
    }
    setSortKey(next);
    setAscending(next === "ticker");
  }

  return (
    <div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] tracking-[0.18em] text-muted uppercase">
            {live ? "Last session" : "Sample tape"}
          </p>
          <h1 className="mt-2 text-3xl font-medium tracking-tight">Markets</h1>
        </div>
        <div className="flex flex-col gap-2 sm:flex-row">
          <label className="text-xs text-muted">
            Search
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              className="mt-1 block w-full border border-line bg-elevated px-2 py-1.5 text-sm text-ink sm:w-56"
              placeholder="Ticker or company"
            />
          </label>
          <label className="text-xs text-muted">
            Sector
            <select
              value={sector}
              onChange={(event) => setSector(event.target.value)}
              className="mt-1 block w-full border border-line bg-elevated px-2 py-1.5 text-sm text-ink"
            >
              {sectors.map((item) => (
                <option key={item}>{item}</option>
              ))}
            </select>
          </label>
        </div>
      </div>
      <p className="mt-3 text-sm text-muted">
        {rows.length} of {quotes.length} names on the core tape.
        {live ? " Levels are the last Nasdaq session, not a live quote." : ""}
      </p>
      {matches.length > 0 ? (
        <ul className="mt-3 flex flex-wrap gap-2 text-sm">
          {matches.map((match) => (
            <li key={match.ticker}>
              <Link href={`/stocks/${match.ticker}`} className="border border-line px-2 py-1">
                <span className="num">{match.ticker}</span>
                <span className="ml-2 text-muted">{match.name}</span>
              </Link>
            </li>
          ))}
        </ul>
      ) : null}
      {rows.length === 0 ? (
        <p className="mt-6 border border-line bg-elevated px-4 py-6 text-sm">
          No core-tape names match that filter. Use a match above to open another listed symbol.
        </p>
      ) : (
        <div className="mt-4 overflow-x-auto border border-line">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-muted-surface text-xs text-muted">
              <tr>
                <SortHeader label="Ticker" active={sortKey === "ticker"} onClick={() => chooseSort("ticker")} />
                <th className="px-3 py-2 font-medium">Company</th>
                <SortHeader label="Last" active={sortKey === "price"} onClick={() => chooseSort("price")} />
                <SortHeader label="Change %" active={sortKey === "changePercent"} onClick={() => chooseSort("changePercent")} />
                <SortHeader label="Volume" active={sortKey === "volume"} onClick={() => chooseSort("volume")} />
                <SortHeader label="Mkt cap" active={sortKey === "marketCap"} onClick={() => chooseSort("marketCap")} />
                <th className="px-3 py-2 font-medium">Sector</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((quote) => {
                const tone = toneFor(quote.change);
                return (
                  <tr key={quote.ticker} className="border-t border-line">
                    <td className="px-3 py-2">
                      <Link href={`/stocks/${quote.ticker}`} className="num font-medium underline-offset-2 hover:underline">
                        {quote.ticker}
                      </Link>
                    </td>
                    <td className="px-3 py-2 text-muted">{quote.name}</td>
                    <td className="num px-3 py-2">{money(quote.price)}</td>
                    <td className={`num px-3 py-2 ${tone}`}>{signed(quote.changePercent)}%</td>
                    <td className="num px-3 py-2">{compact(quote.volume)}</td>
                    <td className="num px-3 py-2">{compact(quote.marketCap)}</td>
                    <td className="px-3 py-2 text-muted">{quote.sector}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function toneFor(change: string): string {
  const value = Number(change);
  if (value > 0) return "text-positive";
  if (value < 0) return "text-negative";
  return "text-muted";
}

function sortValue(quote: Quote, key: SortKey): string | number {
  if (key === "ticker") return quote.ticker;
  if (key === "price") return Number(quote.price);
  if (key === "changePercent") return Number(quote.changePercent);
  if (key === "volume") return quote.volume;
  return quote.marketCap;
}

function SortHeader({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <th className="px-3 py-2 font-medium">
      <button type="button" onClick={onClick} className={active ? "text-ink" : ""}>
        {label}
      </button>
    </th>
  );
}
