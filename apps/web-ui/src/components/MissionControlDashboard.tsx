'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { useJarvisStore } from '@/hooks/useJarvisStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import TaskPanel from '@/components/TaskPanel';
import AgentGraph from '@/components/AgentGraph';
import VoiceIndicator from '@/components/VoiceIndicator';
import CommandConsole from '@/components/CommandConsole';
import StatsBar from '@/components/StatsBar';
import NotificationsPanel from '@/components/NotificationsPanel';
import AgentMemoryPanel from '@/components/AgentMemoryPanel';

const ORCHESTRATOR_WS = process.env.NEXT_PUBLIC_ORCHESTRATOR_WS || 'ws://localhost:8091/ws';

type DashboardTask = {
  id?: string;
  goal?: string;
  agent?: string;
  status?: string;
  priority?: string;
  retries?: number;
};

type LiveEvent = {
  event?: string;
  message?: string;
  timestamp?: string;
  task?: DashboardTask;
};

type DashboardHealth = {
  status?: string;
  services?: {
    bridge?: { status?: string };
    orchestrator?: { status?: string };
  };
  router?: {
    status?: string;
    default_provider?: string;
    active?: {
      fallback_used?: boolean;
      route?: string;
      selected_candidate?: string;
      selected_provider?: string;
    };
  };
  providerHealth?: Record<string, { label?: string; detail?: string; ok?: boolean; status?: string }>;
  live?: {
    status?: string;
    activity?: string;
    queue_snapshot?: {
      queued_tasks?: number;
      running_tasks?: number;
      awaiting_confirmation_tasks?: number;
      done_tasks?: number;
      failed_tasks?: number;
    };
    current_task?: DashboardTask | null;
    last_task?: DashboardTask | null;
    recent_events?: LiveEvent[];
    voice?: {
      active?: boolean;
      phase?: string;
      status?: string;
      detail?: string;
      turn_count?: number;
      last_heard?: string;
      last_response?: string;
    };
  };
};

function tone(status?: string) {
  switch (String(status || '').toLowerCase()) {
    case 'healthy':
    case 'ready':
    case 'online':
    case 'active':
      return 'text-emerald-300 border-emerald-400/20 bg-emerald-400/10';
    case 'degraded':
    case 'warning':
    case 'limited':
      return 'text-amber-200 border-amber-400/20 bg-amber-400/10';
    case 'unhealthy':
    case 'offline':
    case 'failed':
    case 'unreachable':
      return 'text-rose-200 border-rose-400/20 bg-rose-400/10';
    default:
      return 'text-slate-300 border-white/10 bg-white/[0.03]';
  }
}

