"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { PageTitle, SignInPrompt, tone, useWorkspace } from "@/components/desk";
import { SymbolField } from "@/components/symbol-field";
import { api, type AlertRow } from "@/lib/client";
import { money, signed } from "@/lib/format";

type LiveQuote = { price: string; changePercent: string; name?: string };

export default function AlertsPage() {
  const { workspace, error, reload } = useWorkspace();
  const [ticker, setTicker] = useState("NVDA");
  const [alertType, setAlertType] = useState("price");
  const [direction, setDirection] = useState("above");
  const [level, setLevel] = useState("200");
  const [emailOn, setEmailOn] = useState(true);
  const [editing, setEditing] = useState("");
  const [message, setMessage] = useState("");
  const [address, setAddress] = useState("");
  const [quote, setQuote] = useState<LiveQuote | null>(null);

  useEffect(() => {
    if (workspace?.mail) setAddress(workspace.mail.address);
  }, [workspace?.mail]);

  useEffect(() => {
    const symbol = ticker.trim().toUpperCase();
    if (!/^[A-Z.]{1,6}$/.test(symbol)) {
      setQuote(null);
      return;
    }
    const handle = window.setTimeout(() => {
      fetch(`/api/v1/market/quotes/${encodeURIComponent(symbol)}`)
        .then((response) => (response.ok ? response.json() : null))
        .then((body: LiveQuote | null) => setQuote(body))
        .catch(() => setQuote(null));
    }, 250);
    return () => window.clearTimeout(handle);
  }, [ticker]);

  function paramsFor() {
    const email = emailOn;
    if (alertType === "price") return { direction, price: Number(level), email };
    if (alertType === "percent") return { direction, percent: Number(level), email };
    if (alertType === "rsi") return { direction, level: Number(level), email };
    return { relativeVolume: Number(level), email };
  }

  async function create(event: React.FormEvent) {
    event.preventDefault();
    const payload = { ticker, alertType, params: paramsFor(), enabled: true };
    const result = editing
      ? await api(`/api/v1/alerts/${editing}`, { method: "PATCH", body: JSON.stringify(payload) })
      : await api("/api/v1/alerts", { method: "POST", body: JSON.stringify(payload) });
    setMessage(result.ok ? (editing ? "Alert updated." : "Alert saved.") : result.detail);
    if (result.ok) setEditing("");
    reload();
  }

  async function saveAddress(event: React.FormEvent) {
    event.preventDefault();
    const result = await api<{ address: string }>("/api/v1/alerts/destination", {
      method: "PATCH",
      body: JSON.stringify({ email: address }),
    });
    setMessage(result.ok ? "Email address saved." : result.detail);
    reload();
  }

  async function sendTest() {
    const result = await api("/api/v1/alerts/test-email", { method: "POST" });
    setMessage(result.ok ? "Test email sent." : result.detail);
  }

  if (error) {
    return (
      <div className="space-y-4">
        <PageTitle kicker="Alerts" title="Alerts" />
        <SignInPrompt />
      </div>
    );
  }

  const target = quote && alertType === "percent" ? projected(quote.price, level, direction) : null;

  return (
    <div className="space-y-6">
      <PageTitle
        kicker="Alerts"
        title="Alerts"
        text="Each row shows the last Nasdaq close. Set a dollar price, or a percent above or below the close you see when you save. One email goes out when that close crosses the level, and again only after the price moves back."
      />
      <form onSubmit={saveAddress} className="space-y-3 border border-line bg-elevated p-4">
        <label className="block text-sm">
          Email address
          <input
            className="mt-1 w-full border border-line bg-bg px-2 py-1"
            type="email"
            value={address}
            placeholder="you@example.com"
            onChange={(event) => setAddress(event.target.value)}
          />
        </label>
        <div className="flex flex-wrap gap-2">
          <button type="submit" className="border border-line px-3 py-1 text-sm">
            Save address
          </button>
          <button type="button" className="border border-line px-3 py-1 text-sm" onClick={sendTest}>
            Send test email
          </button>
        </div>
        <p className="text-sm text-muted">
          {workspace?.mail.configured
            ? "Mail is configured. A triggered alert sends one message to this address."
            : "Save the address here. To send mail, set SMTP_HOST, SMTP_FROM, and SMTP_PASSWORD in the API environment, then restart the API."}
        </p>
      </form>
      <form onSubmit={create} className="space-y-3 border border-line bg-elevated p-4">
        <div className="grid gap-3 sm:grid-cols-2">
          <SymbolField value={ticker} onChange={setTicker} />
          <p className="self-center text-sm">
            Last price{" "}
            {quote ? (
              <>
                <span className="num">{money(quote.price)}</span>{" "}
                <span className={tone(quote.changePercent)}>{signed(quote.changePercent)}%</span>
              </>
            ) : (
              <span className="text-muted">waiting for a listed symbol</span>
            )}
          </p>
        </div>
        <div className="grid gap-2 sm:grid-cols-4">
          <select
            className="border border-line bg-bg px-2 py-1 text-sm"
            value={alertType}
            onChange={(event) => {
              const next = event.target.value;
              setAlertType(next);
              if (next === "percent") setLevel("5");
              if (next === "price") setLevel("200");
            }}
          >
            <option value="price">Price</option>
            <option value="percent">Percent</option>
            <option value="rsi">RSI</option>
            <option value="volume">Relative volume</option>
          </select>
          {alertType === "volume" ? (
            <span />
          ) : (
            <select className="border border-line bg-bg px-2 py-1 text-sm" value={direction} onChange={(event) => setDirection(event.target.value)}>
              <option value="above">Above</option>
              <option value="below">Below</option>
            </select>
          )}
          <input
            className="border border-line bg-bg px-2 py-1 text-sm"
            value={level}
            aria-label={levelName(alertType)}
            onChange={(event) => setLevel(event.target.value)}
          />
          <button type="submit" className="border border-line px-3 py-1 text-sm">
            {editing ? "Update alert" : "Add alert"}
          </button>
        </div>
        {target ? (
          <p className="text-sm text-muted">
            {level}% {direction} {money(quote?.price ?? "0")} is {money(target)}.
          </p>
        ) : null}
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={emailOn} onChange={(event) => setEmailOn(event.target.checked)} />
          Email me when this triggers
        </label>
        {editing ? (
          <button
            type="button"
            className="text-sm text-muted"
            onClick={() => {
              setEditing("");
              setEmailOn(true);
            }}
          >
            Cancel edit
          </button>
        ) : null}
      </form>
      {message ? <p className="text-sm">{message}</p> : null}
      <ul className="divide-y divide-line border border-line text-sm">
        {workspace?.alerts.map((alert) => (
          <AlertLine
            key={alert.id}
            alert={alert}
            onEdit={() => {
              const params = alert.params;
              setEditing(alert.id);
              setTicker(alert.ticker ?? "");
              setAlertType(alert.alertType);
              setDirection(String(params.direction ?? "above"));
              setEmailOn(alert.email);
              const value = params.percent ?? params.price ?? params.level ?? params.relativeVolume ?? "";
              setLevel(String(value));
            }}
            onReload={reload}
          />
        ))}
      </ul>
    </div>
  );
}

