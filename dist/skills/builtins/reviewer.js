export const reviewerSkill = {
    id: "reviewer",
    version: "1",
    status: "APPROVED",
    manifest: {
        permissions: [{ type: "READ", resource: "memory:runs/*" }]
    },
    async run(input) {
        const content = typeof input === "object" && input && "content" in input
            ? String(input.content)
            : "";
        const passed = content.length > 8;
        return {
            status: passed ? "PASSED" : "FAILED",
            feedback: passed ? "Quality check successful" : "Content too short"
        };
    }
};
