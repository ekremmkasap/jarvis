'use client';
import { useJarvisStore } from '@/hooks/useJarvisStore';

export default function StatsBar() {
  const { tasks } = useJarvisStore();
  const count = (s: string) => tasks.filter((t) => t.status === s).length;

  return (
    <div className="flex items-center gap-4 text-xs">
      <span className="text-blue-400">{count('running')} running</span>
      <span className="text-yellow-400">{count('queued')} queued</span>
      <span className="text-green-500">{count('done')} done</span>
      {count('failed') > 0 && <span className="text-red-400">{count('failed')} failed</span>}
      {count('awaiting_confirmation') > 0 && (
        <span className="text-orange-400">{count('awaiting_confirmation')} pending confirm</span>
      )}
    </div>
  );
}
