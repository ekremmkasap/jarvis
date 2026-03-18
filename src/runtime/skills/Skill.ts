import { ExecutionRequest } from "../executor/types";
import { MemoryWrite, Permission } from "../execution/ExecutionResult";

export type SkillStatus = "APPROVED" | "DRAFT" | "DISABLED";

export type SkillManifest = {
  permissions: Permission[];
};

export type Skill = {
  id: string;
  version: string;
  status: SkillStatus;
  manifest: SkillManifest;
  run(input: unknown, ctx: { runId: string }): Promise<unknown>;
  buildMemoryWrites?(req: ExecutionRequest, output: unknown): MemoryWrite[];
};
