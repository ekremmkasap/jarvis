"use client";

import { useState } from "react";

type ActionState = {
  tone: "idle" | "success" | "error";
  message: string;
};

const initialState: ActionState = {
  tone: "idle",
  message: ""
};

export function AdminQuickActions() {
  const [isLoading, setIsLoading] = useState(false);
  const [state, setState] = useState<ActionState>(initialState);

  async function handleStripeTest() {
    setIsLoading(true);
    setState(initialState);

    try {
      const response = await fetch("/api/admin/stripe-test", {
        method: "POST",
        cache: "no-store"
      });
      const body = (await response.json().catch(() => ({}))) as { message?: string; error?: string };
      if (!response.ok) {
        throw new Error(body.error || "Stripe test webhook gonderilemedi.");
      }
      setState({
        tone: "success",
        message: body.message || "Stripe test webhook gonderildi."
      });
    } catch (error) {
      setState({
        tone: "error",
        message: error instanceof Error ? error.message : "Bilinmeyen bir hata olustu."
      });
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <div className="space-y-4">
      <button
        type="button"
        onClick={handleStripeTest}
        disabled={isLoading}
        className="rounded-full bg-emerald-400 px-5 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:bg-emerald-400/60"
      >
        {isLoading ? "Gonderiliyor..." : "Stripe Test Webhook Gonder"}
      </button>

      <div className="flex flex-wrap gap-3 text-sm">
        <a
          href="/codex-accounts"
          className="rounded-full border border-emerald-400/30 px-4 py-2 text-emerald-100 transition hover:border-emerald-300 hover:bg-emerald-400/10"
        >
          Codex Accounts
        </a>
        <a
          href="/ops"
          className="rounded-full border border-cyan-400/30 px-4 py-2 text-cyan-100 transition hover:border-cyan-300 hover:bg-cyan-400/10"
        >
          Live Ops
        </a>
        <a
          href="/api/admin/stats"
          target="_blank"
          className="rounded-full border border-slate-700 px-4 py-2 text-slate-200 transition hover:border-slate-500 hover:bg-slate-900"
          rel="noreferrer"
        >
          Stats JSON
        </a>
        <a
          href="/api/admin/health"
          target="_blank"
          className="rounded-full border border-slate-700 px-4 py-2 text-slate-200 transition hover:border-slate-500 hover:bg-slate-900"
          rel="noreferrer"
        >
          Health JSON
        </a>
      </div>

      {state.message ? (
        <div
          className={`rounded-2xl border px-4 py-3 text-sm ${
            state.tone === "success"
              ? "border-emerald-400/30 bg-emerald-400/10 text-emerald-100"
              : "border-rose-400/30 bg-rose-400/10 text-rose-100"
          }`}
        >
          {state.message}
        </div>
      ) : null}
    </div>
  );
}
