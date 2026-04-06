import { bridgeSkill } from "./BridgeSkill";
import { Skill } from "./Skill";

export class SkillRegistry {
  private skills = new Map<string, Skill>();

  constructor() {
    this.register(bridgeSkill);
  }

  register(skill: Skill): void {
    if (skill.status !== "APPROVED") {
      return;
    }
    this.skills.set(skill.id, skill);
  }

  get(id: string): Skill | undefined {
    return this.skills.get(id);
  }
}
