export class SkillRegistry {
    skills = new Map();
    register(skill) {
        if (skill.status !== "APPROVED") {
            return;
        }
        this.skills.set(skill.id, skill);
    }
    get(id) {
        return this.skills.get(id);
    }
}
