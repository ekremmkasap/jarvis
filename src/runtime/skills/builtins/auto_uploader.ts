import { Skill } from "../Skill";
import { ExecutionRequest } from "../../executor/types";

type UploadItem = {
  filePath: string;
  caption: string;
  platform: "tiktok" | "reels";
};

type AutoUploaderInput = {
  mode: "ghost" | "api";
  dryRun: boolean;
  items: UploadItem[];
};

export const autoUploaderSkill: Skill = {
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
  async run(input: unknown) {
    const p = input as AutoUploaderInput;
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
  buildMemoryWrites(req: ExecutionRequest, output: unknown) {
    return [
      {
        type: "WRITE" as const,
        key: `runs.${req.runId}.uploader.queue`,
        value: output
      }
    ];
  }
};
