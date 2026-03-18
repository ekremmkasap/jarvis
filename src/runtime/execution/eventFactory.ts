import { RuntimeEvent } from "./ExecutionResult";

let seq = 0;

function eid(): string {
  seq = (seq + 1) % 1_000_000;
  return `${Date.now().toString(36)}-${seq.toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}

export type EventCtx = {
  runId: string;
  parentId?: string;
};

export function makeEvent<T extends Omit<RuntimeEvent, "id" | "at" | "runId" | "parentId">>(
  ctx: EventCtx,
  event: T
): RuntimeEvent {
  return {
    ...(event as unknown as object),
    id: eid(),
    at: Date.now(),
    runId: ctx.runId,
    parentId: ctx.parentId
  } as RuntimeEvent;
}
