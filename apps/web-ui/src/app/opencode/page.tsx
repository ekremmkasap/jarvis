'use client';

import { useEffect, useState } from 'react';

const BRIDGE_API = process.env.NEXT_PUBLIC_BRIDGE_API || 'http://127.0.0.1:8081';

interface OpenCodeStatus {
  running: boolean;
  port: number;
  url: string | null;
}

export default function OpenCodeTerminal() {
  const [status, setStatus] = useState<OpenCodeStatus | null>(null);
  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function fetchStatus() {
    try {
      const res = await fetch(`${BRIDGE_API}/api/opencode/status`, { cache: 'no-store' });
      if (res.ok) setStatus(await res.json());
    } catch {
      setError('Bridge bağlantısı yok');
    }
  }

  async function startOpenCode() {
    setStarting(true);
    setError(null);
    try {
      const res = await fetch(`${BRIDGE_API}/api/opencode/start`, { cache: 'no-store' });
      const data = await res.json();
      setStatus(data);
      if (!data.ok) setError('OpenCode başlatılamadı — opencode kurulu mu?');
    } catch {
      setError('Bridge bağlantısı yok');
    } finally {
      setStarting(false);
    }
  }

  useEffect(() => {
    fetchStatus();
    const t = setInterval(fetchStatus, 5000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="flex h-screen flex-col bg-gray-950 text-green-300">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-green-900/40 px-6 py-3">
        <div className="flex items-center gap-3">
          <a
            href="/"
            className="text-xs text-gray-500 hover:text-gray-300 transition-colors"
          >
            ← Dashboard
          </a>
          <span className="text-gray-700">|</span>
          <span className="text-sm font-bold uppercase tracking-widest text-cyan-300">
            OpenCode Terminal
          </span>
        </div>
        <div className="flex items-center gap-3">
          {status && (
            <span
              className={`rounded border px-2 py-0.5 text-[11px] font-medium ${
                status.running
                  ? 'border-emerald-800/50 bg-emerald-950/30 text-emerald-300'
                  : 'border-gray-700/50 bg-gray-900/30 text-gray-400'
              }`}
            >
              {status.running ? `● aktif :${status.port}` : '○ kapalı'}
            </span>
          )}
          {status && !status.running && (
            <button
              onClick={startOpenCode}
              disabled={starting}
              className="rounded border border-cyan-800/50 bg-cyan-950/30 px-3 py-1 text-xs text-cyan-300 hover:bg-cyan-900/40 disabled:opacity-50 transition-colors"
            >
              {starting ? 'Başlatılıyor...' : 'Başlat'}
            </button>
          )}
          {status?.running && status.url && (
            <a
              href={status.url}
              target="_blank"
              rel="noreferrer"
              className="rounded border border-green-800/40 bg-green-950/20 px-3 py-1 text-xs text-green-300 hover:bg-green-900/30 transition-colors"
            >
              Yeni sekmede aç ↗
            </a>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="border-b border-red-900/40 bg-red-950/20 px-6 py-2 text-xs text-red-300">
          {error}
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 relative">
        {status?.running && status.url ? (
          <iframe
            src={status.url}
            className="absolute inset-0 h-full w-full border-0"
            title="OpenCode Terminal"
            allow="clipboard-read; clipboard-write"
          />
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-6 text-center">
            <div className="space-y-1">
              <div className="text-4xl font-bold tracking-widest text-gray-700">
                OPENCODE
              </div>
              <div className="text-xs text-gray-600">
                AI-powered terminal coding assistant
              </div>
            </div>
            {!status && (
              <div className="text-xs text-gray-600 animate-pulse">
                Bridge bağlantısı kontrol ediliyor...
              </div>
            )}
            {status && !status.running && (
              <div className="space-y-3">
                <p className="text-sm text-gray-500">
                  OpenCode şu an çalışmıyor.
                </p>
                <button
                  onClick={startOpenCode}
                  disabled={starting}
                  className="rounded-lg border border-cyan-700/50 bg-cyan-950/40 px-6 py-2.5 text-sm font-medium text-cyan-300 hover:bg-cyan-900/50 disabled:opacity-50 transition-colors"
                >
                  {starting ? 'Başlatılıyor...' : 'OpenCode Başlat'}
                </button>
                <p className="text-[11px] text-gray-700">
                  Port: {status.port} | opencode serve
                </p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
