'use client';

import { useEffect, useMemo, useState, type FormEvent } from 'react';

const BRIDGE_API = process.env.NEXT_PUBLIC_BRIDGE_API || 'http://127.0.0.1:8081';

type SlotStatus = 'active' | 'idle' | 'cooldown' | 'disabled' | string;

interface CodexSlotRecord {
  slot_id: string;
  label: string;
  role: string;
  status: SlotStatus;
  quota_estimate: string | null;
  is_available: boolean;
  current_job: {
    job_id: string;
    description: string;
    started_at: string | null;
    duration_seconds?: number | null;
  } | null;
  last_completion: string | null;
  fail_count: number;
  cooldown_remaining: number;
  cooldown_until: string | null;
}

interface CodexSlotsPayload {
  slots: CodexSlotRecord[];
}

interface CodexJobRecord {
  job_id: string;
  status: string;
  priority: number;
  role: string;
  slot_id: string | null;
  worktree: string | null;
  task: {
    description: string;
    type: string;
    payload: Record<string, unknown>;
  };
  task_description: string;
  requested_slots: string[];
  selected_slots: string[];
  failure_reason: string | null;
  started_at: string | null;
  completed_at: string | null;
  dispatch_after?: string | null;
  output_summary: string | null;
}

interface CodexJobsPayload {
  jobs: CodexJobRecord[];
}

interface CodexHealthSlotRecord {
  slot_id: string;
  health_score: number;
  status: string;
  quota_estimate: string | null;
  cooldown?: {
    until: string | null;
    reason: string | null;
    active: boolean;
    remaining_seconds: number;
  } | null;
}

interface CodexHealthPayload {
  slots: CodexHealthSlotRecord[];
  stuck_jobs: CodexJobRecord[];
  cooldowns: Record<string, { until: string | null; reason: string | null; active: boolean; remaining_seconds: number }>;
}

interface CodexAuditEntry {
  ts: string;
  job_id: string;
  role: string;
  affinity_chain: string[];
  selected_slot: string | null;
  reason: string;
  quota_before: Record<string, { remaining_pct?: number }>;
  cooldown_state: Record<string, string | null>;
}

interface CodexAuditPayload {
  entries: CodexAuditEntry[];
}

interface SlotRuntimePayload {
  slot_id: string;
  status: 'ok' | 'missing' | 'error';
  exists: boolean;
  path: string;
  updated_at: string | null;
  size_bytes: number | null;
  line_count: number;
  truncated: boolean;
  content: string;
  error: string | null;
}

function formatTimestamp(value: string | null | undefined): string {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString('tr-TR', { hour12: false });
}

function formatDuration(seconds?: number | null): string {
  if (typeof seconds !== 'number' || !Number.isFinite(seconds) || seconds < 0) return '-';
  const total = Math.round(seconds);
  const minutes = Math.floor(total / 60);
  const remainder = total % 60;
  return minutes > 0 ? `${minutes}m ${remainder}s` : `${remainder}s`;
}

function formatRemaining(seconds: number): string {
  if (!seconds) return '-';
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return minutes > 0 ? `${minutes}m ${remainder}s` : `${remainder}s`;
}

