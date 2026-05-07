import { existsSync } from "fs";
import { readdir, readFile } from "fs/promises";
import path from "path";

export type CustomerRecord = {
  email: string;
  plan: string;
  status: string;
  customer_id?: string;
  session_id?: string;
  created_at: string;
  updated_at?: string;
  customer_dir?: string;
  tenant_id?: string;
  tenant_dir?: string;
};

export type BetaSignupRecord = {
  name: string;
  email: string;
  company?: string;
  plan: string;
  createdAt: string;
};

export type TenantConfigRecord = {
  tenant_id: string;
  name: string;
  plan: string;
  active?: boolean;
  stripe_customer_id?: string | null;
  customer_email?: string;
  features?: string[];
  managed_by_bridge?: boolean;
  web_port?: number | null;
  created_at?: string;
};

export type BridgeHealth = {
  reachable: boolean;
  status: string;
  bridgeUrl: string;
  orchestratorUrl: string;
  timestamp?: string;
  error?: string;
  components?: Record<string, unknown>;
  services?: Record<string, unknown>;
  router?: Record<string, unknown>;
  providerHealth?: Record<string, unknown>;
  live?: Record<string, unknown>;
  [key: string]: unknown;
};

export type CodexAccountSummary = {
  total: number;
  active: number;
  blocked: number;
  limited: number;
  pendingLogin: number;
  runtimeSlots: number;
  lastRuntimeSync?: string;
  alerts: string[];
};

type HealthService = {
  name: string;
  url: string;
  reachable: boolean;
  ok: boolean;
  status: string;
  statusCode?: number;
  timestamp?: string;
  error?: string;
  payload?: Record<string, unknown>;
  [key: string]: unknown;
};

function findRepoRoot() {
  const candidates = [
    process.cwd(),
    path.resolve(process.cwd(), ".."),
    path.resolve(process.cwd(), "..", "..")
  ];

  const match = candidates.find((candidate) => existsSync(path.join(candidate, "server")));
  return match ?? path.resolve(process.cwd(), "..", "..");
}

function normalizeBridgeUrl() {
  const rawUrl = process.env.BRIDGE_URL?.trim() || "http://127.0.0.1:8081";
  return rawUrl.endsWith("/") ? rawUrl.slice(0, -1) : rawUrl;
}

