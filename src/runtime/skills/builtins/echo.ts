import { Skill } from "../Skill";
import { ExecutionRequest } from "../../executor/types";

export const echoSkill: Skill = {
  id: "echo",
  version: "1",
  status: "APPROVED",
  manifest: {
    permissions: [
      { type: "WRITE", resource: "memory:runs/*" },
      { type: "WRITE", resource: "memory:project/*" }
    ]
  },
  async run(input: unknown) {
    const message = typeof input === "object" && input && "message" in input
      ? String((input as { message: unknown }).message)
      : "";
    return { echoed: message };
  },
  buildMemoryWrites(req: ExecutionRequest, output: unknown) {
    return [
      {
        type: "WRITE" as const,
        key: `runs.${req.runId}.lastOutput`,
        value: output
      },
      {
        type: "WRITE" as const,
        key: "project.echo.examples",
        value: { input: req.input, output },
        requiresApproval: true,
        reason: "Skill example persistence"
      }
    ];
  }
};
