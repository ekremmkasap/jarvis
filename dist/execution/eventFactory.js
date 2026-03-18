let seq = 0;
function eid() {
    seq = (seq + 1) % 1_000_000;
    return `${Date.now().toString(36)}-${seq.toString(36)}-${Math.random().toString(36).slice(2, 8)}`;
}
export function makeEvent(ctx, event) {
    return {
        ...event,
        id: eid(),
        at: Date.now(),
        runId: ctx.runId,
        parentId: ctx.parentId
    };
}
