import { ExecutionResult } from "../execution/ExecutionResult";
import { RuntimeState } from "../contracts/types";
import { validateTransitions } from "../state/state-transition-validator";
import { evaluatePolicy, PolicyRule } from "./permission-matcher";

export type GateDecision = {
  allowed: boolean;
  reason?: string;
};

export class Gates {
  private rules: PolicyRule[] = [
    { effect: "ALLOW", permission: { type: "WRITE", resource: "memory:runs/*" } },
    { effect: "ALLOW", permission: { type: "WRITE", resource: "memory:project/*" } },
    { effect: "ALLOW", permission: { type: "READ", resource: "memory:*" } },
    { effect: "ALLOW", permission: { type: "NET", resource: "https://*.tiktok.com/*" } },
    { effect: "ALLOW", permission: { type: "NET", resource: "https://graph.instagram.com/*" } }
  ];

  evaluate(result: ExecutionResult, state: RuntimeState): GateDecision {
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
