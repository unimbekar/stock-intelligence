"use client";

import { useState } from "react";

import { Notice, PageTitle, SignInPrompt, useWorkspace } from "@/components/desk";
import { SymbolField } from "@/components/symbol-field";
import { api } from "@/lib/client";

export default function DeskPage() {
  const { workspace, error, reload } = useWorkspace();
  const [ticker, setTicker] = useState("NVDA");
  const [side, setSide] = useState("buy");
  const [quantity, setQuantity] = useState("1");
  const [message, setMessage] = useState("");
  const [plan, setPlan] = useState<Record<string, string | null> | null>(null);
  const [entry, setEntry] = useState("200");
  const [stop, setStop] = useState("195");
  const [target, setTarget] = useState("215");

  async function place(event: React.FormEvent) {
    event.preventDefault();
    const result = await api<{ price: string; cash: string }>("/api/v1/trades", {
      method: "POST",
      body: JSON.stringify({ ticker, side, quantity }),
    });
    setMessage(result.ok && result.body ? `Filled at ${result.body.price}. Cash ${result.body.cash}.` : result.detail);
    reload();
  }

  async function size(event: React.FormEvent) {
    event.preventDefault();
    const account = workspace?.preference.capital ?? "50000";
    const riskPercent = workspace?.preference.maxRiskPerTradePct ?? "1";
    const result = await api<Record<string, string | null>>("/api/v1/position-size", {
      method: "POST",
      body: JSON.stringify({ account, riskPercent, entry, stop, target }),
    });
    if (!result.ok || !result.body) {
      setMessage(result.detail);
      setPlan(null);
      return;
    }
    setPlan(result.body);
  }

  if (error) {
    return (
      <div className="space-y-4">
        <PageTitle kicker="Desk" title="Trading Desk" />
        <SignInPrompt />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageTitle
        kicker="Desk"
        title="Trading Desk"
        text="Paper orders update cash and the ledger in one step. The fill price is the connected last price unless you are sizing a hypothetical stop."
      />
      <form onSubmit={place} className="grid gap-3 border border-line bg-elevated p-4 sm:grid-cols-4">
        <SymbolField value={ticker} onChange={setTicker} />
        <select className="border border-line bg-bg px-2 py-1 text-sm" value={side} onChange={(event) => setSide(event.target.value)}>
          {["buy", "sell", "short", "cover"].map((item) => (
            <option key={item}>{item}</option>
          ))}
        </select>
        <input className="border border-line bg-bg px-2 py-1 text-sm" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
        <button type="submit" className="border border-line bg-muted-surface px-3 py-1 text-sm">
          Place paper order
        </button>
      </form>
      <form onSubmit={size} className="grid gap-3 border border-line p-4 sm:grid-cols-4">
        <label className="text-sm">
          Entry
          <input className="mt-1 w-full border border-line bg-bg px-2 py-1" value={entry} onChange={(event) => setEntry(event.target.value)} />
        </label>
        <label className="text-sm">
          Stop
          <input className="mt-1 w-full border border-line bg-bg px-2 py-1" value={stop} onChange={(event) => setStop(event.target.value)} />
        </label>
        <label className="text-sm">
          Target
          <input className="mt-1 w-full border border-line bg-bg px-2 py-1" value={target} onChange={(event) => setTarget(event.target.value)} />
        </label>
        <button type="submit" className="self-end border border-line px-3 py-1 text-sm">
          Size position
        </button>
      </form>
      {plan ? (
        <Notice
          text={`${plan.shares} shares, value ${plan.positionValue}, max loss ${plan.maxRisk}, risk/reward ${plan.riskReward ?? "n/a"}. ${plan.note ?? ""}`}
        />
      ) : null}
      {message ? <p className="text-sm">{message}</p> : null}
      <section>
        <h2 className="text-sm font-medium">Fills</h2>
        <ul className="mt-2 divide-y divide-line border border-line text-sm">
          {workspace?.portfolio?.transactions.map((row) => (
            <li key={row.id} className="flex justify-between px-3 py-2">
              <span>
                {row.side} {row.quantity} {row.ticker}
              </span>
              <span className="num">{row.price}</span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
