import { RuntimeState, StateSnapshot } from "../contracts/types";
import { StateTransition } from "../execution/ExecutionResult";

export class State {
  private snapshot: StateSnapshot;

  constructor(initial: RuntimeState) {
    this.snapshot = { state: initial };
  }

  getSnapshot(): StateSnapshot {
    return this.snapshot;
  }

  setSnapshot(next: StateSnapshot): void {
    this.snapshot = next;
  }

  applyTransitions(snapshot: StateSnapshot, transitions: StateTransition[]): StateSnapshot {
    let next: RuntimeState = snapshot.state;
    for (const t of transitions) {
      if (t.type === "NOOP") {
        continue;
      }
      if (t.type === "SET_MODE") {
        next = { ...next, mode: t.mode };
        continue;
      }
      if (t.type === "PATCH") {
        next = { ...next, ...(t.patch as Record<string, unknown>) };
      }
    }
    return { state: next };
  }
}
