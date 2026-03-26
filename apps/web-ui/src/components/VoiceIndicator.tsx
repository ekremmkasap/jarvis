'use client';
import { useJarvisStore } from '@/hooks/useJarvisStore';

export default function VoiceIndicator() {
  const { connected, voiceActive } = useJarvisStore();

  return (
    <div className="flex items-center gap-4 text-xs">
      <span className={`flex items-center gap-1.5 ${connected ? 'text-green-400' : 'text-red-500'}`}>
        <span className={`w-1.5 h-1.5 rounded-full inline-block ${connected ? 'bg-green-400 animate-pulse' : 'bg-red-500'}`} />
        {connected ? 'ONLINE' : 'OFFLINE'}
      </span>
      <span className={`flex items-center gap-1.5 ${voiceActive ? 'text-blue-400' : 'text-green-900'}`}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
          <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
          <line x1="12" y1="19" x2="12" y2="23" />
          <line x1="8" y1="23" x2="16" y2="23" />
        </svg>
        {voiceActive ? 'LISTENING' : 'HEY JARVIS'}
      </span>
    </div>
  );
}
