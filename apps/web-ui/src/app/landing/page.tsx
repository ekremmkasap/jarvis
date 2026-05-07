'use client';

import { FormEvent, useState } from 'react';

type Plan = 'Starter' | 'Pro' | 'Agency';

type FormState = {
  name: string;
  email: string;
  company: string;
  plan: Plan;
};

const features = [
  {
    title: 'Self-hosted kurulum',
    description:
      'Jarvis kendi sunucunuzda veya yerel ağınızda çalışır. Veriniz dış servislerde dolaşmaz.',
  },
  {
    title: 'Tam Türkçe komut deneyimi',
    description:
      'Operasyon, destek, raporlama ve rutin iş akışları Türkçe komutlarla yönetilir.',
  },
  {
    title: 'Sıfır API maliyeti',
    description:
      'Harici API çağrı maliyetleri olmadan, sabit aylık ücretle öngörülebilir kullanım sunar.',
  },
  {
    title: 'Çoklu bot mimarisi',
    description:
      'Ekip, departman veya müşteri bazında ayrı botlar tanımlayarak görevleri izole edebilirsiniz.',
  },
  {
    title: 'Görev ve olay merkezi',
    description:
      'Komutlar, kuyruk durumu, bildirimler ve agent akışları tek panelde görünür olur.',
  },
  {
    title: 'Ajans ve white-label uyumu',
    description:
      'Agency paketi ile markanıza uygun kurulum, sınırsız bot ve API erişimi birlikte gelir.',
  },
];

const steps = [
  {
    title: '1. Paketinizi seçin',
    description:
      'İhtiyacınıza göre Starter, Pro veya Agency planını belirleyin ve beta formunu gönderin.',
  },
  {
    title: '2. Kurulumu planlayalım',
    description:
      'Ekibinizle birlikte sunucu yapısı, bot sayısı ve komut kapsamı için kısa bir onboarding yapalım.',
  },
  {
    title: '3. Türkçe AI operasyonunu başlatın',
    description:
      'Jarvis devreye alındıktan sonra görevler, komutlar ve müşteri akışları tek merkezden çalışır.',
  },
];

const plans = [
  {
    name: 'Starter',
    price: '₺1500/ay',
    description: 'Tek botla hızlı başlangıç yapmak isteyen ekipler için.',
    features: ['1 bot', 'Temel komutlar', 'Hızlı kurulum'],
    highlight: false,
  },
  {
    name: 'Pro',
    price: '₺3500/ay',
    description: 'Operasyonunu aktif kullanan ekipler için en dengeli paket.',
    features: ['3 bot', 'Tüm komutlar', 'Öncelikli destek'],
    highlight: true,
  },
  {
    name: 'Agency',
    price: '₺7500/ay',
    description: 'Birden fazla müşteri veya marka yöneten yapılar için.',
    features: ['Sınırsız bot', 'White-label', 'API erişimi'],
    highlight: false,
  },
] as const;

const initialFormState: FormState = {
  name: '',
  email: '',
  company: '',
  plan: 'Starter',
};

