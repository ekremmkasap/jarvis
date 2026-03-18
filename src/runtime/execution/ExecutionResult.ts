export type EventBase = {
  id: string;
  runId: string;
  at: number;
  parentId?: string;
};

export type RuntimeEvent =
  | (EventBase & { type: "EXECUTOR_STARTED" })
  | (EventBase & { type: "SKILL_SELECTED"; skill: string })
  | (EventBase & { type: "SKILL_EXECUTED"; skill: string; ok: true })
  | (EventBase & { type: "SKILL_EXECUTED"; skill: string; ok: false; error: string })
  | (EventBase & { type: "GATE_DECISION"; gate: string; allowed: boolean; reason?: string })
  | (EventBase & { type: "STATE_TRANSITION_APPLIED" })
  | (EventBase & { type: "MEMORY_WRITE_QUEUED"; key: string });

export type StateTransition =
  | { type: "NOOP" }
  | { type: "SET_MODE"; mode: "idle" | "running" | "blocked" | "done" }
  | { type: "PATCH"; patch: Record<string, unknown> };

export type MemoryWrite = {
  type: "WRITE";
  key: string;
  value: unknown;
  requiresApproval?: boolean;
  reason?: string;
};

export type Permission =
  | { type: "READ"; resource: string }
  | { type: "WRITE"; resource: string }
  | { type: "NET"; resource: string };

export type ExecutionPayload = {
  skill: string;
  output: unknown;
};

export type ExecutionResult = {
  ok: boolean;
  accepted: boolean;
  payload?: ExecutionPayload;
  transitions: StateTransition[];
  memoryWrites: MemoryWrite[];
  requiredPermissions: Permission[];
  events: RuntimeEvent[];
  error?: string;
};
