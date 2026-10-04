"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { PageTitle } from "@/components/desk";
import { api } from "@/lib/client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("demo@meridian.local");
  const [password, setPassword] = useState("meridian-demo");
  const [error, setError] = useState("");

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    const result = await api("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    if (!result.ok) {
      setError(result.detail || "Sign-in failed.");
      return;
    }
    router.push("/");
    router.refresh();
  }

  return (
    <div className="max-w-md space-y-6">
      <PageTitle
        kicker="Account"
        title="Sign in"
        text="Sign in with the account stored on this machine. The session stays on this machine."
      />
      <form onSubmit={submit} className="space-y-3 border border-line bg-elevated p-4">
        <label className="block text-sm">
          Email
          <input className="mt-1 w-full border border-line bg-bg px-2 py-1" value={email} onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label className="block text-sm">
          Password
          <input className="mt-1 w-full border border-line bg-bg px-2 py-1" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error ? <p className="text-sm text-negative">{error}</p> : null}
        <button type="submit" className="border border-line bg-muted-surface px-3 py-1.5 text-sm">
          Sign in
        </button>
      </form>
    </div>
  );
}
