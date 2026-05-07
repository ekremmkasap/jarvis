"use client";

import { useEffect, useState } from "react";

const PERSONAS = [
  { id: "seda", label: "Seda (forge)" },
  { id: "mert", label: "Mert (nexus)" },
  { id: "buse", label: "Buse (spark)" },
  { id: "eren", label: "Eren (spark)" },
  { id: "sabri", label: "Sabri (atlas)" },
  { id: "luna", label: "Luna (shield)" },
  { id: "sabrican", label: "Sabrican (nexus)" },
];

export default function SwarmTeamPanel() {
  const [goal, setGoal] = useState("");
  const [selected, setSelected] = useState<string[]>(["seda", "mert"]);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<string>("");
  const [activeAgents, setActiveAgents] = useState<string[]>([]);

  useEffect(() => {
    let mounted = true;
    const poll = async () => {
      try {
        const r = await fetch("/api/swarm-status");
        if (!r.ok) return;
        const j = await r.json();
        const active = Array.isArray(j.active) ? j.active : Array.isArray(j.active_agents) ? j.active_agents : [];
        if (mounted) setActiveAgents(active.map((a: any) => String(a).toLowerCase()));
      } catch {}
    };
    poll();
    const id = setInterval(poll, 4000);
    return () => { mounted = false; clearInterval(id); };
  }, []);

  const toggle = (id: string) => {
    setSelected((s) => s.includes(id) ? s.filter(x => x !== id) : [...s, id]);
  };

  const dispatch = async () => {
    if (!goal.trim() || selected.length === 0) return;
    setBusy(true);
    setResult("");
    try {
      const r = await fetch("/api/swarm/team-dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal, personas: selected }),
      });
      const j = await r.json();
      setResult(j.ok ? String(j.result || "") : `ERROR: ${j.error}`);
    } catch (e: any) {
      setResult(`ERROR: ${e?.message || e}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-lg border border-neutral-700 bg-neutral-900/60 p-4">
      <h3 className="text-sm font-semibold text-neutral-200 mb-3">Swarm Team Dispatch</h3>
      <textarea
        value={goal}
        onChange={(e) => setGoal(e.target.value)}
        placeholder="Hedef (örn: e-ticaret trendi araştır ve strateji çıkar)"
        className="w-full rounded border border-neutral-700 bg-neutral-950 p-2 text-sm text-neutral-200 mb-2"
        rows={2}
      />
      <div className="grid grid-cols-2 gap-1 mb-3">
        {PERSONAS.map((p) => {
          const isActive = activeAgents.includes(p.id);
          const isSel = selected.includes(p.id);
          return (
            <label
              key={p.id}
              className={`flex items-center gap-2 text-xs px-2 py-1 rounded cursor-pointer ${
                isSel ? "bg-emerald-500/20 text-emerald-300" : "bg-neutral-800 text-neutral-400"
              }`}
            >
              <input
                type="checkbox"
                checked={isSel}
                onChange={() => toggle(p.id)}
                className="accent-emerald-500"
              />
              <span>{p.label}</span>
              {isActive && <span className="ml-auto text-emerald-400">●</span>}
            </label>
          );
        })}
      </div>
      <button
        onClick={dispatch}
        disabled={busy || !goal.trim() || selected.length === 0}
        className="w-full rounded bg-emerald-600 hover:bg-emerald-500 disabled:bg-neutral-700 disabled:text-neutral-500 text-white text-sm py-2 font-medium"
      >
        {busy ? "Dispatching..." : `Dispatch (${selected.length} persona)`}
      </button>
      {result && (
        <pre className="mt-3 max-h-60 overflow-auto text-xs text-neutral-300 whitespace-pre-wrap bg-neutral-950 p-2 rounded border border-neutral-800">
          {result}
        </pre>
      )}
    </div>
  );
}
