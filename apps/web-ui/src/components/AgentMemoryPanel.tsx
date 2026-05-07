'use client';

import { useEffect, useState } from 'react';

type AgentSummaryItem = {
  persona_id?: string;
  persona_name?: string;
  last_active?: string | null;
  message_count?: number;
  obsidian_note_count?: number;
  last_obsidian_note?: string | null;
};

type AgentsSummaryPayload = {
  active_persona?: string;
  agents?: AgentSummaryItem[];
};

type MemoryMessage = {
  role?: string;
  content?: string;
  ts?: string;
};

type PersonaMemoryPayload = {
  persona_id?: string;
  persona_name?: string;
  recent_messages?: MemoryMessage[];
  last_active?: string | null;
  message_count?: number;
  obsidian_note_count?: number;
  last_obsidian_note?: string | null;
};

type PcStatusPayload = {
  cpu_percent?: number;
  ram_used_mb?: number;
  ram_total_mb?: number;
  disk_used_gb?: number;
  disk_total_gb?: number;
  jarvis_processes?: string[];
  ts?: string;
};

function clip(value?: string | null, limit = 72) {
  const text = String(value || '').trim();
  if (!text) return '-';
  return text.length > limit ? `${text.slice(0, limit - 3)}...` : text;
}

function formatWhen(value?: string | null) {
  if (!value) return 'henuz aktif degil';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat('tr-TR', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
}

function roleTone(role?: string) {
  const normalized = String(role || '').toLowerCase();
  if (normalized === 'assistant') return 'border-cyan-500/20 bg-cyan-400/10 text-cyan-200';
  if (normalized === 'user') return 'border-amber-500/20 bg-amber-400/10 text-amber-100';
  return 'border-white/10 bg-white/[0.03] text-green-200';
}

export default function AgentMemoryPanel() {
  const [summary, setSummary] = useState<AgentsSummaryPayload | null>(null);
  const [memory, setMemory] = useState<PersonaMemoryPayload | null>(null);
  const [pcStatus, setPcStatus] = useState<PcStatusPayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let disposed = false;
    let timer: number | null = null;
    let activeController: AbortController | null = null;

    const load = async () => {
      const controller = new AbortController();
      activeController = controller;

      try {
        const [summaryResponse, pcResponse] = await Promise.allSettled([
          fetch('/api/agents/summary', { cache: 'no-store', signal: controller.signal }),
          fetch('/api/pc/status', { cache: 'no-store', signal: controller.signal }),
        ]);

        let nextSummary: AgentsSummaryPayload | null = null;

        if (summaryResponse.status === 'fulfilled') {
          if (summaryResponse.value.ok) {
            nextSummary = (await summaryResponse.value.json()) as AgentsSummaryPayload;
          } else {
            const payload = (await summaryResponse.value.json().catch(() => ({}))) as { error?: string };
            throw new Error(payload.error || 'Ajan ozeti alinamadi.');
          }
        } else {
          throw summaryResponse.reason;
        }

        const activePersona = String(nextSummary?.active_persona || '').trim();
        const memoryResponse = activePersona
          ? await fetch(`/api/persona/${encodeURIComponent(activePersona)}/memory?limit=5`, {
              cache: 'no-store',
              signal: controller.signal,
            })
          : null;

        const nextMemory =
          memoryResponse && memoryResponse.ok
            ? ((await memoryResponse.json()) as PersonaMemoryPayload)
            : null;

        const nextPcStatus =
          pcResponse.status === 'fulfilled' && pcResponse.value.ok
            ? ((await pcResponse.value.json()) as PcStatusPayload)
            : null;

        if (!disposed) {
          setSummary(nextSummary);
          setMemory(nextMemory);
          setPcStatus(nextPcStatus);
          setError(null);
        }
      } catch (caught) {
        if (caught instanceof Error && caught.name === 'AbortError') {
          return;
        }
        if (!disposed) {
          setError(caught instanceof Error ? caught.message : 'Agent memory panel yuklenemedi.');
        }
      } finally {
        if (activeController === controller) {
          activeController = null;
        }
        if (!disposed) {
          timer = window.setTimeout(load, 3000);
        }
      }
    };

    load();
    return () => {
      disposed = true;
      if (timer !== null) {
        window.clearTimeout(timer);
      }
      activeController?.abort();
    };
  }, []);

  const activePersonaId = String(summary?.active_persona || memory?.persona_id || '').trim();
  const activeAgentSummary =
    summary?.agents?.find((item) => String(item.persona_id || '') === activePersonaId) || null;
  const recentMessages = memory?.recent_messages || [];
  const agents = summary?.agents || [];

  return (
    <section className="overflow-hidden rounded-2xl border border-green-900/30 bg-gray-900/70">
      <div className="border-b border-green-900/20 px-4 py-2 text-[10px] uppercase tracking-widest text-green-700">
        Agent Memory
      </div>

      <div className="space-y-4 p-3">
        <div className="rounded-xl border border-emerald-900/30 bg-emerald-950/10 p-3">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-[10px] uppercase tracking-[0.25em] text-green-800">aktif persona</div>
              <div className="mt-1 text-lg font-bold text-green-200">
                {memory?.persona_name || activeAgentSummary?.persona_name || activePersonaId || '-'}
              </div>
            </div>
            <div className="text-right text-xs text-green-700">
              <div>notes: {memory?.obsidian_note_count ?? activeAgentSummary?.obsidian_note_count ?? 0}</div>
              <div>msgs: {memory?.message_count ?? activeAgentSummary?.message_count ?? 0}</div>
            </div>
          </div>

          <div className="mt-3 grid gap-2 text-xs text-green-700">
            <div>last active: {formatWhen(memory?.last_active ?? activeAgentSummary?.last_active)}</div>
            <div>last note: {clip(memory?.last_obsidian_note ?? activeAgentSummary?.last_obsidian_note, 64)}</div>
          </div>
        </div>

        {pcStatus ? (
          <div className="rounded-xl border border-cyan-900/30 bg-cyan-950/10 p-3 text-xs text-cyan-100">
            <div className="text-[10px] uppercase tracking-[0.25em] text-cyan-700">pc status</div>
            <div className="mt-2 grid grid-cols-2 gap-2">
              <div>CPU: {pcStatus.cpu_percent ?? 0}%</div>
              <div>
                RAM: {pcStatus.ram_used_mb ?? 0}/{pcStatus.ram_total_mb ?? 0} MB
              </div>
              <div>
                Disk: {pcStatus.disk_used_gb ?? 0}/{pcStatus.disk_total_gb ?? 0} GB
              </div>
              <div>Proc: {(pcStatus.jarvis_processes || []).length}</div>
            </div>
          </div>
        ) : null}

        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
          <div className="text-[10px] uppercase tracking-[0.25em] text-green-800">agent summary</div>
          <div className="mt-3 max-h-40 space-y-2 overflow-y-auto pr-1">
            {agents.length ? (
              agents.map((agent, index) => {
                const isActive = String(agent.persona_id || '') === activePersonaId;
                return (
                  <div
                    key={`${String(agent.persona_id || agent.persona_name || 'agent')}-${index}`}
                    className={`rounded-lg border px-3 py-2 text-xs ${
                      isActive
                        ? 'border-emerald-500/30 bg-emerald-400/10 text-emerald-100'
                        : 'border-white/10 bg-black/10 text-green-300'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="font-semibold">{agent.persona_name || agent.persona_id || '-'}</span>
                      <span>{agent.obsidian_note_count ?? 0} note</span>
                    </div>
                    <div className="mt-1 text-[11px] opacity-80">
                      {clip(agent.last_obsidian_note, 52)}
                    </div>
                  </div>
                );
              })
            ) : (
              <div className="rounded-lg border border-white/10 bg-black/10 px-3 py-2 text-sm text-green-700">
                Ajan ozeti henuz gelmedi.
              </div>
            )}
          </div>
        </div>

        <div className="rounded-xl border border-white/10 bg-white/[0.03] p-3">
          <div className="flex items-center justify-between gap-3">
            <div className="text-[10px] uppercase tracking-[0.25em] text-green-800">son mesajlar</div>
            <div className="text-[10px] text-green-700">{recentMessages.length} kayit</div>
          </div>
          <div className="mt-3 max-h-64 space-y-2 overflow-y-auto pr-1">
            {recentMessages.length ? (
              recentMessages.map((message, index) => (
                <div key={`${message.ts}-${message.role}-${index}`} className="rounded-lg border border-white/10 bg-black/10 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className={`rounded-full border px-2 py-1 text-[10px] uppercase ${roleTone(message.role)}`}>
                      {message.role || 'event'}
                    </span>
                    <span className="text-[10px] text-green-700">{formatWhen(message.ts)}</span>
                  </div>
                  <div className="mt-2 text-sm leading-6 text-green-100">{clip(message.content, 220)}</div>
                </div>
              ))
            ) : (
              <div className="rounded-lg border border-white/10 bg-black/10 px-3 py-2 text-sm text-green-700">
                Son mesaj bulunamadi.
              </div>
            )}
          </div>
        </div>

        {error ? (
          <div className="rounded-xl border border-rose-900/40 bg-rose-950/20 px-3 py-2 text-xs text-rose-200">
            {error}
          </div>
        ) : null}
      </div>
    </section>
  );
}
