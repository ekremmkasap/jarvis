export const autoUploaderSkill = {
    id: "auto_uploader",
    version: "1",
    status: "APPROVED",
    manifest: {
        permissions: [
            { type: "NET", resource: "https://*.tiktok.com/*" },
            { type: "NET", resource: "https://graph.instagram.com/*" },
            { type: "WRITE", resource: "memory:runs/*" }
        ]
    },
    async run(input) {
        const p = input;
        const queue = p.items.map((item, i) => ({
            id: `upload_${i + 1}`,
            ...item,
            mode: p.mode,
            status: p.dryRun ? "simulated" : "queued",
            method: p.mode === "ghost" ? "browser_automation" : "official_api"
        }));
        return {
            status: "prepared",
            dryRun: p.dryRun,
            queueSize: queue.length,
            queue
        };
    },
    buildMemoryWrites(req, output) {
        return [
            {
                type: "WRITE",
                key: `runs.${req.runId}.uploader.queue`,
                value: output
            }
        ];
    }
};
