"use client";

import { useEffect, useState } from "react";

interface MrrRow {
  date: string;
  mrr_usd: number;
  customer_count?: number;
}

interface SaasMetricsData {
  ok: boolean;
  current: { mrr_usd?: number; customer_count?: number; churn_rate?: number; plan?: string };
  trend_30d: MrrRow[];
  customer_count: number;
  metrics?: { arpu?: number; ltv?: number };
}

export default function SaasMetricsPanel() {
  const [data, setData] = useState<SaasMetricsData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetchData = async () => {
      try {
        const res = await fetch("/api/saas-metrics");
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const json = await res.json();
        if (mounted) {
          setData(json);
          setError(null);
        }
      } catch (e: any) {
        if (mounted) setError(String(e?.message || e));
      }
    };
    fetchData();
    const id = setInterval(fetchData, 60000);
    return () => {
      mounted = false;
      clearInterval(id);
    };
  }, []);

  if (error) {
    return (
      <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-4 text-red-300">
        SaaS metrics error: {error}
      </div>
    );
  }
  if (!data) return <div className="text-neutral-400 p-4">Loading SaaS metrics...</div>;

  const mrr = data.current?.mrr_usd ?? 0;
  const customers = data.customer_count ?? 0;
  const arpu = data.metrics?.arpu ?? 0;
  const trend = data.trend_30d ?? [];
  const max = Math.max(1, ...trend.map((r) => r.mrr_usd || 0));

  return (
    <div className="rounded-lg border border-neutral-700 bg-neutral-900/60 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-neutral-200">SaaS Metrics</h3>
        <span className="text-xs text-neutral-500">60s polling</span>
      </div>
      <div className="grid grid-cols-3 gap-3 mb-3">
        <div>
          <div className="text-xs text-neutral-400">MRR (USD)</div>
          <div className="text-lg font-bold text-emerald-400">${mrr.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-xs text-neutral-400">Customers</div>
          <div className="text-lg font-bold text-cyan-400">{customers}</div>
        </div>
        <div>
          <div className="text-xs text-neutral-400">ARPU</div>
          <div className="text-lg font-bold text-amber-400">${arpu}</div>
        </div>
      </div>
      {trend.length > 0 && (
        <div className="flex items-end gap-0.5 h-10">
          {trend.map((r, i) => (
            <div
              key={i}
              className="flex-1 bg-emerald-500/60 rounded-sm"
              style={{ height: `${((r.mrr_usd || 0) / max) * 100}%` }}
              title={`${r.date}: $${r.mrr_usd}`}
            />
          ))}
        </div>
      )}
    </div>
  );
}