function normalizeOrchestratorUrl() {
  const rawUrl = process.env.ORCHESTRATOR_URL?.trim() || "http://127.0.0.1:8091";
  return rawUrl.endsWith("/") ? rawUrl.slice(0, -1) : rawUrl;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeHealthStatus(value: unknown): "healthy" | "degraded" | "unhealthy" {
  const text = String(value ?? "").trim().toLowerCase();
  if (["healthy", "ok", "ready", "online"].includes(text)) {
    return "healthy";
  }
  if (["degraded", "warning", "partial", "disabled", "limited"].includes(text)) {
    return "degraded";
  }
  return "unhealthy";
}

async function readJsonFile<T>(filePath: string, fallback: T): Promise<T> {
  try {
    const raw = await readFile(filePath, "utf-8");
    return JSON.parse(raw) as T;
  } catch {
    return fallback;
  }
}

async function readCustomerDirectoryConfigs(customersDir: string): Promise<CustomerRecord[]> {
  try {
    const entries = await readdir(customersDir, { withFileTypes: true });
    const directories = entries.filter((entry) => entry.isDirectory());
    const configs = await Promise.all(
      directories.map(async (entry) => {
        const configPath = path.join(customersDir, entry.name, "config.json");
        const config = await readJsonFile<Record<string, unknown> | null>(configPath, null);
        if (!config) {
          return null;
        }
        const customer: CustomerRecord = {
          email: String(config.email ?? entry.name),
          plan: String(config.plan ?? "unknown"),
          status: String(config.status ?? "active"),
          created_at: String(config.created_at ?? ""),
          updated_at: String(config.updated_at ?? ""),
          customer_id: typeof config.customer_id === "string" ? config.customer_id : undefined,
          session_id: typeof config.session_id === "string" ? config.session_id : undefined,
          tenant_id: typeof config.tenant_id === "string" ? config.tenant_id : undefined,
          tenant_dir: typeof config.tenant_dir === "string" ? config.tenant_dir : undefined,
          customer_dir: path.join(customersDir, entry.name)
        };
        return customer;
      })
    );
    return configs.filter((config): config is CustomerRecord => Boolean(config));
  } catch {
    return [];
  }
}

async function readTenantConfigs(tenantsDir: string): Promise<TenantConfigRecord[]> {
  try {
    const entries = await readdir(tenantsDir, { withFileTypes: true });
    const tenantDirs = entries.filter((entry) => entry.isDirectory() && entry.name !== "_template");
    const configs = await Promise.all(
      tenantDirs.map(async (entry) => {
        const configPath = path.join(tenantsDir, entry.name, "config.json");
        return readJsonFile<TenantConfigRecord | null>(configPath, null);
      })
    );
    return configs.filter((config): config is TenantConfigRecord => Boolean(config));
  } catch {
    return [];
  }
}

function normalizeAccountStatus(value: unknown) {
  const text = String(value ?? "").trim().toLowerCase();
  if (["active", "ready", "online", "standby"].includes(text)) {
    return "active";
  }
  if (["quota_exceeded", "limited", "rate_limited"].includes(text)) {
    return "limited";
  }
  if (["pending_login"].includes(text)) {
    return "pending_login";
  }
  if (["offline", "inactive", "failed"].includes(text)) {
    return "blocked";
  }
  return text || "unknown";
}

async function readCodexAccountSummary(repoRoot: string): Promise<CodexAccountSummary> {
  const registry = await readJsonFile<{ accounts?: Array<Record<string, unknown>> }>(
    path.join(repoRoot, "config", "account_registry.json"),
    {}
  );
  const runtimeRegistry = await readJsonFile<Record<string, Record<string, unknown>>>(
    path.join(repoRoot, "state", "codex-accounts", "registry.json"),
    {}
  );

  const accounts = Array.isArray(registry.accounts) ? registry.accounts : [];
  let active = 0;
  let blocked = 0;
  let limited = 0;
  let pendingLogin = 0;
  const alerts: string[] = [];

  for (const account of accounts) {
    const status = normalizeAccountStatus(account.status);
    if (status === "active") {
      active += 1;
    } else {
      blocked += 1;
    }
    if (status === "limited") {
      limited += 1;
    }
    if (status === "pending_login") {
      pendingLogin += 1;
    }
  }

  for (const account of accounts.slice(0, 12)) {
    const status = normalizeAccountStatus(account.status);
    const label = String(account.label ?? account.id ?? "account").trim();
    if (status === "limited") {
      alerts.push(`${label} limitte`);
    } else if (status === "pending_login") {
      alerts.push(`${label} login bekliyor`);
    }
  }

  const runtimeSlots = Object.keys(runtimeRegistry).filter((key) => isRecord(runtimeRegistry[key])).length;
  const lastRuntimeSync = Object.values(runtimeRegistry)
    .filter(isRecord)
    .map((entry) => String(entry.saved_at ?? ""))
    .filter(Boolean)
    .sort()
    .at(-1);

  return {
    total: accounts.length,
    active,
    blocked,
    limited,
    pendingLogin,
    runtimeSlots,
    lastRuntimeSync,
    alerts,
  };
}

function mergeCustomers(
  registryCustomers: CustomerRecord[],
  directoryCustomers: CustomerRecord[]
): CustomerRecord[] {
  const merged = new Map<string, CustomerRecord>();

  for (const customer of [...registryCustomers, ...directoryCustomers]) {
    const email = customer.email.toLowerCase();
    const current = merged.get(email);
    merged.set(email, {
      ...current,
      ...customer
    });
  }

  return Array.from(merged.values());
}

async function fetchWithTimeout(url: string, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, {
      cache: "no-store",
      signal: controller.signal
    });
  } finally {
    clearTimeout(timeoutId);
  }
}

async function fetchServiceHealth(name: string, url: string): Promise<HealthService> {
  try {
    const response = await fetchWithTimeout(url, 5000);
    const rawBody = await response.text();
    const payload = rawBody ? (JSON.parse(rawBody) as Record<string, unknown>) : {};
    return {
      name,
      url,
      reachable: true,
      ok: response.ok,
      status: String(payload.status ?? (response.ok ? "healthy" : "degraded")),
      statusCode: response.status,
      timestamp: typeof payload.timestamp === "string" ? payload.timestamp : undefined,
      error: typeof payload.error === "string" ? payload.error : undefined,
      payload
    };
  } catch (error) {
    return {
      name,
      url,
      reachable: false,
      ok: false,
      status: "unreachable",
      error: error instanceof Error ? error.message : `${name} health istegi basarisiz oldu.`
    };
  }
}

function buildHealthComponents(
  bridge: HealthService,
  orchestrator: HealthService,
  router: Record<string, unknown> | undefined
) {
  const active = isRecord(router?.active) ? router.active : {};
  return {
    bridge: bridge.status,
    orchestrator: orchestrator.status,
    router: typeof router?.status === "string" ? router.status : "unknown",
    default_provider: typeof router?.default_provider === "string" ? router.default_provider : "-",
    selected_candidate:
      typeof active.selected_candidate === "string" && active.selected_candidate
        ? active.selected_candidate
        : "-",
    fallback_used: Boolean(active.fallback_used)
  };
}

