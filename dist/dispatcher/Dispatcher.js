import { makeEvent } from "../execution/eventFactory";
export class Dispatcher {
    executor;
    gates;
    state;
    memory;
    constructor(executor, gates, state, memory) {
        this.executor = executor;
        this.gates = gates;
        this.state = state;
        this.memory = memory;
    }
    async dispatch(req) {
        const before = this.state.getSnapshot();
        const execResult = await this.executor.execute(req);
        let parentId = execResult.events.length ? execResult.events[execResult.events.length - 1].id : undefined;
        const decision = this.gates.evaluate(execResult, before.state);
        execResult.events.push(makeEvent({ runId: req.runId, parentId }, { type: "GATE_DECISION", gate: "default", allowed: decision.allowed, reason: decision.reason }));
        if (!decision.allowed) {
            return {
                accepted: false,
                ok: false,
                events: execResult.events,
                snapshot: before,
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
            snapshot: after,
            events: execResult.events,
            error: execResult.error
        };
    }
}
