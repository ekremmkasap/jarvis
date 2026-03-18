import { Dispatcher } from "../dispatcher";
import { Executor } from "../executor";
import { Gates } from "../gates/Gates";
import { State } from "../state/State";
import { Memory } from "../memory/Memory";
import { SkillRegistry } from "../skills/SkillRegistry";
import { echoSkill } from "../skills/builtins/echo";
import { plannerSkill } from "../skills/builtins/planner";
import { implementerSkill } from "../skills/builtins/implementer";
import { reviewerSkill } from "../skills/builtins/reviewer";
import { curatorSkill } from "../skills/builtins/curator";
import { autoUploaderSkill } from "../skills/builtins/auto_uploader";
import { dynamicContentShufflerSkill } from "../skills/builtins/dynamic_content_shuffler";
import { engagementLoopSkill } from "../skills/builtins/engagement_loop";

async function main() {
  const registry = new SkillRegistry();
  registry.register(echoSkill);
  registry.register(plannerSkill);
  registry.register(implementerSkill);
  registry.register(reviewerSkill);
  registry.register(curatorSkill);
  registry.register(autoUploaderSkill);
  registry.register(dynamicContentShufflerSkill);
  registry.register(engagementLoopSkill);

  const executor = new Executor(registry);
  const gates = new Gates();
  const state = new State({ mode: "idle" });
  const memory = new Memory();
  const dispatcher = new Dispatcher(executor, gates, state, memory);

  const echoResult = await dispatcher.dispatch({
    runId: "dev-echo-1",
    skillId: "echo",
    skillVersion: "1",
    input: { message: "hello world" }
  });

  const planResult = await dispatcher.dispatch({
    runId: "dev-plan-1",
    skillId: "planner",
    skillVersion: "1",
    input: { goal: "Build initial mission-control phase" }
  });

  const shufflerResult = await dispatcher.dispatch({
    runId: "dev-shuffle-1",
    skillId: "dynamic_content_shuffler",
    skillVersion: "1",
    input: {
      seed: 42,
      targetVideos: 3,
      clipsPerVideo: 3,
      minSegmentSec: 3,
      maxSegmentSec: 9,
      rawClips: [
        { id: "c1", durationSec: 28 },
        { id: "c2", durationSec: 33 },
        { id: "c3", durationSec: 22 },
        { id: "c4", durationSec: 45 },
        { id: "c5", durationSec: 19 }
      ]
    }
  });

  const engagementResult = await dispatcher.dispatch({
    runId: "dev-engage-1",
    skillId: "engagement_loop",
    skillVersion: "1",
    input: {
      seed: 7,
      maxActionsPerPersona: 3,
      personas: [
        { id: "p1", handle: "@alpha" },
        { id: "p2", handle: "@bravo" },
        { id: "p3", handle: "@charlie" },
        { id: "p4", handle: "@delta" }
      ],
      targetVideoIds: ["video_1", "video_2", "video_3"]
    }
  });

  const uploaderResult = await dispatcher.dispatch({
    runId: "dev-upload-1",
    skillId: "auto_uploader",
    skillVersion: "1",
    input: {
      mode: "ghost",
      dryRun: true,
      items: [
        { filePath: "outputs/video_1.mp4", caption: "Drop 1 #streetwear", platform: "tiktok" },
        { filePath: "outputs/video_2.mp4", caption: "Drop 2 #fashion", platform: "reels" }
      ]
    }
  });

  console.log("ECHO RESULT", {
    accepted: echoResult.accepted,
    ok: echoResult.ok,
    payload: echoResult.payload ?? null,
    state: echoResult.snapshot?.state ?? null,
    events: echoResult.events.length,
    error: echoResult.error ?? null
  });

  console.log("PLAN RESULT", {
    accepted: planResult.accepted,
    ok: planResult.ok,
    payload: planResult.payload ?? null,
    state: planResult.snapshot?.state ?? null,
    events: planResult.events.length,
    error: planResult.error ?? null
  });

  console.log("RUN MEMORY", memory.dump("runs"));
  console.log("PROJECT MEMORY", memory.dump("project"));
  console.log("PENDING MEMORY", memory.getPending());

  console.log("SHUFFLER RESULT", {
    accepted: shufflerResult.accepted,
    ok: shufflerResult.ok,
    produced: (shufflerResult.payload?.output as { producedVideos?: number } | undefined)?.producedVideos ?? 0
  });

  console.log("ENGAGEMENT RESULT", {
    accepted: engagementResult.accepted,
    ok: engagementResult.ok,
    actions: (engagementResult.payload?.output as { actionsCount?: number } | undefined)?.actionsCount ?? 0
  });

  console.log("UPLOADER RESULT", {
    accepted: uploaderResult.accepted,
    ok: uploaderResult.ok,
    queue: (uploaderResult.payload?.output as { queueSize?: number } | undefined)?.queueSize ?? 0
  });
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