function deriveOverallHealth(
  bridge: HealthService,
  orchestrator: HealthService,
  router: Record<string, unknown> | undefined
) {
  const bridgeStatus = normalizeHealthStatus(bridge.status);
  const orchestratorStatus = normalizeHealthStatus(orchestrator.status);
  const routerStatus = normalizeHealthStatus(router?.status ?? "degraded");

  if (!bridge.reachable || !orchestrator.reachable) {
    return "unhealthy";
  }
  if (bridgeStatus === "healthy" && orchestratorStatus === "healthy" && routerStatus === "healthy") {
    return "healthy";
  }
  if (bridgeStatus === "unhealthy" || orchestratorStatus === "unhealthy" || routerStatus === "unhealthy") {
    return "unhealthy";
  }
  return "degraded";
}

function stripPayload(service: HealthService) {
  const { payload, ...rest } = service;
  return rest;
}

export async function getAdminData() {
  const repoRoot = findRepoRoot();
  const serverDir = path.join(repoRoot, "server");
  const dataDir = path.join(serverDir, "data");
  const customersDir = path.join(dataDir, "customers");
  const tenantsDir = path.join(serverDir, "tenants");

  const registryCustomers = await readJsonFile<CustomerRecord[]>(path.join(dataDir, "customers.json"), []);
  const directoryCustomers = await readCustomerDirectoryConfigs(customersDir);
  const betaSignups = await readJsonFile<BetaSignupRecord[]>(path.join(dataDir, "beta_signups.json"), []);
  const tenantConfigs = await readTenantConfigs(tenantsDir);
  const accountSummary = await readCodexAccountSummary(repoRoot);
  const customers = mergeCustomers(registryCustomers, directoryCustomers);

  const planCounts = customers.reduce<Record<string, number>>((counts, customer) => {
    const key = (customer.plan || "unknown").toLowerCase();
    counts[key] = (counts[key] ?? 0) + 1;
    return counts;
  }, {});

  customers.sort((left, right) =>
    String(right.updated_at ?? right.created_at).localeCompare(String(left.updated_at ?? left.created_at))
  );
  betaSignups.sort((left, right) => right.createdAt.localeCompare(left.createdAt));
  tenantConfigs.sort((left, right) =>
    String(right.created_at ?? "").localeCompare(String(left.created_at ?? ""))
  );

  return {
    customers,
    betaSignups,
    tenantConfigs,
    accountSummary,
    summary: {
      customerCount: customers.length,
      activeCustomerCount: customers.filter((customer) => customer.status === "active").length,
      tenantCount: tenantConfigs.length,
      activeTenantCount: tenantConfigs.filter((tenant) => tenant.active).length,
      betaSignupCount: betaSignups.length,
      planCounts
    }
  };
}

export async function getBridgeHealth(): Promise<BridgeHealth> {
  const bridgeUrl = normalizeBridgeUrl();
  const orchestratorUrl = normalizeOrchestratorUrl();
  const [bridge, orchestrator] = await Promise.all([
    fetchServiceHealth("bridge", `${bridgeUrl}/health`),
    fetchServiceHealth("orchestrator", `${orchestratorUrl}/health`)
  ]);
  const bridgePayload = isRecord(bridge.payload) ? bridge.payload : {};
  const router = isRecord(bridgePayload.router) ? bridgePayload.router : undefined;
  const providerHealth = isRecord(bridgePayload.provider_health)
    ? bridgePayload.provider_health
    : isRecord(router?.providers)
      ? router.providers
      : undefined;
  const status = deriveOverallHealth(bridge, orchestrator, router);
  const components = buildHealthComponents(bridge, orchestrator, router);
  const errors = [bridge.error, orchestrator.error].filter(Boolean).join(" | ");

  return {
    bridgeUrl,
    orchestratorUrl,
    reachable: bridge.reachable && orchestrator.reachable,
    status,
    timestamp: bridge.timestamp ?? orchestrator.timestamp,
    error: errors || undefined,
    components,
    services: {
      bridge: stripPayload(bridge),
      orchestrator: stripPayload(orchestrator)
    },
    router,
    providerHealth,
    live: isRecord(bridgePayload.live) ? bridgePayload.live : undefined
  };
}

export async function getSystemHealth(): Promise<BridgeHealth> {
  return getBridgeHealth();
}
