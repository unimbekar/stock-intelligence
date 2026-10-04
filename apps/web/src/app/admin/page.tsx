"use client";

import { useEffect, useState } from "react";

import { PageTitle, SignInPrompt } from "@/components/desk";
import { api } from "@/lib/client";

type Summary = {
  users: number;
  actor: string;
  weights: Record<string, number>;
  data: { dataMode: string; source: string; warning: string };
  audit: { action: string; resource: string; createdAt: string }[];
};

const KEYS = [
  "technicalMomentum",
  "fundamentalStrength",
  "analystSentiment",
  "earningsMomentum",
  "valuation",
  "sectorMomentum",
  "riskVolatility",
] as const;

export default function AdminPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [weights, setWeights] = useState<Record<string, string>>({});
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    api<Summary>("/api/v1/admin/summary").then((result) => {
      if (result.status === 401 || result.status === 403) {
        setError(result.status === 401 ? "signin" : result.detail);
        return;
      }
      if (result.body) {
        setSummary(result.body);
        setWeights(Object.fromEntries(Object.entries(result.body.weights).map(([key, value]) => [key, String(value)])));
      }
    });
  }, []);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    const payload = Object.fromEntries(KEYS.map((key) => [key, Number(weights[key] || 0)]));
    const result = await api("/api/v1/admin/weights", { method: "PUT", body: JSON.stringify(payload) });
    setMessage(result.ok ? "Weights saved." : result.detail);
  }

  if (error === "signin") {
    return (
      <div className="space-y-4">
        <PageTitle kicker="Admin" title="Admin" />
        <SignInPrompt />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <PageTitle kicker="Admin" title="Admin" text="Local operator view. Scoring weights apply to ideas and the scanner." />
      {error ? <p className="text-sm text-negative">{error}</p> : null}
      {summary ? (
        <section className="border border-line p-4 text-sm">
          <p>
            {summary.users} user accounts. Signed in as {summary.actor}. Data: {summary.data.dataMode} ({summary.data.source}).
          </p>
          {summary.data.warning ? <p className="mt-2 text-muted">{summary.data.warning}</p> : null}
          <ul className="mt-3 space-y-1 text-muted">
            {summary.audit.map((row) => (
              <li key={`${row.createdAt}-${row.action}`}>
                {row.createdAt} · {row.action} {row.resource}
              </li>
            ))}
          </ul>
        </section>
      ) : null}
      <form onSubmit={save} className="grid gap-2 sm:grid-cols-2">
        {KEYS.map((key) => (
          <label key={key} className="text-sm">
            {key}
            <input
              className="mt-1 w-full border border-line bg-bg px-2 py-1"
              value={weights[key] ?? ""}
              placeholder="0.00"
              onChange={(event) => setWeights({ ...weights, [key]: event.target.value })}
            />
          </label>
        ))}
        <button type="submit" className="border border-line bg-muted-surface px-3 py-1.5 text-sm sm:col-span-2">
          Save weights
        </button>
      </form>
      {message ? <p className="text-sm">{message}</p> : null}
    </div>
  );
}
