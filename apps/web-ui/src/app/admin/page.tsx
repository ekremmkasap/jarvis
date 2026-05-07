import Link from "next/link";
import { AdminQuickActions } from "@/components/AdminQuickActions";
import { getAdminData, getSystemHealth } from "@/lib/adminData";

export const dynamic = "force-dynamic";

function formatDate(value?: string) {
  if (!value) {
    return "-";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return new Intl.DateTimeFormat("tr-TR", {
    dateStyle: "medium",
    timeStyle: "short"
  }).format(date);
}

function formatComponentValue(value: unknown) {
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return JSON.stringify(value);
}

export default async function AdminPage() {
  const [{ customers, betaSignups, tenantConfigs, accountSummary, summary }, health] = await Promise.all([
    getAdminData(),
    getSystemHealth()
  ]);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-6 py-10 lg:px-10">
        <header className="mb-10 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.3em] text-emerald-300">Admin Dashboard</p>
            <h1 className="mt-3 text-4xl font-semibold text-white">Musteri ve sistem kontrol paneli</h1>
            <p className="mt-3 max-w-3xl text-sm leading-7 text-slate-300">
              Sistem sagligi, beta basvurulari, musteri onboarding kayitlari ve tenant durumlari tek
              ekranda izlenir.
            </p>
          </div>
          <div className="flex flex-wrap gap-3 text-sm">
            <Link
              href="/landing"
              className="rounded-full border border-slate-700 px-4 py-2 text-slate-200 transition hover:border-slate-500 hover:bg-slate-900"
            >
              Landing
            </Link>
            <Link
              href="/ops"
              className="rounded-full bg-emerald-400 px-4 py-2 font-medium text-slate-950 transition hover:bg-emerald-300"
            >
              Live Ops
            </Link>
            <Link
              href="/codex-accounts"
              className="rounded-full border border-cyan-400/30 px-4 py-2 font-medium text-cyan-100 transition hover:border-cyan-300 hover:bg-cyan-400/10"
            >
              Codex Accounts
            </Link>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          <article className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Sistem saglik durumu</p>
            <div className="mt-2 text-3xl font-semibold text-white">{health.status}</div>
          </article>
          <article className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Toplam musteri</p>
            <div className="mt-2 text-3xl font-semibold text-white">{summary.customerCount}</div>
          </article>
          <article className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Aktif musteri</p>
            <div className="mt-2 text-3xl font-semibold text-white">{summary.activeCustomerCount}</div>
          </article>
          <article className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Tenant sayisi</p>
            <div className="mt-2 text-3xl font-semibold text-white">{summary.tenantCount}</div>
          </article>
          <article className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Beta basvuru</p>
            <div className="mt-2 text-3xl font-semibold text-white">{summary.betaSignupCount}</div>
          </article>
          <article className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
            <p className="text-sm text-slate-400">Hazir codex slotu</p>
            <div className="mt-2 text-3xl font-semibold text-white">{accountSummary.runtimeSlots}</div>
          </article>
        </section>

        <section className="mt-8 grid gap-8 xl:grid-cols-[1.15fr_0.85fr]">
          <article className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-white">Codex hesap omurgasi</h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-400">
                  Metadata `config/account_registry.json`, execution slot gercegi ise
                  `state/codex-accounts/registry.json` uzerinden okunur. Ayrintili mutasyon ve slot
                  gorevlendirmeleri ayri sayfada tutulur.
                </p>
              </div>
              <Link
                href="/codex-accounts"
                className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-sm font-medium text-emerald-100 transition hover:border-emerald-300 hover:bg-emerald-400/15"
              >
                Codex hesap paneline git
              </Link>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm text-slate-400">Toplam hesap</p>
                <p className="mt-2 text-2xl font-semibold text-white">{accountSummary.total}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm text-slate-400">Aktif</p>
                <p className="mt-2 text-2xl font-semibold text-emerald-300">{accountSummary.active}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm text-slate-400">Limitte</p>
                <p className="mt-2 text-2xl font-semibold text-amber-300">{accountSummary.limited}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm text-slate-400">Login bekleyen</p>
                <p className="mt-2 text-2xl font-semibold text-cyan-300">{accountSummary.pendingLogin}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm text-slate-400">Son runtime sync</p>
                <p className="mt-2 text-sm font-medium text-white">{formatDate(accountSummary.lastRuntimeSync)}</p>
              </div>
            </div>
          </article>

          <article className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
            <h2 className="text-xl font-semibold text-white">Admin surface boundaries</h2>
            <div className="mt-4 space-y-3 text-sm text-slate-300">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                <span className="font-medium text-white">/landing</span>: public onboarding and beta intake
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                <span className="font-medium text-white">/ops</span>: live tasks, queue, runtime, telemetry
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3">
                <span className="font-medium text-white">/admin</span>: customers, onboarding, account controls
              </div>
            </div>

            <div className="mt-6 space-y-3">
              {accountSummary.alerts.length ? (
                accountSummary.alerts.slice(0, 6).map((alert) => (
                  <div
                    key={alert}
                    className="rounded-2xl border border-amber-400/20 bg-amber-400/10 px-4 py-3 text-sm text-amber-100"
                  >
                    {alert}
                  </div>
                ))
              ) : (
                <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-100">
                  Hesap tarafinda operator uyarisi yok.
                </div>
              )}
            </div>
          </article>
        </section>

        <section className="mt-8 grid gap-8 xl:grid-cols-[1.2fr_0.8fr]">
          <article className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <h2 className="text-xl font-semibold text-white">Sistem durumu</h2>
                <p className="mt-2 text-sm text-slate-400">Bridge: {health.bridgeUrl}</p>
                <p className="text-sm text-slate-500">Orchestrator: {health.orchestratorUrl}</p>
              </div>
              <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300">
                {health.status}
              </span>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm text-slate-400">Son guncelleme</p>
                <p className="mt-2 text-base text-white">{formatDate(health.timestamp)}</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/[0.03] p-4">
                <p className="text-sm text-slate-400">Hata</p>
                <p className="mt-2 text-base text-white">{health.error ?? "-"}</p>
              </div>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-3">
              {health.services && typeof health.services === "object"
                ? Object.entries(health.services).map(([name, value]) => (
                    <div
                      key={name}
                      className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
                    >
                      <p className="text-sm text-slate-400">{name}</p>
                      <p className="mt-2 text-base text-white">{formatComponentValue(value)}</p>
                    </div>
                  ))
                : null}
            </div>

            <div className="mt-6 space-y-3">
              {health.components && Object.keys(health.components).length ? (
                Object.entries(health.components).map(([name, value]) => (
                  <div
                    key={name}
                    className="rounded-2xl border border-white/10 bg-white/[0.03] px-4 py-3 text-sm text-slate-300"
                  >
                    <span className="font-medium text-white">{name}</span>: {formatComponentValue(value)}
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-400">Bridge health endpoint bilesen detayi donmedi.</p>
              )}
            </div>
          </article>

          <article className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
            <h2 className="text-xl font-semibold text-white">Hizli aksiyonlar</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">
              Stripe webhook zincirini bridge uzerinden test edin veya JSON endpointlerini dogrudan
              kontrol edin.
            </p>
            <div className="mt-6">
              <AdminQuickActions />
            </div>
          </article>
        </section>

        <section className="mt-8 rounded-3xl border border-white/10 bg-slate-900/70 p-6">
          <h2 className="text-xl font-semibold text-white">Plan dagilimi</h2>
          <div className="mt-4 flex flex-wrap gap-3 text-sm">
            {Object.entries(summary.planCounts).length ? (
              Object.entries(summary.planCounts).map(([plan, count]) => (
                <span
                  key={plan}
                  className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-4 py-2 text-emerald-100"
                >
                  {plan}: {count}
                </span>
              ))
            ) : (
              <span className="text-slate-400">Henuz musteri kaydi yok.</span>
            )}
          </div>
        </section>

        <section className="mt-8 grid gap-8 xl:grid-cols-2">
          <article className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
            <div className="flex items-center justify-between gap-4">
              <h2 className="text-xl font-semibold text-white">Musteriler</h2>
              <span className="text-sm text-slate-400">{customers.length} kayit</span>
            </div>
            <div className="mt-6 space-y-4">
              {customers.length ? (
                customers.map((customer) => (
                  <div
                    key={customer.email}
                    className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-base font-medium text-white">{customer.email}</h3>
                        <p className="text-sm text-slate-400">
                          Plan: {customer.plan} | Tenant: {customer.tenant_id ?? "-"}
                        </p>
                      </div>
                      <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300">
                        {customer.status}
                      </span>
                    </div>
                    <div className="mt-3 grid gap-2 text-sm text-slate-300 md:grid-cols-2">
                      <p>Customer ID: {customer.customer_id ?? "-"}</p>
                      <p>Oturum: {customer.session_id ?? "-"}</p>
                      <p>Olusturma: {formatDate(customer.created_at)}</p>
                      <p>Guncelleme: {formatDate(customer.updated_at)}</p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-400">Henuz musteri onboarding kaydi olusmadi.</p>
              )}
            </div>
          </article>

          <article className="rounded-3xl border border-white/10 bg-slate-900/70 p-6">
            <div className="flex items-center justify-between gap-4">
              <h2 className="text-xl font-semibold text-white">Tenant konfigurasyonlari</h2>
              <span className="text-sm text-slate-400">{tenantConfigs.length} tenant</span>
            </div>
            <div className="mt-6 space-y-4">
              {tenantConfigs.length ? (
                tenantConfigs.map((tenant) => (
                  <div
                    key={tenant.tenant_id}
                    className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
                  >
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div>
                        <h3 className="text-base font-medium text-white">{tenant.name}</h3>
                        <p className="text-sm text-slate-400">
                          {tenant.tenant_id} | Plan: {tenant.plan}
                        </p>
                      </div>
                      <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300">
                        {tenant.active ? "active" : "inactive"}
                      </span>
                    </div>
                    <div className="mt-3 grid gap-2 text-sm text-slate-300 md:grid-cols-2">
                      <p>Musteri: {tenant.customer_email ?? "-"}</p>
                      <p>Stripe: {tenant.stripe_customer_id ?? "-"}</p>
                      <p>Ozellik: {(tenant.features ?? []).join(", ") || "-"}</p>
                      <p>Web Port: {tenant.web_port ?? "-"}</p>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-sm text-slate-400">Tenant config bulunamadi.</p>
              )}
            </div>
          </article>
        </section>

        <section className="mt-8 rounded-3xl border border-white/10 bg-slate-900/70 p-6">
          <div className="flex items-center justify-between gap-4">
            <h2 className="text-xl font-semibold text-white">Landing beta basvurulari</h2>
            <span className="text-sm text-slate-400">{betaSignups.length} basvuru</span>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-2">
            {betaSignups.length ? (
              betaSignups.map((signup) => (
                <div
                  key={`${signup.email}-${signup.createdAt}`}
                  className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
                >
                  <h3 className="text-base font-medium text-white">{signup.name}</h3>
                  <p className="mt-1 text-sm text-slate-400">{signup.email}</p>
                  <div className="mt-3 flex flex-wrap gap-2 text-xs">
                    <span className="rounded-full border border-white/10 px-3 py-1 text-slate-300">
                      {signup.plan}
                    </span>
                    {signup.company ? (
                      <span className="rounded-full border border-white/10 px-3 py-1 text-slate-300">
                        {signup.company}
                      </span>
                    ) : null}
                    <span className="rounded-full border border-white/10 px-3 py-1 text-slate-300">
                      {formatDate(signup.createdAt)}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-sm text-slate-400">Landing formundan gelen basvuru yok.</p>
            )}
          </div>
        </section>
      </div>
    </main>
  );
}