function formatBytes(value?: number | null): string {
  if (typeof value !== 'number' || !Number.isFinite(value) || value < 0) return '-';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${(value / (1024 * 1024)).toFixed(1)} MB`;
}

function statusClass(status: SlotStatus): string {
  if (status === 'active') return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300';
  if (status === 'cooldown') return 'border-orange-500/40 bg-orange-500/10 text-orange-300';
  if (status === 'disabled') return 'border-red-500/40 bg-red-500/10 text-red-300';
  return 'border-sky-500/40 bg-sky-500/10 text-sky-300';
}

function runtimeClass(status?: string): string {
  if (status === 'ok') return 'border-cyan-500/30 bg-cyan-500/10 text-cyan-200';
  if (status === 'missing') return 'border-amber-500/30 bg-amber-500/10 text-amber-200';
  if (status === 'error') return 'border-red-500/30 bg-red-500/10 text-red-200';
  return 'border-neutral-700 bg-neutral-900 text-neutral-300';
}

function healthClass(score: number): string {
  if (score >= 80) return 'bg-emerald-400';
  if (score >= 50) return 'bg-yellow-400';
  return 'bg-red-400';
}

async function fetchJson<T>(path: string): Promise<T> {
  const response = await fetch(`${BRIDGE_API}${path}`, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`${path} failed`);
  }
  return response.json() as Promise<T>;
}

async function fetchAppJson<T>(path: string): Promise<T> {
  const response = await fetch(path, { cache: 'no-store' });
  if (!response.ok) {
    throw new Error(`${path} failed`);
  }
  return response.json() as Promise<T>;
}

export default function CodexAccountsPage() {
  const [slots, setSlots] = useState<CodexSlotRecord[]>([]);
  const [queue, setQueue] = useState<CodexJobRecord[]>([]);
  const [runningJobs, setRunningJobs] = useState<CodexJobRecord[]>([]);
  const [failedJobs, setFailedJobs] = useState<CodexJobRecord[]>([]);
  const [health, setHealth] = useState<CodexHealthPayload | null>(null);
  const [audit, setAudit] = useState<CodexAuditEntry[]>([]);
  const [forgeRuntime, setForgeRuntime] = useState<SlotRuntimePayload | null>(null);
  const [sparkRuntime, setSparkRuntime] = useState<SlotRuntimePayload | null>(null);
  const [message, setMessage] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);
  const [dispatchLoading, setDispatchLoading] = useState<boolean>(false);
  const [taskDescription, setTaskDescription] = useState<string>('');
  const [role, setRole] = useState<string>('backend');
  const [priority, setPriority] = useState<number>(5);
  const [selectedSlot, setSelectedSlot] = useState<string>('forge');

  async function refresh() {
    const [slotsPayload, queuePayload, healthPayload, runningPayload, failedPayload, auditPayload, forgeRuntimePayload, sparkRuntimePayload] = await Promise.all([
      fetchJson<CodexSlotsPayload>('/api/codex/slots'),
      fetchJson<CodexJobsPayload>('/api/codex/queue'),
      fetchJson<CodexHealthPayload>('/api/codex/health'),
      fetchJson<CodexJobsPayload>('/api/codex/jobs?status=running'),
      fetchJson<CodexJobsPayload>('/api/codex/jobs?status=failed'),
      fetchJson<CodexAuditPayload>('/api/codex/audit'),
      fetchAppJson<SlotRuntimePayload>('/api/codex/forge-runtime'),
      fetchAppJson<SlotRuntimePayload>('/api/codex/spark-runtime'),
    ]);

    setSlots(slotsPayload.slots || []);
    setQueue(queuePayload.jobs || []);
    setHealth(healthPayload);
    setRunningJobs(runningPayload.jobs || []);
    setFailedJobs((failedPayload.jobs || []).slice(0, 10));
    setAudit((auditPayload.entries || []).slice(0, 10));
    setForgeRuntime(forgeRuntimePayload);
    setSparkRuntime(sparkRuntimePayload);
    setLoading(false);
  }

  useEffect(() => {
    let cancelled = false;

    const run = async () => {
      try {
        await refresh();
      } catch {
        if (!cancelled) {
          setMessage('Bridge /api/codex/* endpointleri okunamadi.');
          setLoading(false);
        }
      }
    };

    run();
    const timer = window.setInterval(run, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, []);

  const healthBySlot = useMemo(() => {
    const map = new Map<string, CodexHealthSlotRecord>();
    for (const item of health?.slots || []) {
      map.set(item.slot_id, item);
    }
    return map;
  }, [health]);

  useEffect(() => {
    if (!slots.length) return;
    if (!slots.some((slot) => slot.slot_id === selectedSlot)) {
      setSelectedSlot(slots[0].slot_id);
    }
  }, [selectedSlot, slots]);

  const selectedSlotRecord =
    slots.find((slot) => slot.slot_id === selectedSlot) ?? slots[0] ?? null;
  const selectedSlotId = selectedSlotRecord?.slot_id ?? selectedSlot;
  const selectedSlotHealth = selectedSlotRecord ? healthBySlot.get(selectedSlotRecord.slot_id) : null;
  const selectedSlotRunning = useMemo(
    () => runningJobs.filter((job) => job.slot_id === selectedSlotId),
    [runningJobs, selectedSlotId]
  );
  const selectedSlotQueue = useMemo(
    () =>
      queue.filter((job) => {
        const resolvedSlot = job.selected_slots[0] || job.requested_slots[0] || job.slot_id;
        return resolvedSlot === selectedSlotId;
      }),
    [queue, selectedSlotId]
  );
  const selectedSlotFailed = useMemo(
    () => failedJobs.filter((job) => job.slot_id === selectedSlotId),
    [failedJobs, selectedSlotId]
  );
  const selectedSlotAudit = useMemo(
    () =>
      audit.filter(
        (entry) => entry.selected_slot === selectedSlotId || (entry.affinity_chain || []).includes(selectedSlotId)
      ),
    [audit, selectedSlotId]
  );
  const selectedRuntime =
    selectedSlotId === 'forge' ? forgeRuntime : selectedSlotId === 'spark' ? sparkRuntime : null;
  const showsRuntimeMaster = selectedSlotId === 'forge' || selectedSlotId === 'spark';
  const runtimePanelTitle =
    selectedSlotId === 'forge'
      ? 'Forge Runtime Master'
      : selectedSlotId === 'spark'
        ? 'Spark Runtime Master'
        : 'Slot Activity Lens';
  const runtimePanelDescription =
    selectedSlotId === 'forge'
      ? 'Desktop TXT kaynagi bridge runtime referansi olarak okunur.'
      : selectedSlotId === 'spark'
        ? 'Desktop TXT kaynagi voice/hologram/media referansi olarak okunur.'
        : 'Secili slot icin is, kuyruk ve audit ozeti.';

  async function control(action: string, slotId?: string, jobId?: string) {
    const response = await fetch(`${BRIDGE_API}/api/codex/control`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, slot_id: slotId, job_id: jobId }),
    });
    const payload = await response.json();
    setMessage(payload.message || (payload.ok ? 'islem tamamlandi' : 'islem basarisiz'));
    await refresh();
  }

  async function dispatchJob(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!taskDescription.trim()) {
      setMessage('Is tanimi gerekli.');
      return;
    }
    setDispatchLoading(true);
    try {
      const response = await fetch(`${BRIDGE_API}/api/codex/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_description: taskDescription.trim(), role, priority }),
      });
      const payload = await response.json();
      setMessage(payload.message || `Job olusturuldu: ${payload.job_id || '-'}`);
      setTaskDescription('');
      await refresh();
    } finally {
      setDispatchLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-neutral-950 px-6 py-6 font-mono text-neutral-100">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-wrap items-center justify-between gap-3 border-b border-neutral-800 pb-4">
          <div>
            <a href="/" className="text-xs uppercase tracking-[0.2em] text-neutral-500 hover:text-neutral-300">Dashboard</a>
            <h1 className="mt-2 text-2xl font-semibold text-neutral-100">Codex Accounts</h1>
            <p className="mt-1 text-sm text-neutral-400">5-slot scheduler, queue, health, controls.</p>
          </div>
          <div className="text-xs text-neutral-400">{message || (loading ? 'yukleniyor...' : 'canli veri akiyor')}</div>
        </header>

        <section className="grid gap-4 lg:grid-cols-5">
          {(slots || []).map((slot) => {
            const healthSlot = healthBySlot.get(slot.slot_id);
            const currentJob = slot.current_job;
            return (
              <div key={slot.slot_id} className="border border-neutral-800 bg-neutral-900 p-4 rounded-md">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <div className="text-sm font-semibold text-white">{slot.label}</div>
                    <div className="mt-1 text-[11px] uppercase tracking-[0.2em] text-neutral-500">{slot.role}</div>
                  </div>
                  <div className={`rounded-md border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${statusClass(slot.status)}`}>{slot.status}</div>
                </div>
                <div className="mt-4 space-y-2 text-xs text-neutral-300">
                  <div>quota: {slot.quota_estimate || '-'}</div>
                  <div>fail count: <span className={slot.fail_count > 3 ? 'text-red-300' : 'text-neutral-300'}>{slot.fail_count}</span></div>
                  <div>last completion: {formatTimestamp(slot.last_completion)}</div>
                  <div>cooldown: {slot.cooldown_remaining ? formatRemaining(slot.cooldown_remaining) : '-'}</div>
                  <div className="min-h-[2.5rem] text-neutral-400">{currentJob ? `${currentJob.description} | ${formatDuration(currentJob.duration_seconds)}` : 'current job yok'}</div>
                </div>
                <div className="mt-4 flex flex-wrap gap-2">
                  <button onClick={() => control('drain', slot.slot_id)} className="border border-neutral-700 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-neutral-200 rounded-md hover:bg-neutral-800">Drain</button>
                  <button onClick={() => control('pause', slot.slot_id)} className="border border-neutral-700 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-neutral-200 rounded-md hover:bg-neutral-800">Pause</button>
                  <button onClick={() => control('disable', slot.slot_id)} className="border border-red-800 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-red-300 rounded-md hover:bg-red-950/30">Disable</button>
                </div>
                <div className="mt-4 flex items-center gap-2 text-xs text-neutral-400">
                  <span className={`h-2.5 w-2.5 rounded-full ${healthClass(healthSlot?.health_score || 0)}`} />
                  <span>health {healthSlot?.health_score ?? 0}</span>
                </div>
              </div>
            );
          })}
        </section>

        <section className="grid gap-6 lg:grid-cols-[0.92fr_1.08fr]">
          <div className="border border-neutral-800 bg-neutral-900 p-4 rounded-md">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-white">Slot Detail</h2>
                <p className="mt-1 text-xs text-neutral-500">Atlas, Forge, Nexus, Shield ve Spark icin tek panel.</p>
              </div>
              <div className="text-xs uppercase tracking-[0.18em] text-neutral-500">{selectedSlotId}</div>
            </div>

            <div className="mt-4 flex flex-wrap gap-2">
              {(slots || []).map((slot) => (
                <button
                  key={slot.slot_id}
                  onClick={() => setSelectedSlot(slot.slot_id)}
                  className={`rounded-md border px-3 py-1.5 text-[11px] uppercase tracking-[0.18em] transition ${
                    slot.slot_id === selectedSlotId
                      ? 'border-cyan-500/50 bg-cyan-500/10 text-cyan-200'
                      : 'border-neutral-700 bg-neutral-950 text-neutral-400 hover:border-neutral-500 hover:text-neutral-200'
                  }`}
                >
                  {slot.label}
                </button>
              ))}
            </div>

            {selectedSlotRecord ? (
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                <div className="rounded-md border border-neutral-800 bg-neutral-950 p-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-neutral-500">Runtime</div>
                  <div className="mt-2 flex items-center justify-between gap-3">
                    <div className="text-lg font-semibold text-white">{selectedSlotRecord.label}</div>
                    <span className={`rounded-md border px-2 py-1 text-[10px] uppercase tracking-[0.18em] ${statusClass(selectedSlotRecord.status)}`}>
                      {selectedSlotRecord.status}
                    </span>
                  </div>
                  <div className="mt-3 space-y-2 text-sm text-neutral-300">
                    <div>role: {selectedSlotRecord.role}</div>
                    <div>quota: {selectedSlotRecord.quota_estimate || '-'}</div>
                    <div>last completion: {formatTimestamp(selectedSlotRecord.last_completion)}</div>
                    <div>cooldown until: {formatTimestamp(selectedSlotRecord.cooldown_until)}</div>
                  </div>
                </div>

                <div className="rounded-md border border-neutral-800 bg-neutral-950 p-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-neutral-500">Health + Queue</div>
                  <div className="mt-3 grid grid-cols-2 gap-3 text-sm">
                    <div className="rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2">
                      <div className="text-neutral-500">health</div>
                      <div className="mt-1 text-white">{selectedSlotHealth?.health_score ?? 0}</div>
                    </div>
                    <div className="rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2">
                      <div className="text-neutral-500">fail count</div>
                      <div className="mt-1 text-white">{selectedSlotRecord.fail_count}</div>
                    </div>
                    <div className="rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2">
                      <div className="text-neutral-500">running</div>
                      <div className="mt-1 text-white">{selectedSlotRunning.length}</div>
                    </div>
                    <div className="rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2">
                      <div className="text-neutral-500">queued</div>
                      <div className="mt-1 text-white">{selectedSlotQueue.length}</div>
                    </div>
                  </div>
                  <div className="mt-3 min-h-[3rem] rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-xs text-neutral-400">
                    {selectedSlotRecord.current_job
                      ? `${selectedSlotRecord.current_job.description} | ${formatDuration(selectedSlotRecord.current_job.duration_seconds)}`
                      : 'current job yok'}
                  </div>
                </div>
              </div>
            ) : (
              <div className="mt-4 rounded-md border border-neutral-800 bg-neutral-950 p-4 text-sm text-neutral-500">
                Slot verisi henuz gelmedi.
              </div>
            )}
          </div>

          <div className="border border-neutral-800 bg-neutral-900 p-4 rounded-md">
            <div className="flex items-center justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-white">{runtimePanelTitle}</h2>
                <p className="mt-1 text-xs text-neutral-500">{runtimePanelDescription}</p>
              </div>
              <span className="rounded-md border border-neutral-700 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-neutral-300">
                {selectedSlotId}
              </span>
            </div>

            {showsRuntimeMaster ? (
              <div className="mt-4 space-y-4">
                <div className={`rounded-md border p-3 text-sm ${runtimeClass(selectedRuntime?.status)}`}>
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div className="font-medium">{selectedRuntime?.status || (loading ? 'loading' : 'unknown')}</div>
                    <div className="text-xs">
                      {selectedRuntime?.updated_at ? formatTimestamp(selectedRuntime.updated_at) : '-'}
                    </div>
                  </div>
                  <div className="mt-2 break-all text-xs opacity-80">
                    {selectedRuntime?.path || 'Path bekleniyor'}
                  </div>
                  {selectedRuntime?.error ? (
                    <div className="mt-2 text-xs opacity-90">{selectedRuntime.error}</div>
                  ) : null}
                </div>

                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-md border border-neutral-800 bg-neutral-950 px-3 py-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-neutral-500">size</div>
                    <div className="mt-2 text-sm text-white">{formatBytes(selectedRuntime?.size_bytes)}</div>
                  </div>
                  <div className="rounded-md border border-neutral-800 bg-neutral-950 px-3 py-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-neutral-500">lines</div>
                    <div className="mt-2 text-sm text-white">{selectedRuntime?.line_count ?? 0}</div>
                  </div>
                  <div className="rounded-md border border-neutral-800 bg-neutral-950 px-3 py-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-neutral-500">mode</div>
                    <div className="mt-2 text-sm text-white">{selectedRuntime?.truncated ? 'preview' : 'full'}</div>
                  </div>
                </div>

                <div className="rounded-md border border-neutral-800 bg-neutral-950">
                  <div className="border-b border-neutral-800 px-3 py-2 text-xs uppercase tracking-[0.18em] text-neutral-500">
                    Runtime Text
                  </div>
                  <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words px-3 py-3 text-xs leading-6 text-neutral-200">
                    {selectedRuntime?.content || 'Dosya icerigi bekleniyor.'}
                  </pre>
                </div>
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                <div className="grid gap-3 md:grid-cols-3">
                  <div className="rounded-md border border-neutral-800 bg-neutral-950 px-3 py-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-neutral-500">running</div>
                    <div className="mt-2 text-sm text-white">{selectedSlotRunning.length}</div>
                  </div>
                  <div className="rounded-md border border-neutral-800 bg-neutral-950 px-3 py-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-neutral-500">queued</div>
                    <div className="mt-2 text-sm text-white">{selectedSlotQueue.length}</div>
                  </div>
                  <div className="rounded-md border border-neutral-800 bg-neutral-950 px-3 py-3">
                    <div className="text-xs uppercase tracking-[0.18em] text-neutral-500">failed</div>
                    <div className="mt-2 text-sm text-white">{selectedSlotFailed.length}</div>
                  </div>
                </div>

                <div className="rounded-md border border-neutral-800 bg-neutral-950 p-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-neutral-500">Recent Activity</div>
                  <div className="mt-3 space-y-3">
                    {selectedSlotRunning.slice(0, 2).map((job) => (
                      <div key={job.job_id} className="rounded-md border border-neutral-800 bg-neutral-900 p-3">
                        <div className="flex items-center justify-between gap-3 text-xs text-neutral-500">
                          <span>{job.job_id}</span>
                          <span>{formatTimestamp(job.started_at)}</span>
                        </div>
                        <div className="mt-2 text-sm text-white">{job.task_description}</div>
                      </div>
                    ))}
                    {!selectedSlotRunning.length && !selectedSlotQueue.length && !selectedSlotFailed.length ? (
                      <div className="text-sm text-neutral-500">Secili slot icin aktif is kaydi yok.</div>
                    ) : null}
                    {!selectedSlotRunning.length && selectedSlotQueue.length ? (
                      selectedSlotQueue.slice(0, 2).map((job) => (
                        <div key={job.job_id} className="rounded-md border border-neutral-800 bg-neutral-900 p-3">
                          <div className="flex items-center justify-between gap-3 text-xs text-neutral-500">
                            <span>{job.job_id}</span>
                            <span>p{job.priority}</span>
                          </div>
                          <div className="mt-2 text-sm text-white">{job.task_description}</div>
                        </div>
                      ))
                    ) : null}
                    {!selectedSlotRunning.length && !selectedSlotQueue.length && selectedSlotFailed.length ? (
                      selectedSlotFailed.slice(0, 2).map((job) => (
                        <div key={job.job_id} className="rounded-md border border-red-900/30 bg-red-950/10 p-3">
                          <div className="flex items-center justify-between gap-3 text-xs text-red-300">
                            <span>{job.job_id}</span>
                            <span>failed</span>
                          </div>
                          <div className="mt-2 text-sm text-white">{job.task_description}</div>
                          <div className="mt-1 text-xs text-red-300">{job.failure_reason || 'failure reason yok'}</div>
                        </div>
                      ))
                    ) : null}
                  </div>
                </div>

                <div className="rounded-md border border-neutral-800 bg-neutral-950 p-3">
                  <div className="text-xs uppercase tracking-[0.18em] text-neutral-500">Dispatch Audit</div>
                  <div className="mt-3 space-y-3">
                    {selectedSlotAudit.length ? (
                      selectedSlotAudit.slice(0, 3).map((entry) => (
                        <div key={`${entry.ts}-${entry.job_id}`} className="rounded-md border border-neutral-800 bg-neutral-900 p-3">
                          <div className="flex items-center justify-between gap-3 text-xs text-neutral-500">
                            <span>{entry.job_id}</span>
                            <span>{formatTimestamp(entry.ts)}</span>
                          </div>
                          <div className="mt-2 text-sm text-white">{entry.reason}</div>
                        </div>
                      ))
                    ) : (
                      <div className="text-sm text-neutral-500">Secili slot icin audit kaydi yok.</div>
                    )}
                  </div>
                </div>
              </div>
            )}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[1.25fr_0.95fr]">
          <div className="space-y-4">
            <div className="border border-neutral-800 bg-neutral-900 p-4 rounded-md">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-white">Running Jobs</h2>
                <span className="text-xs text-neutral-400">{runningJobs.length} job</span>
              </div>
              <div className="space-y-3">
                {runningJobs.length ? runningJobs.map((job) => (
                  <div key={job.job_id} className="border border-neutral-800 bg-neutral-950 p-3 rounded-md">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-xs uppercase tracking-[0.18em] text-neutral-500">{job.slot_id || '-'}</div>
                      <div className="text-xs text-neutral-400">{formatTimestamp(job.started_at)}</div>
                    </div>
                    <div className="mt-2 text-sm text-white">{job.task_description}</div>
                    <div className="mt-1 text-xs text-neutral-400">{job.role}</div>
                  </div>
                )) : <div className="text-sm text-neutral-500">running job yok</div>}
              </div>
            </div>

            <div className="border border-neutral-800 bg-neutral-900 p-4 rounded-md">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-white">Pending Queue</h2>
                <span className="text-xs text-neutral-400">{queue.length} job</span>
              </div>
              <div className="space-y-3">
                {queue.length ? queue.map((job) => (
                  <div key={job.job_id} className="border border-neutral-800 bg-neutral-950 p-3 rounded-md">
                    <div className="flex items-center justify-between gap-3 text-xs text-neutral-400">
                      <span>p{job.priority}</span>
                      <span>{job.role}</span>
                    </div>
                    <div className="mt-2 text-sm text-white">{job.task_description}</div>
                    <div className="mt-1 text-xs text-neutral-500">{job.selected_slots[0] || job.requested_slots[0] || '-'}</div>
                  </div>
                )) : <div className="text-sm text-neutral-500">pending queue bos</div>}
              </div>
            </div>

            <div className="border border-neutral-800 bg-neutral-900 p-4 rounded-md">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-white">Failed Jobs</h2>
                <span className="text-xs text-neutral-400">{failedJobs.length} job</span>
              </div>
              <div className="space-y-3">
                {failedJobs.length ? failedJobs.map((job) => (
                  <div key={job.job_id} className="border border-neutral-800 bg-neutral-950 p-3 rounded-md">
                    <div className="flex items-center justify-between gap-3">
                      <div className="text-xs uppercase tracking-[0.18em] text-red-300">{job.slot_id || '-'}</div>
                      <button onClick={() => control('retry', undefined, job.job_id)} className="border border-neutral-700 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-neutral-200 rounded-md hover:bg-neutral-800">Retry</button>
                    </div>
                    <div className="mt-2 text-sm text-white">{job.task_description}</div>
                    <div className="mt-1 text-xs text-red-300">{job.failure_reason || 'failure reason yok'}</div>
                  </div>
                )) : <div className="text-sm text-neutral-500">failed job yok</div>}
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="border border-neutral-800 bg-neutral-900 p-4 rounded-md">
              <div className="mb-3 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-white">Controls</h2>
                <button onClick={() => control('clear_cooldowns')} className="border border-neutral-700 px-2 py-1 text-[10px] uppercase tracking-[0.18em] text-neutral-200 rounded-md hover:bg-neutral-800">Clear All Cooldowns</button>
              </div>
              <form onSubmit={dispatchJob} className="space-y-3">
                <textarea value={taskDescription} onChange={(event) => setTaskDescription(event.target.value)} rows={5} className="w-full rounded-md border border-neutral-800 bg-neutral-950 px-3 py-2 text-sm text-white outline-none" placeholder="Dispatch New Job" />
                <div className="grid gap-3 sm:grid-cols-2">
                  <select value={role} onChange={(event) => setRole(event.target.value)} className="rounded-md border border-neutral-800 bg-neutral-950 px-3 py-2 text-sm text-white outline-none">
                    {['backend', 'security', 'voice', 'video', 'core', 'manager', 'overflow', 'any'].map((item) => (
                      <option key={item} value={item}>{item}</option>
                    ))}
                  </select>
                  <div className="rounded-md border border-neutral-800 bg-neutral-950 px-3 py-2">
                    <div className="flex items-center justify-between text-xs text-neutral-400">
                      <span>priority</span>
                      <span>{priority}</span>
                    </div>
                    <input type="range" min={0} max={10} value={priority} onChange={(event) => setPriority(Number(event.target.value))} className="mt-2 w-full" />
                  </div>
                </div>
                <button type="submit" disabled={dispatchLoading} className="w-full rounded-md border border-emerald-700 bg-emerald-900/30 px-3 py-2 text-sm text-emerald-200 hover:bg-emerald-900/50 disabled:opacity-50">
                  {dispatchLoading ? 'dispatching...' : 'Dispatch New Job'}
                </button>
              </form>
            </div>

            <div className="border border-neutral-800 bg-neutral-900 p-4 rounded-md">
              <h2 className="text-sm font-semibold text-white">Health</h2>
              <div className="mt-3 space-y-3">
                {(health?.slots || []).map((slot) => (
                  <div key={slot.slot_id} className="flex items-center justify-between border border-neutral-800 bg-neutral-950 px-3 py-2 rounded-md text-sm">
                    <div>
                      <div className="text-white">{slot.slot_id}</div>
                      <div className="text-xs text-neutral-500">{slot.quota_estimate || '-'}</div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`h-2.5 w-2.5 rounded-full ${healthClass(slot.health_score)}`} />
                      <span className="text-neutral-300">{slot.health_score}</span>
                    </div>
                  </div>
                ))}
                <div className="text-sm text-neutral-400">stuck jobs: {health?.stuck_jobs?.length || 0}</div>
              </div>
            </div>

            <div className="border border-neutral-800 bg-neutral-900 p-4 rounded-md">
              <h2 className="text-sm font-semibold text-white">Dispatch Audit</h2>
              <div className="mt-3 space-y-3">
                {audit.length ? audit.map((entry) => (
                  <div key={`${entry.ts}-${entry.job_id}`} className="border border-neutral-800 bg-neutral-950 p-3 rounded-md">
                    <div className="flex items-center justify-between gap-3 text-xs text-neutral-500">
                      <span>{entry.job_id}</span>
                      <span>{formatTimestamp(entry.ts)}</span>
                    </div>
                    <div className="mt-2 text-sm text-white">{`${entry.role} -> ${entry.selected_slot || 'none'}`}</div>
                    <div className="mt-1 text-xs text-neutral-400">{entry.reason}</div>
                  </div>
                )) : <div className="text-sm text-neutral-500">dispatch audit kaydi yok</div>}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
