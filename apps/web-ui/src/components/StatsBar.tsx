'use client';
import { useJarvisStore } from '@/hooks/useJarvisStore';

type QueueSnapshot = {
  queued_tasks?: number;
  running_tasks?: number;
  awaiting_confirmation_tasks?: number;
  done_tasks?: number;
  failed_tasks?: number;
};

type StatsBarProps = {
  health?: {
    live?: {
      queue_snapshot?: QueueSnapshot | null;
    } | null;
  } | null;
};

export default function StatsBar({ health }: StatsBarProps = {}) {
  const { tasks } = useJarvisStore();
  const snapshot = health?.live?.queue_snapshot;

  const count = (status: string) => {
    if (snapshot) {
      switch (status) {
        case 'running':
          return snapshot.running_tasks ?? 0;
        case 'queued':
          return snapshot.queued_tasks ?? 0;
        case 'done':
          return snapshot.done_tasks ?? 0;
        case 'failed':
          return snapshot.failed_tasks ?? 0;
        case 'awaiting_confirmation':
          return snapshot.awaiting_confirmation_tasks ?? 0;
        default:
          return 0;
      }
    }
    return tasks.filter((task) => task.status === status).length;
  };

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
