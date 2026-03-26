import { create } from 'zustand';

export type TaskStatus =
  | 'queued'
  | 'running'
  | 'done'
  | 'failed'
  | 'pending'
  | 'awaiting_confirmation';

export interface Task {
  id: string;
  goal: string;
  agent: string;
  status: TaskStatus;
  priority: string;
  created_at: string;
  started_at?: string;
  finished_at?: string;
  result?: string;
  error?: string;
  requires_confirmation?: boolean;
  retries?: number;
}

export interface AgentNode {
  id: string;
  name: string;
  status: 'idle' | 'active' | 'error';
  task_count: number;
}

export interface Notification {
  id: string;
  type: 'info' | 'success' | 'warning' | 'error';
  message: string;
  timestamp: string;
}

interface JarvisState {
  tasks: Task[];
  agentNodes: AgentNode[];
  notifications: Notification[];
  connected: boolean;
  voiceActive: boolean;

  addTask: (task: Task) => void;
  updateTask: (task: Task) => void;
  addNotification: (n: Omit<Notification, 'id'>) => void;
  setConnected: (v: boolean) => void;
  setVoiceActive: (v: boolean) => void;
}

const DEFAULT_NODES: AgentNode[] = [
  { id: 'planner', name: 'Planner', status: 'idle', task_count: 0 },
  { id: 'repo_analyst', name: 'RepoAnalyst', status: 'idle', task_count: 0 },
  { id: 'developer', name: 'Developer', status: 'idle', task_count: 0 },
  { id: 'reviewer', name: 'Reviewer', status: 'idle', task_count: 0 },
  { id: 'debug', name: 'Debug', status: 'idle', task_count: 0 },
  { id: 'release', name: 'Release', status: 'idle', task_count: 0 },
  { id: 'docs', name: 'Docs', status: 'idle', task_count: 0 },
  { id: 'voice_narrator', name: 'VoiceNarrator', status: 'idle', task_count: 0 },
  { id: 'mission_control', name: 'MissionControl', status: 'idle', task_count: 0 },
];

export const useJarvisStore = create<JarvisState>((set) => ({
  tasks: [],
  agentNodes: DEFAULT_NODES,
  notifications: [],
  connected: false,
  voiceActive: false,

  addTask: (task) =>
    set((s) => ({ tasks: [task, ...s.tasks].slice(0, 100) })),

  updateTask: (task) =>
    set((s) => ({
      tasks: s.tasks.map((t) => (t.id === task.id ? { ...t, ...task } : t)),
      agentNodes: s.agentNodes.map((n) => {
        if (n.id !== task.agent) return n;
        const isActive = task.status === 'running';
        return { ...n, status: isActive ? 'active' : task.status === 'failed' ? 'error' : 'idle' };
      }),
    })),

  addNotification: (n) =>
    set((s) => ({
      notifications: [
        { ...n, id: `${Date.now()}-${Math.random().toString(36).slice(2)}` },
        ...s.notifications,
      ].slice(0, 50),
    })),

  setConnected: (connected) => set({ connected }),
  setVoiceActive: (voiceActive) => set({ voiceActive }),
}));
