"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { MoneyCell, PageTitle, SignInPrompt, Stat, Usd, tone, useWorkspace } from "@/components/desk";
import { SymbolField } from "@/components/symbol-field";
import { api, type PositionRow } from "@/lib/client";
import { compact, money, signed } from "@/lib/format";

export default function PortfolioPage() {
  const { workspace, error, reload } = useWorkspace();
  const portfolio = workspace?.portfolio;
  const [ticker, setTicker] = useState("");
  const [shares, setShares] = useState("10");
  const [buyPrice, setBuyPrice] = useState("");
  const [cash, setCash] = useState("");
  const [message, setMessage] = useState("");
  const [columns, setColumns] = useState<ColumnId[]>(DEFAULT_COLUMNS);

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
      <div className="border border-line">
        <div className="flex items-center justify-end border-b border-line bg-muted-surface px-2 py-1">
          <ColumnMenu columns={columns} onChange={setColumns} />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[980px] text-left text-sm">
            <thead className="text-xs text-muted">
              <tr>
                {BASE_HEADERS.map((label) => (
                  <th key={label} className="px-3 py-2 font-medium">
                    {label}
                  </th>
                ))}
                {columns.map((id) => (
                  <th key={id} className="px-3 py-2 font-medium">
                    {COLUMN_LABEL[id]}
                  </th>
                ))}
                <th className="px-3 py-2 font-medium" />
              </tr>
            </thead>
            <tbody>
              {portfolio.positions.length === 0 ? (
                <tr>
                  <td className="px-3 py-4 text-muted" colSpan={BASE_HEADERS.length + columns.length + 1}>
                    No holdings yet. Add a symbol and the price you paid.
                  </td>
                </tr>
              ) : null}
              {portfolio.positions.map((row) => (
                <HoldingRow key={row.ticker} row={row} columns={columns} onMessage={setMessage} onReload={reload} />
              ))}
            </tbody>
          </table>
        </div>
      </div>
      <p className="text-xs leading-5 text-muted">
        EPS is diluted earnings per share from the latest annual SEC filing. Support is the lowest low of the last 20
        sessions, and resistance is the highest high. Buy, hold, and sell follow Meridian&apos;s rules on the last
        close, that filing, and the moving averages. They are not a broker rating, and they are not a promise of
        profit. Adding shares in a name you already hold updates the average buy price.
      </p>
    </div>
  );
}

function HoldingRow({
  row,
  columns,
  onMessage,
  onReload,
}: {
  row: PositionRow;
  columns: ColumnId[];
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
      {columns.map((id) => (
        <td key={id} className={`px-3 py-2 ${id === "sector" ? "" : "num"}`}>
          {columnValue(row, id)}
        </td>
      ))}
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

const COLUMN_LABEL = {
  support: "Support",
  resistance: "Resistance",
  rsi: "RSI",
  sma20: "SMA 20",
  sma50: "SMA 50",
  atr: "ATR",
  volume: "Volume",
  relativeVolume: "Rel. volume",
  sector: "Sector",
  dailyPnl: "Day P&L",
  weight: "Weight",
} as const;

type ColumnId = keyof typeof COLUMN_LABEL;

const BASE_HEADERS = ["Ticker", "Shares", "Buy", "Last", "Profit / loss", "P&L %", "EPS", "Rating"];
const DEFAULT_COLUMNS: ColumnId[] = ["support", "resistance"];
const COLUMN_KEY = "meridian-portfolio-columns";

function ColumnMenu({ columns, onChange }: { columns: ColumnId[]; onChange: (columns: ColumnId[]) => void }) {
  const [open, setOpen] = useState(false);
  const panel = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const stored = window.localStorage.getItem(COLUMN_KEY);
    if (!stored) return;
    try {
      const parsed = JSON.parse(stored) as string[];
      const known = parsed.filter((id): id is ColumnId => id in COLUMN_LABEL);
      onChange(known);
    } catch {
      window.localStorage.removeItem(COLUMN_KEY);
    }
  }, [onChange]);

  useEffect(() => {
    if (!open) return;
    function close(event: MouseEvent) {
      if (!panel.current?.contains(event.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, [open]);

  function toggle(id: ColumnId) {
    const next = columns.includes(id) ? columns.filter((item) => item !== id) : [...columns, id];
    onChange(next);
    window.localStorage.setItem(COLUMN_KEY, JSON.stringify(next));
  }

  return (
    <div className="relative" ref={panel}>
      <button
        type="button"
        className="border border-line bg-bg p-1.5 text-ink"
        aria-label="Add columns"
        aria-expanded={open}
        onClick={() => setOpen((value) => !value)}
      >
        <ColumnsIcon />
      </button>
      {open ? (
        <fieldset className="absolute right-0 z-20 mt-1 w-52 border border-line bg-elevated p-3 text-sm shadow-none">
          <legend className="px-1 text-xs text-muted">Columns</legend>
          <ul className="space-y-2">
            {(Object.keys(COLUMN_LABEL) as ColumnId[]).map((id) => (
              <li key={id}>
                <label className="flex items-center gap-2">
                  <input type="checkbox" checked={columns.includes(id)} onChange={() => toggle(id)} />
                  {COLUMN_LABEL[id]}
                </label>
              </li>
            ))}
          </ul>
        </fieldset>
      ) : null}
    </div>
  );
}

function ColumnsIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" aria-hidden="true">
      <rect x="1" y="2" width="3.2" height="12" fill="none" stroke="currentColor" />
      <rect x="6.4" y="2" width="3.2" height="12" fill="none" stroke="currentColor" />
      <rect x="11.8" y="2" width="3.2" height="12" fill="none" stroke="currentColor" />
    </svg>
  );
}

function columnValue(row: PositionRow, id: ColumnId) {
  if (id === "support") return row.support ? <Usd value={row.support} /> : "—";
  if (id === "resistance") return row.resistance ? <Usd value={row.resistance} /> : "—";
  if (id === "sma20") return row.sma20 ? <Usd value={row.sma20} /> : "—";
  if (id === "sma50") return row.sma50 ? <Usd value={row.sma50} /> : "—";
  if (id === "atr") return row.atr ? <Usd value={row.atr} /> : "—";
  if (id === "dailyPnl") return <MoneyCell value={row.dailyPnl} />;
  if (id === "weight") return row.weightPercent ? `${row.weightPercent}%` : "—";
  if (id === "volume") return row.volume == null ? "—" : compact(row.volume);
  if (id === "sector") return row.sector || "—";
  if (id === "rsi") return row.rsi || "—";
  if (id === "relativeVolume") return row.relativeVolume || "—";
  return "—";
}

function ratingTone(rating: string | undefined): string {
  if (rating === "Buy") return "text-positive";
  if (rating === "Sell") return "text-negative";
  return "text-muted";
}
