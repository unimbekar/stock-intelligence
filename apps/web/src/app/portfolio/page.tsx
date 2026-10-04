"use client";

import Link from "next/link";
import { useState } from "react";

import { MoneyCell, PageTitle, SignInPrompt, Stat, Usd, tone, useWorkspace } from "@/components/desk";
import { SymbolField } from "@/components/symbol-field";
import { api, type PositionRow } from "@/lib/client";
import { money, signed } from "@/lib/format";

export default function PortfolioPage() {
  const { workspace, error, reload } = useWorkspace();
  const portfolio = workspace?.portfolio;
  const [ticker, setTicker] = useState("");
  const [shares, setShares] = useState("10");
  const [buyPrice, setBuyPrice] = useState("");
  const [cash, setCash] = useState("");
  const [message, setMessage] = useState("");

  async function addHolding(event: React.FormEvent) {
    event.preventDefault();
    const symbol = ticker.trim().toUpperCase();
    if (!symbol || !buyPrice) {
      setMessage("Choose a symbol and enter the price you paid.");
      return;
    }
    const result = await api<{ price: string }>("/api/v1/trades", {
      method: "POST",
      body: JSON.stringify({
        ticker: symbol,
        side: "buy",
        quantity: shares,
        price: buyPrice,
        notes: "Cost basis entered on the portfolio.",
      }),
    });
    setMessage(result.ok ? `${symbol} added at ${result.body?.price ?? buyPrice}.` : result.detail);
    if (result.ok) {
      setTicker("");
      setBuyPrice("");
    }
    reload();
  }

  async function deposit(event: React.FormEvent) {
    event.preventDefault();
    const result = await api<{ cash: string }>("/api/v1/portfolio/cash", {
      method: "POST",
      body: JSON.stringify({ amount: cash }),
    });
    setMessage(result.ok && result.body ? `Cash is now ${result.body.cash}.` : result.detail);
    if (result.ok) setCash("");
    reload();
  }

  if (error || !portfolio) {
    return (
      <div className="space-y-4">
        <PageTitle kicker="Portfolio" title="Portfolio" />
        {error ? <SignInPrompt /> : <p className="text-sm text-muted">Loading positions.</p>}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageTitle
        kicker="Portfolio"
        title={portfolio.name}
        text="Enter the symbol, the shares, and the price you paid. Profit and loss is the last Nasdaq session against that buy price."
      />
      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Equity" value={money(portfolio.equity)} />
        <Stat label="Market value" value={money(portfolio.marketValue)} />
        <Stat label="Cash" value={money(portfolio.cash)} />
        <Stat label="Profit / loss" value={money(portfolio.unrealizedPnl)} tone={tone(portfolio.unrealizedPnl)} />
      </section>
      <form onSubmit={addHolding} className="grid gap-3 border border-line bg-elevated p-4 sm:grid-cols-4">
        <SymbolField value={ticker} onChange={setTicker} placeholder="Symbol or company" />
        <input
          className="border border-line bg-bg px-2 py-1 text-sm"
          inputMode="decimal"
          value={shares}
          onChange={(event) => setShares(event.target.value)}
          aria-label="Shares"
          placeholder="Shares"
        />
        <input
          className="border border-line bg-bg px-2 py-1 text-sm"
          inputMode="decimal"
          value={buyPrice}
          onChange={(event) => setBuyPrice(event.target.value)}
          aria-label="Buy price"
          placeholder="Price you paid"
        />
        <button type="submit" className="border border-line bg-muted-surface px-3 py-1 text-sm">
          Add holding
        </button>
      </form>
      <form onSubmit={deposit} className="flex max-w-md gap-2">
        <input
          className="w-full border border-line bg-bg px-2 py-1 text-sm"
          inputMode="decimal"
          value={cash}
          onChange={(event) => setCash(event.target.value)}
          aria-label="Cash to add"
          placeholder="Cash to add"
        />
        <button type="submit" className="border border-line px-3 py-1 text-sm">
          Add cash
        </button>
      </form>
      {message ? <p className="text-sm">{message}</p> : null}
      <div className="overflow-x-auto border border-line">
        <table className="w-full min-w-[980px] text-left text-sm">
          <thead className="bg-muted-surface text-xs text-muted">
            <tr>
              {["Ticker", "Shares", "Buy", "Last", "Profit / loss", "P&L %", "EPS", "Rating", ""].map((label) => (
                <th key={label} className="px-3 py-2 font-medium">
                  {label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {portfolio.positions.length === 0 ? (
              <tr>
                <td className="px-3 py-4 text-muted" colSpan={9}>
                  No holdings yet. Add a symbol and the price you paid.
                </td>
              </tr>
            ) : null}
            {portfolio.positions.map((row) => (
              <HoldingRow key={row.ticker} row={row} onMessage={setMessage} onReload={reload} />
            ))}
          </tbody>
        </table>
      </div>
      <p className="text-xs leading-5 text-muted">
        EPS is diluted earnings per share from the latest annual SEC filing. Buy, hold, and sell follow Meridian&apos;s
        rules on the last close, that filing, and the moving averages. They are not a broker rating, and they are not a
        promise of profit. Adding shares in a name you already hold updates the average buy price.
      </p>
    </div>
  );
}

function HoldingRow({
  row,
  onMessage,
  onReload,
}: {
  row: PositionRow;
  onMessage: (message: string) => void;
  onReload: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [shares, setShares] = useState(row.quantity);
  const [buyPrice, setBuyPrice] = useState(row.averageCost);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    const result = await api(`/api/v1/portfolio/holdings/${row.ticker}`, {
      method: "PATCH",
      body: JSON.stringify({ quantity: shares, price: buyPrice }),
    });
    onMessage(result.ok ? `${row.ticker} updated.` : result.detail);
    if (result.ok) setEditing(false);
    onReload();
  }

  async function remove() {
    const result = await api(`/api/v1/portfolio/holdings/${row.ticker}`, { method: "DELETE" });
    onMessage(result.ok ? `${row.ticker} removed. Cash was adjusted by the cost basis.` : result.detail);
    onReload();
  }

  return (
    <tr className="border-t border-line">
      <td className="px-3 py-2">
        <Link href={`/stocks/${row.ticker}`} className="num">
          {row.ticker}
        </Link>
        {row.name ? <span className="ml-2 text-muted">{row.name}</span> : null}
      </td>
      <td className="num px-3 py-2">
        {editing ? (
          <input className="w-24 border border-line bg-bg px-2 py-1" value={shares} onChange={(event) => setShares(event.target.value)} aria-label={`${row.ticker} shares`} />
        ) : (
          row.quantity
        )}
      </td>
      <td className="px-3 py-2">
        {editing ? (
          <input className="w-24 border border-line bg-bg px-2 py-1" value={buyPrice} onChange={(event) => setBuyPrice(event.target.value)} aria-label={`${row.ticker} buy price`} />
        ) : (
          <Usd value={row.averageCost} />
        )}
      </td>
      <td className="px-3 py-2">
        <Usd value={row.price} />
      </td>
      <td className="px-3 py-2">
        <MoneyCell value={row.unrealizedPnl} />
      </td>
      <td className={`num px-3 py-2 ${tone(row.unrealizedPnlPercent ?? "0")}`}>
        {row.unrealizedPnlPercent ? `${signed(row.unrealizedPnlPercent)}%` : "—"}
      </td>
      <td className="num px-3 py-2">{row.eps ?? "—"}</td>
      <td className={`px-3 py-2 ${ratingTone(row.rating)}`}>{row.rating ?? "—"}</td>
      <td className="px-3 py-2 text-right">
        {editing ? (
          <form onSubmit={save} className="flex justify-end gap-2">
            <button type="submit" className="text-xs">
              Save
            </button>
            <button type="button" className="text-xs text-muted" onClick={() => setEditing(false)}>
              Cancel
            </button>
          </form>
        ) : (
          <span className="flex justify-end gap-3">
            <button type="button" className="text-xs" onClick={() => setEditing(true)}>
              Edit
            </button>
            <button type="button" className="text-xs text-muted" onClick={remove}>
              Delete
            </button>
          </span>
        )}
      </td>
    </tr>
  );
}

function ratingTone(rating: string | undefined): string {
  if (rating === "Buy") return "text-positive";
  if (rating === "Sell") return "text-negative";
  return "text-muted";
}
