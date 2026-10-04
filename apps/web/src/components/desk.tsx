"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { loadWorkspace, type Workspace } from "@/lib/client";
import { money, signed } from "@/lib/format";

export function useWorkspace() {
  const [tick, setTick] = useState(0);
  const [state, setState] = useState<{ loading: boolean; workspace: Workspace | null; error: string }>({
    loading: true,
    workspace: null,
    error: "",
  });

  useEffect(() => {
    let cancelled = false;
    loadWorkspace()
      .then((result) => {
        if (cancelled) return;
        if (result.status === 401) {
          setState({ loading: false, workspace: null, error: "Sign in to load your paper account." });
          return;
        }
        if (!result.ok || !result.body) {
          setState({ loading: false, workspace: null, error: result.detail || "The workspace could not be loaded." });
          return;
        }
        setState({ loading: false, workspace: result.body, error: "" });
      })
      .catch(() => {
        if (!cancelled) setState({ loading: false, workspace: null, error: "The API is not reachable." });
      });
    return () => {
      cancelled = true;
    };
  }, [tick]);

  return { ...state, reload: () => setTick((value) => value + 1) };
}

export function PageTitle({ kicker, title, text }: { kicker: string; title: string; text?: string }) {
  return (
    <div>
      <p className="text-[11px] tracking-[0.18em] text-muted uppercase">{kicker}</p>
      <h1 className="mt-2 text-3xl font-medium tracking-tight">{title}</h1>
      {text ? <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">{text}</p> : null}
    </div>
  );
}

export function Stat({ label, value, tone }: { label: string; value: string; tone?: string }) {
  return (
    <article className="border border-line bg-elevated px-4 py-3">
      <h2 className="text-xs text-muted">{label}</h2>
      <p className={`num mt-2 text-2xl ${tone ?? ""}`}>{value}</p>
    </article>
  );
}

export function tone(value: string | number): string {
  const amount = Number(value);
  if (amount > 0) return "text-positive";
  if (amount < 0) return "text-negative";
  return "text-muted";
}

export function Notice({ text }: { text: string }) {
  if (!text) return null;
  return <p className="border border-line bg-elevated px-4 py-3 text-sm leading-6">{text}</p>;
}

export function SignInPrompt() {
  return (
    <p className="text-sm text-muted">
      <Link href="/login" className="text-accent underline">
        Sign in
      </Link>{" "}
      with the local account to use this desk.
    </p>
  );
}

export function MoneyCell({ value }: { value: string }) {
  return <span className={`num ${tone(value)}`}>{signed(value)}</span>;
}

export function Usd({ value }: { value: string }) {
  return <span className="num">{money(value)}</span>;
}
