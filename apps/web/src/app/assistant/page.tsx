"use client";

import { useState } from "react";

import { PageTitle, SignInPrompt } from "@/components/desk";
import { api } from "@/lib/client";

type Answer = { content: string; model: string; usedTools: string[]; disclaimer: string };

export default function AssistantPage() {
  const [question, setQuestion] = useState("What is the latest NVDA quote and RSI?");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);

  async function ask(event: React.FormEvent) {
    event.preventDefault();
    setPending(true);
    setError("");
    const result = await api<Answer>("/api/v1/assistant", {
      method: "POST",
      body: JSON.stringify({ question }),
    });
    if (result.status === 401) {
      setError("signin");
      return;
    }
    if (!result.ok || !result.body) {
      setError(result.detail || "The assistant did not respond.");
      return;
    }
    setPending(false);
    setAnswer(result.body);
  }

  return (
    <div className="space-y-6">
      <PageTitle
        kicker="Assistant"
        title="AI Assistant"
        text="Qwen reads the Nasdaq session, SEC filings, and your paper account for the company you name. Missing figures stay missing."
      />
      <form onSubmit={ask} className="space-y-3">
        <textarea className="w-full border border-line bg-bg px-3 py-2 text-sm" rows={4} value={question} onChange={(event) => setQuestion(event.target.value)} />
        <button type="submit" disabled={pending} className="border border-line bg-muted-surface px-3 py-1.5 text-sm">
          {pending ? "Reading records…" : "Ask"}
        </button>
      </form>
      {pending ? (
        <p className="text-sm text-muted">The first answer loads Qwen 3.6 on this machine. Later answers are faster.</p>
      ) : null}
      {error === "signin" ? <SignInPrompt /> : null}
      {error && error !== "signin" ? <p className="text-sm text-negative">{error}</p> : null}
      {answer ? (
        <article className="border border-line bg-elevated p-4 text-sm leading-6">
          <p className="text-xs text-muted">
            {answer.model} · {answer.usedTools.join(", ")}
          </p>
          <pre className="mt-3 whitespace-pre-wrap font-sans">{answer.content}</pre>
          <p className="mt-3 text-xs text-muted">{answer.disclaimer}</p>
        </article>
      ) : null}
    </div>
  );
}
