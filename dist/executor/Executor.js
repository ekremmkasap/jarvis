import { makeEvent } from "../execution/eventFactory";
export class Executor {
    registry;
    constructor(registry) {
        this.registry = registry;
    }
    async execute(req) {
        const events = [];
        const started = makeEvent({ runId: req.runId }, { type: "EXECUTOR_STARTED" });
        events.push(started);
        let parentId = started.id;
        const selected = makeEvent({ runId: req.runId, parentId }, { type: "SKILL_SELECTED", skill: req.skillId });
        events.push(selected);
        parentId = selected.id;
        const skill = this.registry.get(req.skillId);
        if (!skill) {
            return {
                ok: false,
                accepted: false,
                transitions: [{ type: "SET_MODE", mode: "blocked" }],
                memoryWrites: [],
                requiredPermissions: [],
                events,
                error: `SKILL_NOT_FOUND:${req.skillId}`
            };
        }
        try {
            const output = await skill.run(req.input, { runId: req.runId });
            events.push(makeEvent({ runId: req.runId, parentId }, { type: "SKILL_EXECUTED", skill: req.skillId, ok: true }));
            const memoryWrites = skill.buildMemoryWrites ? skill.buildMemoryWrites(req, output) : [];
            return {
                ok: true,
                accepted: true,
                payload: { skill: req.skillId, output },
                transitions: [
                    { type: "SET_MODE", mode: "running" },
                    { type: "PATCH", patch: { lastSkill: req.skillId, lastRunId: req.runId } }
                ],
                memoryWrites,
                requiredPermissions: skill.manifest.permissions,
                events
            };
        }
        catch (err) {
            const msg = err instanceof Error ? err.message : String(err);
            events.push(makeEvent({ runId: req.runId, parentId }, { type: "SKILL_EXECUTED", skill: req.skillId, ok: false, error: msg }));
            return {
                ok: false,
                accepted: false,
                transitions: [{ type: "SET_MODE", mode: "blocked" }],
                memoryWrites: [],
                requiredPermissions: [],
                events,
                error: msg
            };
        }
    }
}
