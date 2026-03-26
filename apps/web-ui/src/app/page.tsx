'use client';

import { useJarvisStore } from '@/hooks/useJarvisStore';
import { useWebSocket } from '@/hooks/useWebSocket';
import TaskPanel from '@/components/TaskPanel';
import AgentGraph from '@/components/AgentGraph';
import VoiceIndicator from '@/components/VoiceIndicator';
import CommandConsole from '@/components/CommandConsole';
import StatsBar from '@/components/StatsBar';
import NotificationsPanel from '@/components/NotificationsPanel';

const ORCHESTRATOR_WS = process.env.NEXT_PUBLIC_ORCHESTRATOR_WS || 'ws://localhost:8091/ws';

export default function Dashboard() {
  const { tasks, notifications, agentNodes } = useJarvisStore();
  useWebSocket(ORCHESTRATOR_WS);

  return (
    <div className="min-h-screen bg-gray-950 text-green-400 font-mono flex flex-col select-none">
      {/* Header */}
      <header className="border-b border-green-900/40 px-6 py-3 flex items-center justify-between bg-gray-950/90 backdrop-blur sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
          <span className="text-lg font-bold tracking-widest text-green-300 uppercase">
            Jarvis Mission Control
          </span>
          <span className="text-[10px] text-green-800 border border-green-900 px-1.5 py-0.5 rounded">
            v2.0
          </span>
        </div>
        <StatsBar />
        <VoiceIndicator />
      </header>

      {/* Body */}
      <div className="flex-1 grid grid-cols-12 overflow-hidden" style={{ height: 'calc(100vh - 52px)' }}>
        {/* Agent Graph */}
        <div className="col-span-5 border-r border-green-900/30 flex flex-col overflow-hidden">
          <div className="px-4 py-2 border-b border-green-900/20 text-[10px] text-green-700 uppercase tracking-widest">
            Agent Network
          </div>
          <div className="flex-1 overflow-hidden">
            <AgentGraph nodes={agentNodes} />
          </div>
        </div>

        {/* Task Queue */}
        <div className="col-span-4 border-r border-green-900/30 flex flex-col overflow-hidden">
          <div className="px-4 py-2 border-b border-green-900/20 text-[10px] text-green-700 uppercase tracking-widest">
            Mission Queue ({tasks.length})
          </div>
          <div className="flex-1 overflow-y-auto">
            <TaskPanel tasks={tasks} />
          </div>
        </div>

        {/* Right panel */}
        <div className="col-span-3 flex flex-col overflow-hidden">
          <div className="flex-1 border-b border-green-900/30 flex flex-col overflow-hidden min-h-0">
            <div className="px-4 py-2 border-b border-green-900/20 text-[10px] text-green-700 uppercase tracking-widest">
              Command Console
            </div>
            <CommandConsole />
          </div>
          <div className="h-56 flex flex-col overflow-hidden">
            <div className="px-4 py-2 border-b border-green-900/20 text-[10px] text-green-700 uppercase tracking-widest">
              Notifications ({notifications.length})
            </div>
            <NotificationsPanel notifications={notifications} />
          </div>
        </div>
      </div>
    </div>
  );
}
