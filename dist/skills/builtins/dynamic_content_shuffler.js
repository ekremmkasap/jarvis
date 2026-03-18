function rng(seed) {
    let s = seed >>> 0;
    return () => {
        s ^= s << 13;
        s ^= s >>> 17;
        s ^= s << 5;
        return (s >>> 0) / 4294967296;
    };
}
function pickInt(rand, min, max) {
    return Math.floor(rand() * (max - min + 1)) + min;
}
export const dynamicContentShufflerSkill = {
    id: "dynamic_content_shuffler",
    version: "1",
    status: "APPROVED",
    manifest: {
        permissions: [{ type: "WRITE", resource: "memory:runs/*" }]
    },
    async run(input) {
        const p = input;
        const rand = rng(Number(p.seed || 1));
        const videos = [];
        for (let i = 0; i < p.targetVideos; i += 1) {
            const used = new Set();
            const segments = [];
            for (let j = 0; j < p.clipsPerVideo; j += 1) {
                const candidates = p.rawClips.filter((c) => c.durationSec >= p.minSegmentSec + 1 && !used.has(c.id));
                if (candidates.length === 0) {
                    break;
                }
                const clip = candidates[pickInt(rand, 0, candidates.length - 1)];
                used.add(clip.id);
                const segLen = pickInt(rand, p.minSegmentSec, Math.min(p.maxSegmentSec, clip.durationSec - 1));
                const startMax = Math.max(0, clip.durationSec - segLen);
                const startSec = pickInt(rand, 0, startMax);
                const endSec = startSec + segLen;
                segments.push({ clipId: clip.id, startSec, endSec });
            }
            const uniquenessHash = segments.map((s) => `${s.clipId}:${s.startSec}-${s.endSec}`).join("|");
            videos.push({
                videoId: `video_${i + 1}`,
                uniquenessHash,
                segments
            });
        }
        return {
            status: "generated",
            targetVideos: p.targetVideos,
            producedVideos: videos.length,
            videos
        };
    },
    buildMemoryWrites(req, output) {
        return [
            {
                type: "WRITE",
                key: `runs.${req.runId}.shuffler.plan`,
                value: output
            }
        ];
    }
};
