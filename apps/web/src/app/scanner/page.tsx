"use client";

import Link from "next/link";
import { useState } from "react";

import { PageTitle, SignInPrompt } from "@/components/desk";
import { api } from "@/lib/client";
import { compact, money } from "@/lib/format";

type Row = {
  ticker: string;
  company: string;
  sector: string;
  price: string;
  marketCap: number;
  volume: number;
  rsi: number | null;
  pe: number | null;
  score: number;
  analyst: string | null;
};

export default function ScannerPage() {
  const [rows, setRows] = useState<Row[]>([]);
  const [query, setQuery] = useState("");
  const [sector, setSector] = useState("All");
  const [error, setError] = useState("");

  async function run(event: React.FormEvent) {
    event.preventDefault();
    const result = await api<{ rows: Row[] }>("/api/v1/scanner", {
      method: "POST",
      body: JSON.stringify({ query, sector }),
    });
    if (result.status === 401) {
      setError("signin");
      return;
    }
    if (!result.ok || !result.body) {
      setError(result.detail || "Scan failed.");
      return;
    }
    setError("");
    setRows(result.body.rows);
  }

  return (
    <div className="space-y-6">
      <PageTitle kicker="Scanner" title="Stock Scanner" text="Filter the connected universe and sort by the active scoring weights." />
      <form onSubmit={run} className="flex flex-wrap gap-2">
        <input className="border border-line bg-bg px-2 py-1 text-sm" placeholder="Ticker or name" value={query} onChange={(event) => setQuery(event.target.value)} />
        <select className="border border-line bg-bg px-2 py-1 text-sm" value={sector} onChange={(event) => setSector(event.target.value)}>
          {["All", "Technology", "Healthcare", "Financials", "Consumer Discretionary", "Consumer Staples", "Communication Services"].map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <button type="submit" className="border border-line bg-muted-surface px-3 py-1 text-sm">
          Scan
        </button>
      </form>
      {error === "signin" ? <SignInPrompt /> : null}
      {error && error !== "signin" ? <p className="text-sm text-negative">{error}</p> : null}
      {rows.length > 0 ? (
        <div className="overflow-x-auto border border-line">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-muted-surface text-xs text-muted">
              <tr>
                {["Ticker", "Sector", "Price", "Market cap", "Volume", "RSI", "P/E", "Score"].map((label) => (
                  <th key={label} className="px-3 py-2 font-medium">
                    {label}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.ticker} className="border-t border-line">
                  <td className="px-3 py-2">
                    <Link href={`/stocks/${row.ticker}`} className="num">
                      {row.ticker}
                    </Link>
                    <span className="ml-2 text-muted">{row.company}</span>
                  </td>
                  <td className="px-3 py-2">{row.sector}</td>
                  <td className="num px-3 py-2">{money(row.price)}</td>
                  <td className="num px-3 py-2">{compact(row.marketCap)}</td>
                  <td className="num px-3 py-2">{compact(row.volume)}</td>
                  <td className="num px-3 py-2">{row.rsi ?? "—"}</td>
                  <td className="num px-3 py-2">{row.pe ?? "—"}</td>
                  <td className="num px-3 py-2">{row.score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}
