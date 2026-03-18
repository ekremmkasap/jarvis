import { Skill } from "../Skill";
import { ExecutionRequest } from "../../executor/types";

export const curatorSkill: Skill = {
  id: "curator",
  version: "1",
  status: "APPROVED",
  manifest: {
    permissions: [{ type: "WRITE", resource: "memory:project/*" }]
  },
  async run(input: unknown) {
    const artifact = typeof input === "object" && input && "artifact" in input
      ? String((input as { artifact: unknown }).artifact)
      : "unknown";
    return {
      status: "memorized",
      storedKey: `project.artifacts.${artifact.replace(/\./g, "_")}`
    };
  },
  buildMemoryWrites(req: ExecutionRequest, output: unknown) {
    const out = output as { storedKey?: string };
    return [
      {
        type: "WRITE" as const,
        key: out.storedKey ?? "project.artifacts.unknown",
        value: { input: req.input, storedAt: Date.now() },
        requiresApproval: true,
        reason: "Strategic artifact archival"
      }
    ];
  }
};
