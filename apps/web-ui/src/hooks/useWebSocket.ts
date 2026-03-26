import { useEffect, useRef } from 'react';
import { useJarvisStore } from './useJarvisStore';

export function useWebSocket(url: string) {
  const ws = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const { addTask, updateTask, addNotification, setConnected } = useJarvisStore();

  const connect = () => {
    try {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        setConnected(true);
        addNotification({
          type: 'success',
          message: 'Connected to Jarvis Orchestrator',
          timestamp: new Date().toISOString(),
        });
        // Keepalive
        const ping = setInterval(() => {
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send('ping');
          }
        }, 25000);
        (ws.current as any)._ping = ping;
      };

      ws.current.onmessage = ({ data }) => {
        if (data === 'pong') return;
        try {
          handleEvent(JSON.parse(data));
        } catch {}
      };

      ws.current.onclose = () => {
        setConnected(false);
        clearInterval((ws.current as any)?._ping);
        reconnectTimer.current = setTimeout(connect, 3000);
      };

      ws.current.onerror = () => ws.current?.close();
    } catch {}
  };

  const handleEvent = (data: any) => {
    const { event, task } = data;
    switch (event) {
      case 'task_created':
        addTask(task);
        addNotification({
          type: 'info',
          message: `Task ${task.id} → ${task.agent}: ${task.goal.slice(0, 50)}`,
          timestamp: new Date().toISOString(),
        });
        break;
      case 'task_started':
        updateTask(task);
        addNotification({
          type: 'info',
          message: `[${task.agent}] started task ${task.id}`,
          timestamp: new Date().toISOString(),
        });
        break;
      case 'task_updated':
      case 'task_confirmed':
        updateTask(task);
        if (task.status === 'done') {
          addNotification({
            type: 'success',
            message: `✓ Task ${task.id} done (${task.agent})`,
            timestamp: new Date().toISOString(),
          });
        } else if (task.status === 'failed') {
          addNotification({
            type: 'error',
            message: `✗ Task ${task.id} failed: ${(task.error || '').slice(0, 80)}`,
            timestamp: new Date().toISOString(),
          });
        }
        break;
      case 'task_retry':
        updateTask(task);
        addNotification({
          type: 'warning',
          message: `↻ Retrying task ${task.id} (attempt ${task.retries})`,
          timestamp: new Date().toISOString(),
        });
        break;
    }
  };

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      ws.current?.close();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url]);
}
