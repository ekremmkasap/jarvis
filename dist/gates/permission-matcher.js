function globMatch(pattern, value) {
    if (pattern === "*") {
        return true;
    }
    const re = new RegExp(`^${pattern.replace(/[.+?^${}()|[\\]\\]/g, "\\$&").replace(/\*/g, ".*")}$`);
    return re.test(value);
}
function permMatch(required, granted) {
    return required.type === granted.type && globMatch(granted.resource, required.resource);
}
export function evaluatePolicy(required, rules) {
    for (const p of required) {
        for (const r of rules) {
            if (r.effect === "DENY" && permMatch(p, r.permission)) {
                return { allowed: false, reason: `POLICY_DENY:${p.type}:${p.resource}` };
            }
        }
    }
    for (const p of required) {
        const ok = rules.some((r) => r.effect === "ALLOW" && permMatch(p, r.permission));
        if (!ok) {
            return { allowed: false, reason: `POLICY_MISSING:${p.type}:${p.resource}` };
        }
    }
    return { allowed: true };
}
