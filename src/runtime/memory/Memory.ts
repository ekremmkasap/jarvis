import { MemoryWrite } from "../execution/ExecutionResult";

export type MemoryNamespace = "runs" | "project" | "knowledge";

type PendingWrite = MemoryWrite & { requestedAt: number };

function parseNamespace(key: string): MemoryNamespace {
  const ns = key.split(".")[0] as MemoryNamespace;
  if (ns === "runs" || ns === "project" || ns === "knowledge") {
    return ns;
  }
  return "runs";
}

export class Memory {
  private store = new Map<string, unknown>();
  private pending: PendingWrite[] = [];

  write(op: MemoryWrite): void {
    if (op.type !== "WRITE") {
      return;
    }

    const key = op.key.trim();
    const ns = parseNamespace(key);

    if ((ns === "project" || ns === "knowledge") && op.requiresApproval) {
      this.pending.push({ ...op, key, requestedAt: Date.now() });
      return;
    }

    this.store.set(key, op.value);
  }

  approve(key: string): boolean {
    const idx = this.pending.findIndex((p) => p.key === key);
    if (idx < 0) {
      return false;
    }
    const op = this.pending.splice(idx, 1)[0];
    this.store.set(op.key, op.value);
    return true;
  }

  getPending(): PendingWrite[] {
    return [...this.pending];
  }

  dump(namespace?: MemoryNamespace): Record<string, unknown> {
    const all = Object.fromEntries(this.store.entries()) as Record<string, unknown>;
    if (!namespace) {
      return all;
    }
    const out: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(all)) {
      if (parseNamespace(k) === namespace) {
        out[k] = v;
      }
    }
    return out;
  }
}