export default function LandingPage() {
  const [formState, setFormState] = useState<FormState>(initialFormState);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [errorMessage, setErrorMessage] = useState('');

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSubmitting(true);
    setErrorMessage('');
    setIsSuccess(false);

    try {
      const response = await fetch('/api/beta-signup', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formState),
      });

      if (!response.ok) {
        throw new Error('Beta başvurusu gönderilemedi.');
      }

      setIsSuccess(true);
      setFormState(initialFormState);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : 'Beklenmeyen bir hata oluştu.');
      setIsSuccess(false);
    } finally {
      setIsSubmitting(false);
    }
  }

  function updateField<K extends keyof FormState>(field: K, value: FormState[K]) {
    setIsSuccess(false);
    setFormState((current) => ({ ...current, [field]: value }));
  }

  return (
    <main className="relative isolate min-h-screen bg-slate-950 text-slate-100">
      <div className="absolute inset-x-0 top-0 -z-10 h-[32rem] bg-[radial-gradient(circle_at_top,rgba(16,185,129,0.18),transparent_58%),radial-gradient(circle_at_right,rgba(59,130,246,0.14),transparent_35%)]" />

      <section className="mx-auto flex min-h-screen w-full max-w-7xl flex-col px-6 pb-16 pt-10 lg:px-10">
        <header className="mb-16 flex flex-wrap items-center justify-between gap-4">
          <div className="inline-flex items-center gap-3 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-4 py-2 text-sm text-emerald-200">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            Jarvis SaaS
          </div>
          <nav className="flex flex-wrap items-center gap-5 text-sm text-slate-300">
            <a href="#ozellikler" className="transition hover:text-white">
              Özellikler
            </a>
            <a href="#nasil-calisir" className="transition hover:text-white">
              Nasıl Çalışır
            </a>
            <a href="#fiyatlar" className="transition hover:text-white">
              Fiyatlandırma
            </a>
            <a href="#beta-formu" className="transition hover:text-white">
              Beta Başvuru
            </a>
          </nav>
        </header>

        <div className="grid flex-1 items-center gap-12 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="max-w-3xl">
            <p className="mb-5 text-sm uppercase tracking-[0.3em] text-emerald-300">
              Türkçe. Self-hosted. Sıfır API maliyeti.
            </p>
            <h1 className="max-w-2xl text-4xl font-semibold tracking-tight text-white sm:text-5xl lg:text-6xl">
              Ekibiniz için çalışan, maliyeti öngörülebilir AI asistan altyapısı.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
              Jarvis; şirket içinde kurulan, Türkçe komutları anlayan ve bot tabanlı iş akışlarını
              tek panelde yöneten bir AI asistan SaaS çözümüdür. Ek API faturası çıkarmaz, tüm
              operasyonunuzu sade bir kontrol yüzeyinde toplar.
            </p>

            <div className="mt-8 flex flex-wrap gap-4">
              <a
                href="#beta-formu"
                className="rounded-full bg-emerald-400 px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300"
              >
                Beta Başvurusu Yap
              </a>
              <a
                href="#fiyatlar"
                className="rounded-full border border-slate-700 px-6 py-3 text-sm font-semibold text-slate-100 transition hover:border-slate-500 hover:bg-slate-900"
              >
                Paketleri İncele
              </a>
            </div>

            <div className="mt-10 grid gap-4 sm:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <div className="text-2xl font-semibold text-white">1 gün</div>
                <p className="mt-2 text-sm text-slate-300">İlk kurulum ve temel komut aktivasyonu</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <div className="text-2xl font-semibold text-white">0 TL</div>
                <p className="mt-2 text-sm text-slate-300">Ek API kullanım ücreti olmadan sabit model</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
                <div className="text-2xl font-semibold text-white">TR odaklı</div>
                <p className="mt-2 text-sm text-slate-300">Türkçe komut, ekip ve müşteri operasyonları</p>
              </div>
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-slate-900/80 p-6 shadow-2xl shadow-emerald-950/30 backdrop-blur">
            <div className="rounded-[1.5rem] border border-emerald-500/20 bg-slate-950 p-6">
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div>
                  <p className="text-sm text-slate-400">Canlı Görev Akışı</p>
                  <h2 className="mt-1 text-xl font-semibold text-white">Jarvis Control Layer</h2>
                </div>
                <span className="rounded-full border border-emerald-400/30 bg-emerald-400/10 px-3 py-1 text-xs text-emerald-300">
                  Self-hosted
                </span>
              </div>

              <div className="mt-6 space-y-4">
                {[
                  ['Satış Botu', 'Yeni lead raporu hazırlandı', 'Aktif'],
                  ['Destek Botu', 'Türkçe ticket akışı otomatik işlendi', 'Çalışıyor'],
                  ['Ajans Koordinatörü', 'White-label müşteri paneli senkron', 'Hazır'],
                ].map(([title, description, status]) => (
                  <div
                    key={title}
                    className="rounded-2xl border border-white/10 bg-white/[0.03] p-4"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="font-medium text-white">{title}</h3>
                      <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">
                        {status}
                      </span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{description}</p>
                  </div>
                ))}
              </div>

              <div className="mt-6 rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-sm leading-6 text-emerald-100">
                Jarvis, dış API bağımlılığı yerine kendi altyapınıza kurulur ve her ay sabit maliyetle
                çalışır.
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="ozellikler" className="border-t border-white/10 bg-slate-950/60 py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-10">
          <div className="max-w-2xl">
            <p className="text-sm uppercase tracking-[0.3em] text-emerald-300">Özellikler</p>
            <h2 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">
              Operasyonu hızlandıran net bir altyapı
            </h2>
            <p className="mt-4 text-base leading-7 text-slate-300">
              Jarvis, ajanslar ve ekipler için karmaşık AI iş akışlarını yönetilebilir hale getirir.
            </p>
          </div>

          <div className="mt-12 grid gap-6 md:grid-cols-2 xl:grid-cols-3">
            {features.map((feature) => (
              <article
                key={feature.title}
                className="rounded-3xl border border-white/10 bg-white/[0.04] p-6"
              >
                <div className="mb-4 h-10 w-10 rounded-2xl bg-emerald-400/10 ring-1 ring-inset ring-emerald-400/30" />
                <h3 className="text-xl font-semibold text-white">{feature.title}</h3>
                <p className="mt-3 text-sm leading-7 text-slate-300">{feature.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="nasil-calisir" className="py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-10">
          <div className="flex flex-col gap-10 lg:flex-row lg:items-end lg:justify-between">
            <div className="max-w-2xl">
              <p className="text-sm uppercase tracking-[0.3em] text-emerald-300">Nasıl Çalışır</p>
              <h2 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">
                Üç adımda beta kurulumuna geçin
              </h2>
            </div>
            <p className="max-w-xl text-base leading-7 text-slate-300">
              Teknik altyapıyı sıfırdan kurmak yerine Jarvis ile kontrollü, hızlı ve yerel bir AI
              operasyon katmanı kurarsınız.
            </p>
          </div>

          <div className="mt-12 grid gap-6 lg:grid-cols-3">
            {steps.map((step) => (
              <article
                key={step.title}
                className="rounded-3xl border border-white/10 bg-slate-900/60 p-7"
              >
                <h3 className="text-xl font-semibold text-white">{step.title}</h3>
                <p className="mt-4 text-sm leading-7 text-slate-300">{step.description}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="fiyatlar" className="border-y border-white/10 bg-slate-900/60 py-24">
        <div className="mx-auto max-w-7xl px-6 lg:px-10">
          <div className="max-w-2xl">
            <p className="text-sm uppercase tracking-[0.3em] text-emerald-300">Fiyatlandırma</p>
            <h2 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">
              Sabit ücret, net kapsam, hızlı karar
            </h2>
            <p className="mt-4 text-base leading-7 text-slate-300">
              Her plan, ek API maliyeti olmadan aylık sabit fiyatla sunulur.
            </p>
          </div>

          <div className="mt-12 grid gap-6 lg:grid-cols-3">
            {plans.map((plan) => (
              <article
                key={plan.name}
                className={`rounded-3xl border p-8 ${
                  plan.highlight
                    ? 'border-emerald-400/40 bg-emerald-400/10 shadow-xl shadow-emerald-950/20'
                    : 'border-white/10 bg-white/[0.04]'
                }`}
              >
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-2xl font-semibold text-white">{plan.name}</h3>
                  {plan.highlight ? (
                    <span className="rounded-full bg-emerald-400 px-3 py-1 text-xs font-semibold text-slate-950">
                      En Popüler
                    </span>
                  ) : null}
                </div>
                <p className="mt-5 text-4xl font-semibold text-white">{plan.price}</p>
                <p className="mt-4 text-sm leading-7 text-slate-300">{plan.description}</p>

                <ul className="mt-8 space-y-3 text-sm text-slate-200">
                  {plan.features.map((item) => (
                    <li key={item} className="flex items-center gap-3">
                      <span className="h-2 w-2 rounded-full bg-emerald-400" />
                      {item}
                    </li>
                  ))}
                </ul>

                <a
                  href="#beta-formu"
                  className={`mt-8 inline-flex rounded-full px-5 py-3 text-sm font-semibold transition ${
                    plan.highlight
                      ? 'bg-emerald-400 text-slate-950 hover:bg-emerald-300'
                      : 'border border-slate-700 text-slate-100 hover:border-slate-500 hover:bg-slate-900'
                  }`}
                >
                  Bu Paketle Başvur
                </a>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section id="beta-formu" className="py-24">
        <div className="mx-auto grid max-w-7xl gap-10 px-6 lg:grid-cols-[0.9fr_1.1fr] lg:px-10">
          <div className="max-w-xl">
            <p className="text-sm uppercase tracking-[0.3em] text-emerald-300">CTA / Beta Başvuru</p>
            <h2 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">
              Jarvis beta sürecine ekibinizi dahil edin
            </h2>
            <p className="mt-4 text-base leading-7 text-slate-300">
              Formu doldurun; kullanım senaryonuz, bot ihtiyacınız ve uygun paket için size geri
              dönüş yapalım.
            </p>

            <div className="mt-8 rounded-3xl border border-white/10 bg-white/[0.04] p-6">
              <h3 className="text-lg font-semibold text-white">Beta sürecinde sizi ne bekliyor?</h3>
              <ul className="mt-5 space-y-4 text-sm leading-7 text-slate-300">
                <li>Türkçe komut yapınıza göre kısa keşif görüşmesi</li>
                <li>Sunucu ve bot kurgusuna uygun başlangıç önerisi</li>
                <li>Kurulum sonrası erken erişim ve geri bildirim kanalı</li>
              </ul>
            </div>
          </div>

          <div className="rounded-[2rem] border border-white/10 bg-slate-900/80 p-6 backdrop-blur">
            <form onSubmit={handleSubmit} className="grid gap-5">
              <div>
                <label htmlFor="name" className="mb-2 block text-sm font-medium text-slate-200">
                  İsim
                </label>
                <input
                  id="name"
                  name="name"
                  type="text"
                  value={formState.name}
                  onChange={(event) => updateField('name', event.target.value)}
                  required
                  className="w-full rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-emerald-400"
                  placeholder="Adınız Soyadınız"
                />
              </div>

              <div>
                <label htmlFor="email" className="mb-2 block text-sm font-medium text-slate-200">
                  E-posta
                </label>
                <input
                  id="email"
                  name="email"
                  type="email"
                  value={formState.email}
                  onChange={(event) => updateField('email', event.target.value)}
                  required
                  className="w-full rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-emerald-400"
                  placeholder="ornek@sirket.com"
                />
              </div>

              <div>
                <label htmlFor="company" className="mb-2 block text-sm font-medium text-slate-200">
                  Şirket <span className="text-slate-500">(opsiyonel)</span>
                </label>
                <input
                  id="company"
                  name="company"
                  type="text"
                  value={formState.company}
                  onChange={(event) => updateField('company', event.target.value)}
                  className="w-full rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition placeholder:text-slate-500 focus:border-emerald-400"
                  placeholder="Şirket adınız"
                />
              </div>

              <div>
                <label htmlFor="plan" className="mb-2 block text-sm font-medium text-slate-200">
                  Paket seçimi
                </label>
                <select
                  id="plan"
                  name="plan"
                  value={formState.plan}
                  onChange={(event) => updateField('plan', event.target.value as Plan)}
                  className="w-full rounded-2xl border border-white/10 bg-slate-950 px-4 py-3 text-slate-100 outline-none transition focus:border-emerald-400"
                >
                  <option value="Starter">Starter</option>
                  <option value="Pro">Pro</option>
                  <option value="Agency">Agency</option>
                </select>
              </div>

              <button
                type="submit"
                disabled={isSubmitting}
                className="mt-2 rounded-full bg-emerald-400 px-6 py-3 text-sm font-semibold text-slate-950 transition hover:bg-emerald-300 disabled:cursor-not-allowed disabled:bg-emerald-400/60"
              >
                {isSubmitting ? 'Gönderiliyor...' : 'Beta Başvurusu Gönder'}
              </button>

              {isSuccess ? (
                <div className="rounded-2xl border border-emerald-400/30 bg-emerald-400/10 px-4 py-3 text-sm text-emerald-100">
                  Başvurunuz alındı. Kısa süre içinde sizinle iletişime geçeceğiz.
                </div>
              ) : null}

              {errorMessage ? (
                <div className="rounded-2xl border border-rose-400/30 bg-rose-400/10 px-4 py-3 text-sm text-rose-100">
                  {errorMessage}
                </div>
              ) : null}
            </form>
          </div>
        </div>
      </section>
    </main>
  );
}
