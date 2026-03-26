'use client';
import { Notification } from '@/hooks/useJarvisStore';

const TYPE_COLOR: Record<Notification['type'], string> = {
  info:    'text-blue-400',
  success: 'text-green-400',
  warning: 'text-yellow-400',
  error:   'text-red-400',
};

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

export default function NotificationsPanel({ notifications }: { notifications: Notification[] }) {
  if (!notifications.length) {
    return <div className="text-green-900 text-xs text-center py-4">No notifications</div>;
  }

  return (
    <div className="overflow-y-auto flex-1 p-2 space-y-1">
      {notifications.map((n) => (
        <div key={n.id} className="text-xs border-l-2 border-green-900/30 pl-2">
          <span className={TYPE_COLOR[n.type]}>{n.message}</span>
          <div className="text-green-900 text-[10px]">{timeAgo(n.timestamp)}</div>
        </div>
      ))}
    </div>
  );
}
