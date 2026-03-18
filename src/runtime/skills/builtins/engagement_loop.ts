import { Skill } from "../Skill";
import { ExecutionRequest } from "../../executor/types";

type Persona = {
  id: string;
  handle: string;
};

type EngagementInput = {
  seed: number;
  maxActionsPerPersona: number;
  personas: Persona[];
  targetVideoIds: string[];
};

function rng(seed: number): () => number {
  let s = seed >>> 0;
  return () => {
    s = (1664525 * s + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

function shuffle<T>(arr: T[], rand: () => number): T[] {
  const out = [...arr];
  for (let i = out.length - 1; i > 0; i -= 1) {
    const j = Math.floor(rand() * (i + 1));
    [out[i], out[j]] = [out[j], out[i]];
  }
  return out;
}

export const engagementLoopSkill: Skill = {
  id: "engagement_loop",
  version: "1",
  status: "APPROVED",
  manifest: {
    permissions: [{ type: "WRITE", resource: "memory:runs/*" }]
  },
  async run(input: unknown) {
    const p = input as EngagementInput;
    const rand = rng(Number(p.seed || 1));
    const actions = [] as Array<{
      actor: string;
      action: "follow" | "comment" | "boost";
      targetPersona?: string;
      targetVideo?: string;
      text?: string;
    }>;

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
  buildMemoryWrites(req: ExecutionRequest, output: unknown) {
    return [
      {
        type: "WRITE" as const,
        key: `runs.${req.runId}.engagement.actions`,
        value: output
      }
    ];
  }
};