function AlertLine({ alert, onEdit, onReload }: { alert: AlertRow; onEdit: () => void; onReload: () => void }) {
  return (
    <li className="flex flex-wrap items-center justify-between gap-3 px-3 py-3">
      <div>
        <p>
          {alert.ticker ? (
            <Link href={`/stocks/${alert.ticker}`} className="num">
              {alert.ticker}
            </Link>
          ) : (
            "—"
          )}{" "}
          <span className="num">{alert.price ? money(alert.price) : "—"}</span>{" "}
          {alert.changePercent ? <span className={tone(alert.changePercent)}>{signed(alert.changePercent)}%</span> : null}
        </p>
        <p className="mt-1 text-muted">{describe(alert)}</p>
      </div>
      <span className={alert.triggered ? "text-warning" : "text-muted"}>{statusLabel(alert)}</span>
      <span className="flex gap-3">
        <button type="button" className="text-xs" onClick={onEdit}>
          Edit
        </button>
        <button type="button" className="text-xs" onClick={() => api(`/api/v1/alerts/${alert.id}`, { method: "PATCH", body: "{}" }).then(onReload)}>
          Toggle
        </button>
        <button type="button" className="text-xs text-muted" onClick={() => api(`/api/v1/alerts/${alert.id}`, { method: "DELETE" }).then(onReload)}>
          Delete
        </button>
      </span>
    </li>
  );
}

function describe(alert: AlertRow): string {
  const params = alert.params;
  const direction = String(params.direction ?? "above");
  if (alert.alertType === "percent") {
    return `${params.percent}% ${direction} ${money(String(params.basis ?? "0"))} → ${money(String(params.target ?? "0"))}`;
  }
  if (alert.alertType === "price") return `Price ${direction} ${money(String(params.price ?? "0"))}`;
  if (alert.alertType === "rsi") return `RSI ${direction} ${params.level}`;
  return `Relative volume at or above ${params.relativeVolume}`;
}

function statusLabel(alert: AlertRow): string {
  if (!alert.enabled) return "Off";
  if (!alert.triggered) return alert.email ? "Watching · email on" : "Watching";
  if (alert.email && alert.notified) return "Triggered · email sent";
  if (alert.email) return "Triggered · email waiting";
  return "Triggered";
}

function levelName(alertType: string): string {
  if (alertType === "percent") return "Percent";
  if (alertType === "price") return "Price";
  if (alertType === "rsi") return "RSI";
  return "Relative volume";
}

function projected(price: string, percent: string, direction: string): string | null {
  const basis = Number(price);
  const move = Number(percent);
  if (!basis || !move || move <= 0 || move > 90) return null;
  const sign = direction === "below" ? -1 : 1;
  return (basis * (1 + (sign * move) / 100)).toFixed(2);
}
