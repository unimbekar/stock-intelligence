"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { PageTitle, SignInPrompt, useWorkspace } from "@/components/desk";
import { api } from "@/lib/client";

export default function OnboardingPage() {
  const router = useRouter();
  const { workspace, error } = useWorkspace();
  const [capital, setCapital] = useState("50000");
  const [target, setTarget] = useState("2000");
  const [style, setStyle] = useState("swing");
  const [risk, setRisk] = useState("moderate");
  const [goals, setGoals] = useState("Practice a paper process. The daily target is a stress test, not a forecast.");
  const [message, setMessage] = useState("");

  async function save(event: React.FormEvent) {
    event.preventDefault();
    if (!workspace) return;
    const result = await api("/api/v1/preferences", {
      method: "PATCH",
      body: JSON.stringify({
        ...workspace.preference,
        capital,
        dailyProfitTarget: target,
        tradingStyle: style,
        riskTolerance: risk,
        goals,
        onboardingCompleted: true,
      }),
    });
    if (!result.ok) {
      setMessage(result.detail);
      return;
    }
    router.push("/");
  }

  if (error) {
    return (
      <div className="space-y-4">
        <PageTitle kicker="Start" title="Onboarding" />
        <SignInPrompt />
      </div>
    );
  }

  return (
    <div className="max-w-xl space-y-6">
      <PageTitle
        kicker="Start"
        title="Onboarding"
        text="Set the paper account and the risk limits. A 4% daily objective on $50,000 is $2,000. That figure is not a promise."
      />
      <form onSubmit={save} className="space-y-3">
        <label className="block text-sm">
          Capital
          <input className="mt-1 w-full border border-line bg-bg px-2 py-1" value={capital} onChange={(event) => setCapital(event.target.value)} />
        </label>
        <label className="block text-sm">
          Daily profit target
          <input className="mt-1 w-full border border-line bg-bg px-2 py-1" value={target} onChange={(event) => setTarget(event.target.value)} />
        </label>
        <label className="block text-sm">
          Style
          <select className="mt-1 w-full border border-line bg-bg px-2 py-1" value={style} onChange={(event) => setStyle(event.target.value)}>
            {["day", "swing", "short", "long"].map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          Risk
          <select className="mt-1 w-full border border-line bg-bg px-2 py-1" value={risk} onChange={(event) => setRisk(event.target.value)}>
            {["conservative", "moderate", "aggressive"].map((item) => (
              <option key={item}>{item}</option>
            ))}
          </select>
        </label>
        <label className="block text-sm">
          Goals
          <textarea className="mt-1 w-full border border-line bg-bg px-2 py-1" rows={3} value={goals} onChange={(event) => setGoals(event.target.value)} />
        </label>
        <button type="submit" className="border border-line bg-muted-surface px-3 py-1.5 text-sm">
          Save and open the desk
        </button>
      </form>
      {message ? <p className="text-sm text-negative">{message}</p> : null}
    </div>
  );
}
