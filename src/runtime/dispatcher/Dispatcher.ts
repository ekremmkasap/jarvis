import { Executor } from "../executor";
import { ExecutionRequest } from "../executor/types";
import { Gates } from "../gates/Gates";
import { State } from "../state/State";
import { Memory } from "../memory/Memory";
import { makeEvent } from "../execution/eventFactory";
import { ExecutionResult } from "../execution/ExecutionResult";

export type DispatchResult = {
  accepted: boolean;
  ok: boolean;
  payload?: ExecutionResult["payload"];
  snapshot?: { state: Record<string, unknown> };
  events: ExecutionResult["events"];
  error?: string;
};

export class Dispatcher {
  constructor(
    private executor: Executor,
    private gates: Gates,
    private state: State,
    private memory: Memory
  ) {}

  async dispatch(req: ExecutionRequest): Promise<DispatchResult> {
    const before = this.state.getSnapshot();
    const execResult = await this.executor.execute(req);

    let parentId = execResult.events.length ? execResult.events[execResult.events.length - 1].id : undefined;
    const decision = this.gates.evaluate(execResult, before.state);
    execResult.events.push(
      makeEvent(
        { runId: req.runId, parentId },
        { type: "GATE_DECISION", gate: "default", allowed: decision.allowed, reason: decision.reason }
      )
    );

    if (!decision.allowed) {
      return {
        accepted: false,
        ok: false,
        events: execResult.events,
        snapshot: before as unknown as { state: Record<string, unknown> },
        error: decision.reason
      };
    }

    const after = this.state.applyTransitions(before, execResult.transitions);
    this.state.setSnapshot(after);
    parentId = execResult.events[execResult.events.length - 1]?.id;
    execResult.events.push(makeEvent({ runId: req.runId, parentId }, { type: "STATE_TRANSITION_APPLIED" }));

    for (const w of execResult.memoryWrites) {
      this.memory.write(w);
      parentId = execResult.events[execResult.events.length - 1]?.id;
      execResult.events.push(makeEvent({ runId: req.runId, parentId }, { type: "MEMORY_WRITE_QUEUED", key: w.key }));
    }

    return {
      accepted: true,
      ok: execResult.ok,
      payload: execResult.payload,
      snapshot: after as unknown as { state: Record<string, unknown> },
      events: execResult.events,
      error: execResult.error
    };
  }
}
