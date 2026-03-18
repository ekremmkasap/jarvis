export type TaskStatus =
  | "queued"
  | "planning"
  | "running"
  | "waiting"
  | "blocked"
  | "done"
  | "failed"
  | "cancelled";

export type RuntimeMode = "idle" | "running" | "blocked" | "done";

export type RuntimeState = {
  mode: RuntimeMode;
  lastSkill?: string;
  lastRunId?: string;
  [k: string]: unknown;
};

export type StateSnapshot = {
  state: RuntimeState;
};

export type Task = {
  id: string;
  title: string;
  goal: string;
  constraints: string[];
  inputs: Record<string, unknown>;
  acceptanceCriteria: string[];
  status: TaskStatus;
};
