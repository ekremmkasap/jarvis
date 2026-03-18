import { validateTransitions } from "../state/state-transition-validator";
import { evaluatePolicy } from "./permission-matcher";
export class Gates {
    rules = [
        { effect: "ALLOW", permission: { type: "WRITE", resource: "memory:runs/*" } },
        { effect: "ALLOW", permission: { type: "WRITE", resource: "memory:project/*" } },
        { effect: "ALLOW", permission: { type: "READ", resource: "memory:*" } },
        { effect: "ALLOW", permission: { type: "NET", resource: "https://*.tiktok.com/*" } },
        { effect: "ALLOW", permission: { type: "NET", resource: "https://graph.instagram.com/*" } }
    ];
    evaluate(result, state) {
        if (!result.accepted) {
            return { allowed: false, reason: "EXECUTION_NOT_ACCEPTED" };
        }
        if (!result.ok) {
            return { allowed: false, reason: result.error ?? "EXECUTION_FAILED" };
        }
        const p = evaluatePolicy(result.requiredPermissions, this.rules);
        if (!p.allowed) {
            return { allowed: false, reason: p.reason };
        }
        const t = validateTransitions(state, result.transitions);
        if (!t.ok) {
            return { allowed: false, reason: t.reason };
        }
        return { allowed: true };
    }
}
