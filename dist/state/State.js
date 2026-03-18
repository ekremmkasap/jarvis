export class State {
    snapshot;
    constructor(initial) {
        this.snapshot = { state: initial };
    }
    getSnapshot() {
        return this.snapshot;
    }
    setSnapshot(next) {
        this.snapshot = next;
    }
    applyTransitions(snapshot, transitions) {
        let next = snapshot.state;
        for (const t of transitions) {
            if (t.type === "NOOP") {
                continue;
            }
            if (t.type === "SET_MODE") {
                next = { ...next, mode: t.mode };
                continue;
            }
            if (t.type === "PATCH") {
                next = { ...next, ...t.patch };
            }
        }
        return { state: next };
    }
}
