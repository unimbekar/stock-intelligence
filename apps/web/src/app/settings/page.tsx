"use client";

import { useState } from "react";

import { PageTitle, SignInPrompt, useWorkspace } from "@/components/desk";
import { api, type Preference } from "@/lib/client";

export default function SettingsPage() {
  const { workspace, error, reload } = useWorkspace();
  if (error || !workspace) {
    return (
      <div className="space-y-4">
        <PageTitle kicker="Settings" title="Settings" />
        {error ? <SignInPrompt /> : <p className="text-sm text-muted">Loading preferences.</p>}
      </div>
    );
  }
  return <SettingsForm key={workspace.preference.capital} preference={workspace.preference} reload={reload} />;
}

function SettingsForm({ preference, reload }: { preference: Preference; reload: () => void }) {
  const [form, setForm] = useState(preference);
  const [message, setMessage] = useState("");

  async function save(event: React.FormEvent) {
    event.preventDefault();
    const result = await api("/api/v1/preferences", { method: "PATCH", body: JSON.stringify(form) });
    setMessage(result.ok ? "Preferences saved." : result.detail);
    reload();
  }

  return (
    <div className="max-w-xl space-y-6">
      <PageTitle kicker="Settings" title="Settings" text="These limits drive position sizing, ideas, and the risk panel. They do not place orders." />
      <form onSubmit={save} className="space-y-3">
        <Field label="Capital" value={form.capital} onChange={(value) => setForm({ ...form, capital: value })} />
        <Field label="Daily profit target" value={form.dailyProfitTarget} onChange={(value) => setForm({ ...form, dailyProfitTarget: value })} />
        <Field label="Style" value={form.tradingStyle} onChange={(value) => setForm({ ...form, tradingStyle: value })} />
        <Field label="Risk tolerance" value={form.riskTolerance} onChange={(value) => setForm({ ...form, riskTolerance: value })} />
        <Field label="Max position %" value={form.maxPositionPct} onChange={(value) => setForm({ ...form, maxPositionPct: value })} />
        <Field label="Max sector %" value={form.maxSectorPct} onChange={(value) => setForm({ ...form, maxSectorPct: value })} />
        <Field label="Risk per trade %" value={form.maxRiskPerTradePct} onChange={(value) => setForm({ ...form, maxRiskPerTradePct: value })} />
        <Field label="Max daily loss" value={form.maxDailyLoss} onChange={(value) => setForm({ ...form, maxDailyLoss: value })} />
        <label className="block text-sm">
          Goals
          <textarea className="mt-1 w-full border border-line bg-bg px-2 py-1" rows={3} value={form.goals} onChange={(event) => setForm({ ...form, goals: event.target.value })} />
        </label>
        <button type="submit" className="border border-line bg-muted-surface px-3 py-1.5 text-sm">
          Save
        </button>
      </form>
      {message ? <p className="text-sm">{message}</p> : null}
    </div>
  );
}

function Field({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="block text-sm">
      {label}
      <input className="mt-1 w-full border border-line bg-bg px-2 py-1" value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}