function formatWhen(value?: string) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('tr-TR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

function clip(value?: string, limit = 96) {
  const text = String(value || '').trim();
  if (!text) return '-';
  return text.length > limit ? `${text.slice(0, limit - 3)}...` : text;
}

export default function MissionControlDashboard() {
  const { tasks, notifications, agentNodes } = useJarvisStore();
  const [health, setHealth] = useState<DashboardHealth | null>(null);
  useWebSocket(ORCHESTRATOR_WS);

  useEffect(() => {
    let disposed = false;

    const loadHealth = async () => {
      try {
        const response = await fetch('/api/admin/health', { cache: 'no-store' });
        const payload = (await response.json()) as DashboardHealth;
        if (!disposed) {
          setHealth(payload);
        }
      } catch {
        if (!disposed) {
          setHealth(null);
        }
      }
    };

    loadHealth();
    const timer = setInterval(loadHealth, 15000);
    return () => {
      disposed = true;
      clearInterval(timer);
    };
  }, []);

  const queueSnapshot = health?.live?.queue_snapshot;
  const currentTask = health?.live?.current_task ?? health?.live?.last_task ?? null;
  const voice = health?.live?.voice;
  const liveEvents = health?.live?.recent_events ?? [];
  const providerEntries = Object.entries(health?.providerHealth ?? {});
  const queuedCount = queueSnapshot?.queued_tasks ?? tasks.filter((task) => task.status === 'queued').length;
  const runningCount = queueSnapshot?.running_tasks ?? tasks.filter((task) => task.status === 'running').length;
  const awaitingCount =
    queueSnapshot?.awaiting_confirmation_tasks ??
    tasks.filter((task) => task.status === 'awaiting_confirmation').length;
  const doneCount = queueSnapshot?.done_tasks ?? tasks.filter((task) => task.status === 'done').length;
  const failedCount = queueSnapshot?.failed_tasks ?? tasks.filter((task) => task.status === 'failed').length;

  return (
    <div className="min-h-screen bg-gray-950 text-green-400 font-mono select-none">
      <header className="sticky top-0 z-50 border-b border-green-900/40 bg-gray-950/90 px-6 py-3 backdrop-blur">
        <div className="flex flex-col gap-4 xl:flex-row xl:items-center xl:justify-between">
          <div className="flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <div className="h-2 w-2 rounded-full bg-green-400 animate-pulse" />
              <span className="text-lg font-bold tracking-widest text-green-300 uppercase">
                Jarvis Mission Control
              </span>
              <span className="rounded border border-green-900 px-1.5 py-0.5 text-[10px] text-green-800">
                /ops
              </span>
            </div>
            <p className="max-w-3xl text-xs leading-6 text-green-800">
              Live tasks, queue health, router telemetry ve runtime durumu tek operatör yüzeyinde tutulur.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs">
            <Link
              href="/landing"
              className="rounded-full border border-green-900/40 px-3 py-1.5 text-green-300 transition hover:border-green-700 hover:bg-green-950/30"
            >
              landing
            </Link>
            <Link
              href="/admin"
              className="rounded-full border border-cyan-900/50 px-3 py-1.5 text-cyan-300 transition hover:border-cyan-700 hover:bg-cyan-950/30"
            >
              admin
            </Link>
            <Link
              href="/codex-accounts"
              className="rounded-full border border-violet-900/50 px-3 py-1.5 text-violet-300 transition hover:border-violet-700 hover:bg-violet-950/30"
            >
              codex-accounts
            </Link>
            <VoiceIndicator />
          </div>
        </div>

        <div className="mt-4 overflow-x-auto">
          <StatsBar health={health} />
        </div>
      </header>

      <main className="space-y-4 p-4">
        <section className="grid gap-4 lg:grid-cols-2 2xl:grid-cols-4">
          <article className="rounded-2xl border border-green-900/30 bg-gray-900/70 p-4">
            <div className="text-[10px] uppercase tracking-[0.3em] text-green-800">Current Mission</div>
            <div className="mt-3 flex items-start justify-between gap-3">
              <div>
                <div className="text-lg font-bold text-green-200">
                  {currentTask?.id ? `#${currentTask.id}` : 'No active task'}
                </div>
                <div className="mt-1 text-xs text-green-700">
                  {currentTask?.agent ?? health?.live?.activity ?? 'idle'}
                </div>
              </div>
              <span className={`rounded-full border px-2 py-1 text-[10px] ${tone(currentTask?.status ?? health?.live?.status)}`}>
                {currentTask?.status ?? health?.live?.status ?? 'idle'}
              </span>
            </div>
            <p className="mt-3 text-sm leading-6 text-green-300">{clip(currentTask?.goal, 140)}</p>
          </article>

          <article className="rounded-2xl border border-green-900/30 bg-gray-900/70 p-4">
            <div className="text-[10px] uppercase tracking-[0.3em] text-green-800">Queue Health</div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
              <div className="rounded-xl border border-blue-900/30 bg-blue-950/20 p-3">
                <div className="text-blue-300">{runningCount}</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.25em] text-blue-800">running</div>
              </div>
              <div className="rounded-xl border border-yellow-900/30 bg-yellow-950/20 p-3">
                <div className="text-yellow-300">{queuedCount}</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.25em] text-yellow-800">queued</div>
              </div>
              <div className="rounded-xl border border-orange-900/30 bg-orange-950/20 p-3">
                <div className="text-orange-300">{awaitingCount}</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.25em] text-orange-800">awaiting</div>
              </div>
              <div className="rounded-xl border border-emerald-900/30 bg-emerald-950/20 p-3">
                <div className="text-emerald-300">{doneCount}</div>
                <div className="mt-1 text-[10px] uppercase tracking-[0.25em] text-emerald-800">done</div>
              </div>
            </div>
            {failedCount > 0 ? (
              <div className="mt-3 rounded-xl border border-rose-900/40 bg-rose-950/20 px-3 py-2 text-xs text-rose-300">
                {failedCount} failed task detected
              </div>
            ) : null}
          </article>

          <article className="rounded-2xl border border-green-900/30 bg-gray-900/70 p-4">
            <div className="text-[10px] uppercase tracking-[0.3em] text-green-800">Voice Runtime</div>
            <div className="mt-3 flex items-center justify-between gap-3">
              <div className="text-lg font-bold text-green-200">{voice?.status ?? 'offline'}</div>
              <span className={`rounded-full border px-2 py-1 text-[10px] ${tone(voice?.phase)}`}>
                {voice?.phase ?? 'idle'}
              </span>
            </div>
            <div className="mt-3 space-y-2 text-xs text-green-700">
              <div>turns: {voice?.turn_count ?? 0}</div>
              <div>heard: {clip(voice?.last_heard, 90)}</div>
              <div>reply: {clip(voice?.last_response, 90)}</div>
            </div>
          </article>

          <article className="rounded-2xl border border-green-900/30 bg-gray-900/70 p-4">
            <div className="text-[10px] uppercase tracking-[0.3em] text-green-800">Router Telemetry</div>
            <div className="mt-3 text-lg font-bold text-green-200">
              {health?.router?.active?.selected_candidate ?? health?.router?.default_provider ?? '-'}
            </div>
            <div className="mt-2 space-y-2 text-xs text-green-700">
              <div>provider: {health?.router?.active?.selected_provider ?? health?.router?.default_provider ?? '-'}</div>
              <div>route: {health?.router?.active?.route ?? '-'}</div>
              <div>fallback: {health?.router?.active?.fallback_used ? 'on' : 'off'}</div>
              <div>system: {health?.status ?? 'unknown'}</div>
            </div>
          </article>
        </section>

        <section className="grid gap-4 xl:grid-cols-[1.1fr_1fr_0.9fr]">
          <div className="space-y-4">
            <section className="overflow-hidden rounded-2xl border border-green-900/30 bg-gray-900/70">
              <div className="border-b border-green-900/20 px-4 py-2 text-[10px] uppercase tracking-widest text-green-700">
                Agent Network
              </div>
              <div className="h-[360px] overflow-hidden p-3">
                <AgentGraph nodes={agentNodes} />
              </div>
            </section>

            <section className="overflow-hidden rounded-2xl border border-green-900/30 bg-gray-900/70">
              <div className="border-b border-green-900/20 px-4 py-2 text-[10px] uppercase tracking-widest text-green-700">
                Provider Health
              </div>
              <div className="space-y-2 p-3">
                {providerEntries.length ? (
                  providerEntries.map(([name, value]) => (
                    <div
                      key={name}
                      className={`rounded-xl border px-3 py-3 text-sm ${tone(value?.label ?? value?.status)}`}
                    >
                      <div className="flex items-center justify-between gap-3">
                        <span className="uppercase tracking-[0.2em]">{name}</span>
                        <span>{value?.label ?? value?.status ?? '-'}</span>
                      </div>
                      <div className="mt-1 text-xs opacity-80">{clip(value?.detail, 120)}</div>
                    </div>
                  ))
                ) : (
                  <div className="rounded-xl border border-white/10 bg-white/[0.03] px-3 py-3 text-sm text-green-700">
                    Provider telemetry gelmedi.
                  </div>
                )}
              </div>
            </section>
          </div>

          <div className="space-y-4">
            <section className="overflow-hidden rounded-2xl border border-green-900/30 bg-gray-900/70">
              <div className="border-b border-green-900/20 px-4 py-2 text-[10px] uppercase tracking-widest text-green-700">
                Mission Queue ({tasks.length})
              </div>
              <div className="max-h-[420px] overflow-y-auto">
                <TaskPanel tasks={tasks} />
              </div>
            </section>

            <section className="overflow-hidden rounded-2xl border border-green-900/30 bg-gray-900/70">
              <div className="border-b border-green-900/20 px-4 py-2 text-[10px] uppercase tracking-widest text-green-700">
                Live Event Feed ({liveEvents.length})
              </div>
              <div className="max-h-[320px] space-y-2 overflow-y-auto p-3">
                {liveEvents.length ? (
                  [...liveEvents].reverse().map((event, index) => (
                    <div key={`${event.timestamp}-${event.event}-${index}`} className="rounded-xl border border-white/10 bg-white/[0.03] p-3 text-xs">
                      <div className="flex items-center justify-between gap-3 text-green-700">
                        <span className="uppercase tracking-[0.25em]">{event.event ?? 'event'}</span>
                        <span>{formatWhen(event.timestamp)}</span>
                      </div>
                      <div className="mt-2 text-sm leading-6 text-green-300">{clip(event.message, 160)}</div>
                      {event.task?.id ? (
                        <div className="mt-2 text-[11px] text-green-700">
                          #{event.task.id} - {event.task.agent ?? '-'} - {event.task.status ?? '-'}
                        </div>
                      ) : null}
                    </div>
                  ))
                ) : (
                  <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3 text-sm text-green-700">
                    Canonical live event akisi henuz veri donmedi.
                  </div>
                )}
              </div>
            </section>
          </div>

          <div className="space-y-4">
            <section className="overflow-hidden rounded-2xl border border-green-900/30 bg-gray-900/70">
              <div className="border-b border-green-900/20 px-4 py-2 text-[10px] uppercase tracking-widest text-green-700">
                Command Console
              </div>
              <div className="h-[220px] overflow-hidden">
                <CommandConsole />
              </div>
            </section>

            <AgentMemoryPanel />

            <section className="overflow-hidden rounded-2xl border border-green-900/30 bg-gray-900/70">
              <div className="border-b border-green-900/20 px-4 py-2 text-[10px] uppercase tracking-widest text-green-700">
                Notifications ({notifications.length})
              </div>
              <div className="h-[220px] overflow-y-auto">
                <NotificationsPanel notifications={notifications} />
              </div>
            </section>
          </div>
        </section>
      </main>
    </div>
  );
}
