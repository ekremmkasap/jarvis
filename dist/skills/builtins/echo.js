export const echoSkill = {
    id: "echo",
    version: "1",
    status: "APPROVED",
    manifest: {
        permissions: [
            { type: "WRITE", resource: "memory:runs/*" },
            { type: "WRITE", resource: "memory:project/*" }
        ]
    },
    async run(input) {
        const message = typeof input === "object" && input && "message" in input
            ? String(input.message)
            : "";
        return { echoed: message };
    },
    buildMemoryWrites(req, output) {
        return [
            {
                type: "WRITE",
                key: `runs.${req.runId}.lastOutput`,
                value: output
            },
            {
                type: "WRITE",
                key: "project.echo.examples",
                value: { input: req.input, output },
                requiresApproval: true,
                reason: "Skill example persistence"
            }
        ];
    }
};
