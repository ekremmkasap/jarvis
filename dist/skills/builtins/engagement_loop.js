function rng(seed) {
    let s = seed >>> 0;
    return () => {
        s = (1664525 * s + 1013904223) >>> 0;
        return s / 4294967296;
    };
}
function shuffle(arr, rand) {
    const out = [...arr];
    for (let i = out.length - 1; i > 0; i -= 1) {
        const j = Math.floor(rand() * (i + 1));
        [out[i], out[j]] = [out[j], out[i]];
    }
    return out;
}
export const engagementLoopSkill = {
    id: "engagement_loop",
    version: "1",
    status: "APPROVED",
    manifest: {
        permissions: [{ type: "WRITE", resource: "memory:runs/*" }]
    },
    async run(input) {
        const p = input;
        const rand = rng(Number(p.seed || 1));
        const actions = [];
        const personas = shuffle(p.personas, rand);
        const videos = shuffle(p.targetVideoIds, rand);
        for (const persona of personas) {
            let budget = p.maxActionsPerPersona;
            const others = personas.filter((x) => x.id !== persona.id);
            const targetPersona = others[Math.floor(rand() * others.length)];
            if (budget > 0 && targetPersona) {
                actions.push({ actor: persona.handle, action: "follow", targetPersona: targetPersona.handle });
                budget -= 1;
            }
            if (budget > 0 && videos.length > 0) {
                const v = videos[Math.floor(rand() * videos.length)];
                actions.push({ actor: persona.handle, action: "comment", targetVideo: v, text: `Great cut on ${v}` });
                budget -= 1;
            }
            if (budget > 0 && videos.length > 0) {
                const v = videos[Math.floor(rand() * videos.length)];
                actions.push({ actor: persona.handle, action: "boost", targetVideo: v });
            }
        }
        return {
            status: "planned",
            actionsCount: actions.length,
            actions
        };
    },
    buildMemoryWrites(req, output) {
        return [
            {
                type: "WRITE",
                key: `runs.${req.runId}.engagement.actions`,
                value: output
            }
        ];
    }
};
