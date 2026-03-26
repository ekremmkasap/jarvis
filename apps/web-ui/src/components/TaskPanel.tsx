'use client';
import { Task } from '@/hooks/useJarvisStore';

const ORCHESTRATOR = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8091';

const STATUS_STYLE: Record<string, string> = {
  queued: 'text-yellow-400 border-yellow-800/50',
  running: 'text-blue-400 border-blue-800/50',
  done: 'text-green-400 border-green-800/50',
  failed: 'text-red-400 border-red-800/50',
  awaiting_confirmation: 'text-orange-400 border-orange-800/50',
  pending: 'text-gray-400 border-gray-700/50',
};

const AGENT_STYLE: Record<string, string> = {
  planner: 'bg-purple-950/40 text-purple-300',
  repo_analyst: 'bg-blue-950/40 text-blue-300',
  developer: 'bg-cyan-950/40 text-cyan-300',
  reviewer: 'bg-yellow-950/40 text-yellow-300',
  debug: 'bg-red-950/40 text-red-300',
  release: 'bg-green-950/40 text-green-300',
  docs: 'bg-gray-800/40 text-gray-400',
  voice_narrator: 'bg-pink-950/40 text-pink-300',
  mission_control: 'bg-emerald-950/40 text-emerald-300',
};

function timeAgo(iso: string): string {
  if (!iso) return '';
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

export default function TaskPanel({ tasks }: { tasks: Task[] }) {
  if (!tasks.length) {
    return (
      <div className="flex items-center justify-center h-24 text-green-900 text-xs">
        No tasks yet
      </div>
    );
  }

  return (
    <div className="p-2 space-y-1.5">
      {tasks.map((t) => (
        <div
          key={t.id}
          className={`border rounded p-3 text-xs bg-gray-900/60 ${STATUS_STYLE[t.status] || 'border-green-900/30 text-green-400'}`}
        >
          <div className="flex items-center justify-between mb-1.5 gap-2">
            <span className="font-bold text-green-300 shrink-0">#{t.id}</span>
            <div className="flex items-center gap-1.5 min-w-0">
              <span className={`px-1.5 py-0.5 rounded text-[10px] shrink-0 ${AGENT_STYLE[t.agent] || 'bg-gray-800 text-gray-300'}`}>
                {t.agent}
              </span>
              <span className={`uppercase text-[10px] font-bold shrink-0 ${STATUS_STYLE[t.status]?.split(' ')[0]}`}>
                {t.status === 'awaiting_confirmation' ? 'CONFIRM' : t.status}
              </span>
            </div>
          </div>

          <p className="text-green-400/80 leading-snug line-clamp-2 text-[11px]">{t.goal}</p>

          <div className="mt-1 text-green-900 text-[10px]">
            {timeAgo(t.created_at)}
            {t.retries ? ` · retry ${t.retries}` : ''}
          </div>

          {t.requires_confirmation && (
            <button
              className="mt-2 w-full text-[10px] border border-orange-600/40 text-orange-400 rounded px-2 py-1 hover:bg-orange-950/30 transition-colors"
              onClick={() =>
                fetch(`${ORCHESTRATOR}/tasks/${t.id}/confirm`, { method: 'POST' }).catch(() => {})
              }
            >
              ⚠ Confirm to proceed
            </button>
          )}

          {t.status === 'done' && t.result && (
            <details className="mt-1.5">
              <summary className="text-green-800 cursor-pointer text-[10px] hover:text-green-600">
                View result
              </summary>
              <pre className="mt-1 text-green-700 whitespace-pre-wrap text-[10px] max-h-28 overflow-y-auto leading-relaxed">
                {t.result.slice(0, 600)}
              </pre>
            </details>
          )}

          {t.status === 'failed' && t.error && (
            <p className="mt-1 text-red-500 text-[10px] truncate">✗ {t.error}</p>
          )}
        </div>
      ))}
    </div>
  );
}
