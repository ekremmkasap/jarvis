'use client';
import { useState, useRef, useEffect } from 'react';

const ORCHESTRATOR = process.env.NEXT_PUBLIC_ORCHESTRATOR_URL || 'http://localhost:8091';

const SUGGESTIONS = [
  'analyze repo',
  'review PRs',
  'triage issues',
  'debug CI',
  'release prep',
  'daily summary',
  'status',
  'update docs',
];

type LogEntry = { text: string; kind: 'cmd' | 'res' | 'sys' | 'err' };

export default function CommandConsole() {
  const [input, setInput] = useState('');
  const [log, setLog] = useState<LogEntry[]>([
    { text: 'Jarvis Mission Control v2.0', kind: 'sys' },
    { text: 'Type a goal or say "Hey Jarvis"', kind: 'sys' },
    { text: `Orchestrator: ${ORCHESTRATOR}`, kind: 'sys' },
  ]);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [log]);

  const push = (text: string, kind: LogEntry['kind']) =>
    setLog((l) => [...l, { text, kind }]);

  const submit = async () => {
    const cmd = input.trim();
    if (!cmd) return;
    push(`> ${cmd}`, 'cmd');
    setInput('');

    try {
      const res = await fetch(`${ORCHESTRATOR}/task`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal: cmd, agent: 'planner' }),
      });
      const data = await res.json();
      if (data.task_id) {
        push(`✓ Task ${data.task_id} created (${data.status})`, 'res');
        if (data.requires_confirmation) {
          push('⚠ Requires confirmation — see task panel', 'res');
        }
      } else {
        push(`✗ ${data.detail || JSON.stringify(data)}`, 'err');
      }
    } catch {
      push('✗ Orchestrator unreachable', 'err');
    }
  };

  const COLOR: Record<LogEntry['kind'], string> = {
    cmd: 'text-green-300',
    res: 'text-green-500',
    sys: 'text-green-900',
    err: 'text-red-400',
  };

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      <div className="flex-1 overflow-y-auto px-3 py-2 space-y-0.5 text-xs">
        {log.map((e, i) => (
          <div key={i} className={COLOR[e.kind]}>
            {e.text}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-green-900/30 flex items-center px-3 py-2 gap-2">
        <span className="text-green-700 text-xs">$</span>
        <input
          className="flex-1 bg-transparent text-green-300 text-xs outline-none placeholder:text-green-900"
          placeholder="Enter goal..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && submit()}
          list="jarvis-suggestions"
          autoComplete="off"
        />
        <datalist id="jarvis-suggestions">
          {SUGGESTIONS.map((s) => <option key={s} value={s} />)}
        </datalist>
        <button
          className="text-green-700 hover:text-green-400 text-xs px-2 transition-colors"
          onClick={submit}
        >
          ↵
        </button>
      </div>
    </div>
  );
}
