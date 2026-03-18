const allowed = {
    idle: ["running", "blocked", "done"],
    running: ["blocked", "done", "idle"],
    blocked: ["idle", "running"],
    done: []
};
export function validateTransitions(current, transitions) {
    let mode = current.mode;
    for (const t of transitions) {
        if (t.type !== "SET_MODE") {
            continue;
        }
        if (t.mode === mode) {
            continue;
        }
        if (!allowed[mode].includes(t.mode)) {
            return { ok: false, reason: `ILLEGAL_TRANSITION:${mode}->${t.mode}` };
        }
        mode = t.mode;
    }
    return { ok: true };
}
