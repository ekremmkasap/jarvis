'use client';

import { useEffect, useMemo, useState } from 'react';

const BRIDGE_API = process.env.NEXT_PUBLIC_BRIDGE_API || 'http://127.0.0.1:8081';
const USD_TO_TRY = 38;

type SkillError = {
  ok: false;
  error: string;
};

type Ec2Instance = {
  id: string;
  name: string;
  state: string;
  type: string;
  region: string;
  public_ip: string;
  launch_time: string | null;
};

type S3Bucket = {
  name: string;
  region: string;
  creation_date: string | null;
};

type CostPayload = {
  total_usd: number;
  by_service: Record<string, number>;
  period: string;
  currency: 'USD';
  mock?: boolean;
  note?: string;
};

type BudgetAlert = {
  name: string;
  limit_usd: number;
  current_usd: number;
  pct_used: number;
};

type Ec2ActionResponse = {
  ok: boolean;
  message?: string;
  error?: string;
};

function isSkillError(value: unknown): value is SkillError {
  return Boolean(value) && typeof value === 'object' && (value as SkillError).ok === false;
}

function formatMoney(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

function formatTry(value: number) {
  return new Intl.NumberFormat('tr-TR', { maximumFractionDigits: 2 }).format(value);
}

function formatDate(value: string | null) {
  if (!value) return '-';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat('tr-TR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(parsed);
}

function stateTone(state: string) {
  const lowered = String(state || '').toLowerCase();
  if (lowered === 'running') return 'text-emerald-300';
  if (lowered === 'stopped') return 'text-rose-300';
  if (lowered === 'pending') return 'text-amber-300';
  return 'text-slate-300';
}

async function fetchBridgeJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BRIDGE_API}${path}`, { cache: 'no-store' });
  const payload = (await response.json().catch(() => ({}))) as T | SkillError;
  if (!response.ok || isSkillError(payload)) {
    throw new Error(isSkillError(payload) ? payload.error : `Bridge error: ${path}`);
  }
  return payload as T;
}

export default function CloudPage() {
  const [instances, setInstances] = useState<Ec2Instance[]>([]);
  const [buckets, setBuckets] = useState<S3Bucket[]>([]);
  const [cost, setCost] = useState<CostPayload | null>(null);
  const [alerts, setAlerts] = useState<BudgetAlert[]>([]);
  const [message, setMessage] = useState<string>('');
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [actioningId, setActioningId] = useState<string | null>(null);

  async function loadCloudData() {
    setRefreshing(true);
    const results = await Promise.allSettled([
      fetchBridgeJson<Ec2Instance[]>('/api/cloud/ec2'),
      fetchBridgeJson<S3Bucket[]>('/api/cloud/s3'),
      fetchBridgeJson<CostPayload>('/api/cloud/cost'),
      fetchBridgeJson<BudgetAlert[]>('/api/cloud/alerts'),
    ]);

    const [ec2Result, s3Result, costResult, alertsResult] = results;

    if (ec2Result.status === 'fulfilled') setInstances(ec2Result.value);
    if (s3Result.status === 'fulfilled') setBuckets(s3Result.value);
    if (costResult.status === 'fulfilled') setCost(costResult.value);
    if (alertsResult.status === 'fulfilled') setAlerts(alertsResult.value);

    const firstError = results.find((item) => item.status === 'rejected') as PromiseRejectedResult | undefined;
    setMessage(firstError ? String(firstError.reason?.message || 'Cloud verisi alinamadi.') : '');
    setLastUpdated(new Date());
    setRefreshing(false);
  }

  useEffect(() => {
    loadCloudData().catch((error: unknown) => {
      setMessage(error instanceof Error ? error.message : 'Cloud verisi alinamadi.');
      setRefreshing(false);
    });

    const timer = window.setInterval(() => {
      loadCloudData().catch((error: unknown) => {
        setMessage(error instanceof Error ? error.message : 'Cloud verisi alinamadi.');
        setRefreshing(false);
      });
    }, 10000);

    return () => window.clearInterval(timer);
  }, []);

  async function runEc2Action(instanceId: string, action: 'start' | 'stop') {
    try {
      setActioningId(instanceId);
      const response = await fetch(`${BRIDGE_API}/api/cloud/ec2/action`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ instance_id: instanceId, action }),
      });
      const payload = (await response.json().catch(() => ({}))) as Ec2ActionResponse;
      if (!response.ok || payload.ok === false) {
        throw new Error(payload.error || 'EC2 aksiyonu basarisiz.');
      }
      setMessage(payload.message || `${instanceId} guncellendi.`);
      await loadCloudData();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'EC2 aksiyonu basarisiz.');
    } finally {
      setActioningId(null);
    }
  }

  const sortedServices = useMemo(() => {
    if (!cost) return [];
    return Object.entries(cost.by_service).sort((left, right) => right[1] - left[1]);
  }, [cost]);

  const tryEstimate = useMemo(() => (cost ? cost.total_usd * USD_TO_TRY : 0), [cost]);

  return (
    <div className="min-h-screen bg-gray-950 px-4 py-6 text-slate-100 md:px-6">
      <div className="mx-auto max-w-7xl space-y-4">
        <header className="flex flex-col gap-3 border-b border-slate-800 pb-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-cyan-300">Cloud</h1>
            <div className="mt-1 text-sm text-slate-400">
              {refreshing ? 'Yenileniyor...' : 'Hazir'} {lastUpdated ? `• ${formatDate(lastUpdated.toISOString())}` : ''}
            </div>
          </div>
          <button
            type="button"
            onClick={() => loadCloudData().catch(() => undefined)}
            className="rounded-md border border-cyan-700/40 px-3 py-2 text-sm text-cyan-200 transition hover:bg-cyan-950/30"
          >
            Yenile
          </button>
        </header>

        {message ? (
          <div className="rounded-md border border-amber-700/30 bg-amber-950/20 px-3 py-2 text-sm text-amber-200">
            {message}
          </div>
        ) : null}

        <section className="grid gap-4 xl:grid-cols-[1.5fr_1fr]">
          <article className="overflow-hidden rounded-md border border-slate-800 bg-slate-900/60">
            <div className="border-b border-slate-800 px-4 py-3 text-sm font-medium text-emerald-300">EC2</div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-950/60 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3">ID</th>
                    <th className="px-4 py-3">Name</th>
                    <th className="px-4 py-3">State</th>
                    <th className="px-4 py-3">Type</th>
                    <th className="px-4 py-3">Region</th>
                    <th className="px-4 py-3">IP</th>
                    <th className="px-4 py-3">Action</th>
                  </tr>
                </thead>
                <tbody>
                  {instances.length ? (
                    instances.map((instance) => (
                      <tr key={instance.id} className="border-t border-slate-800 text-slate-200">
                        <td className="px-4 py-3 align-top">{instance.id}</td>
                        <td className="px-4 py-3 align-top">{instance.name || '-'}</td>
                        <td className={`px-4 py-3 align-top ${stateTone(instance.state)}`}>{instance.state}</td>
                        <td className="px-4 py-3 align-top">{instance.type}</td>
                        <td className="px-4 py-3 align-top">{instance.region}</td>
                        <td className="px-4 py-3 align-top">{instance.public_ip || '-'}</td>
                        <td className="px-4 py-3 align-top">
                          <div className="flex flex-wrap gap-2">
                            <button
                              type="button"
                              onClick={() => runEc2Action(instance.id, 'start')}
                              disabled={actioningId === instance.id}
                              className="rounded-md border border-emerald-700/40 px-2 py-1 text-xs text-emerald-200 transition hover:bg-emerald-950/30 disabled:opacity-50"
                            >
                              Start
                            </button>
                            <button
                              type="button"
                              onClick={() => runEc2Action(instance.id, 'stop')}
                              disabled={actioningId === instance.id}
                              className="rounded-md border border-rose-700/40 px-2 py-1 text-xs text-rose-200 transition hover:bg-rose-950/30 disabled:opacity-50"
                            >
                              Stop
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={7} className="px-4 py-6 text-center text-slate-500">
                        EC2 kaydi yok.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>

          <div className="grid gap-4">
            <article className="rounded-md border border-slate-800 bg-slate-900/60">
              <div className="border-b border-slate-800 px-4 py-3 text-sm font-medium text-cyan-300">Cost</div>
              <div className="space-y-4 p-4">
                <div>
                  <div className="text-xs uppercase tracking-wide text-slate-500">Monthly total</div>
                  <div className="mt-1 text-3xl font-semibold text-cyan-200">
                    {cost ? formatMoney(cost.total_usd) : '$0.00'}
                  </div>
                  <div className="mt-1 text-sm text-slate-400">
                    Yaklasik TRY {formatTry(tryEstimate)} - 1 USD = 38 TRY
                  </div>
                </div>

                <div className="space-y-2">
                  {sortedServices.length ? (
                    sortedServices.slice(0, 6).map(([service, amount]) => (
                      <div key={service} className="flex items-center justify-between gap-3 border-t border-slate-800 pt-2 text-sm">
                        <span className="text-slate-300">{service}</span>
                        <span className="text-amber-300">{formatMoney(amount)}</span>
                      </div>
                    ))
                  ) : (
                    <div className="text-sm text-slate-500">Maliyet verisi yok.</div>
                  )}
                </div>
              </div>
            </article>

            <article className="rounded-md border border-slate-800 bg-slate-900/60">
              <div className="border-b border-slate-800 px-4 py-3 text-sm font-medium text-amber-300">Alerts</div>
              <div className="space-y-3 p-4">
                {alerts.length ? (
                  alerts.map((alert) => (
                    <div key={alert.name} className="space-y-2 border-b border-slate-800 pb-3 last:border-b-0 last:pb-0">
                      <div className="flex items-center justify-between gap-3">
                        <span className="text-sm text-slate-200">{alert.name}</span>
                        <span className="text-xs text-slate-400">{alert.pct_used.toFixed(2)}%</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-md bg-slate-800">
                        <div
                          className="h-full bg-amber-400"
                          style={{ width: `${Math.min(alert.pct_used, 100)}%` }}
                        />
                      </div>
                      <div className="flex items-center justify-between gap-3 text-xs text-slate-400">
                        <span>Limit {formatMoney(alert.limit_usd)}</span>
                        <span>Current {formatMoney(alert.current_usd)}</span>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="text-sm text-slate-500">Butce uyarisi yok</div>
                )}
              </div>
            </article>
          </div>
        </section>

        <section className="grid gap-4 xl:grid-cols-[1.2fr_1fr]">
          <article className="overflow-hidden rounded-md border border-slate-800 bg-slate-900/60">
            <div className="border-b border-slate-800 px-4 py-3 text-sm font-medium text-sky-300">S3</div>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-slate-950/60 text-left text-xs uppercase tracking-wide text-slate-500">
                  <tr>
                    <th className="px-4 py-3">Bucket</th>
                    <th className="px-4 py-3">Region</th>
                    <th className="px-4 py-3">Creation date</th>
                  </tr>
                </thead>
                <tbody>
                  {buckets.length ? (
                    buckets.map((bucket) => (
                      <tr key={bucket.name} className="border-t border-slate-800 text-slate-200">
                        <td className="px-4 py-3">{bucket.name}</td>
                        <td className="px-4 py-3">{bucket.region}</td>
                        <td className="px-4 py-3">{formatDate(bucket.creation_date)}</td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={3} className="px-4 py-6 text-center text-slate-500">
                        S3 bucket yok.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </article>

          <article className="rounded-md border border-slate-800 bg-slate-900/60">
            <div className="border-b border-slate-800 px-4 py-3 text-sm font-medium text-emerald-300">Refresh</div>
            <div className="space-y-3 p-4 text-sm text-slate-300">
              <div className="flex items-center justify-between gap-3">
                <span>Bridge</span>
                <span className="text-cyan-300">{BRIDGE_API}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>Son yenileme</span>
                <span>{lastUpdated ? formatDate(lastUpdated.toISOString()) : '-'}</span>
              </div>
              <div className="flex items-center justify-between gap-3">
                <span>Durum</span>
                <span className={refreshing ? 'text-amber-300' : 'text-emerald-300'}>
                  {refreshing ? 'Yenileniyor' : 'Hazir'}
                </span>
              </div>
              {cost?.mock ? (
                <div className="rounded-md border border-amber-700/30 bg-amber-950/20 px-3 py-2 text-xs text-amber-200">
                  Cost Explorer verisi yerine mock veri kullaniliyor.
                </div>
              ) : null}
            </div>
          </article>
        </section>
      </div>
    </div>
  );
}
