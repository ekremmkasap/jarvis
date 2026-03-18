export const curatorSkill = {
    id: "curator",
    version: "1",
    status: "APPROVED",
    manifest: {
        permissions: [{ type: "WRITE", resource: "memory:project/*" }]
    },
    async run(input) {
        const artifact = typeof input === "object" && input && "artifact" in input
            ? String(input.artifact)
            : "unknown";
        return {
            status: "memorized",
            storedKey: `project.artifacts.${artifact.replace(/\./g, "_")}`
        };
    },
    buildMemoryWrites(req, output) {
        const out = output;
        return [
            {
                type: "WRITE",
                key: out.storedKey ?? "project.artifacts.unknown",
                value: { input: req.input, storedAt: Date.now() },
                requiresApproval: true,
                reason: "Strategic artifact archival"
            }
        ];
    }
};
