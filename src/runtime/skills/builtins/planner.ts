import { Skill } from "../Skill";

export const plannerSkill: Skill = {
  id: "planner",
  version: "1",
  status: "APPROVED",
  manifest: {
    permissions: [{ type: "WRITE", resource: "memory:runs/*" }]
  },
  async run(input: unknown) {
    const goal = typeof input === "object" && input && "goal" in input ? String((input as { goal: unknown }).goal) : "unknown";
    return {
      goal,
      tasks: [
        { id: "t1", title: "Context discovery", status: "queued", dependencies: [] },
        { id: "t2", title: "Implementation", status: "queued", dependencies: ["t1"] },
        { id: "t3", title: "Review", status: "queued", dependencies: ["t2"] }
      ]
    };
  }
};
