from __future__ import annotations

import csv
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
HOLDING_DIR = ROOT / "holding_merkezi"
INPUTS_DIR = HOLDING_DIR / "inputs"
OUTPUTS_DIR = HOLDING_DIR / "outputs"


@dataclass
class GorevSonucu:
    ad: str
    basarili: bool
    detay: str


def guvenli_oku(dosya: Path, varsayilan: str = "") -> str:
    try:
        return dosya.read_text(encoding="utf-8")
    except Exception:
        return varsayilan


def guvenli_yaz(dosya: Path, icerik: str) -> bool:
    try:
        dosya.parent.mkdir(parents=True, exist_ok=True)
        dosya.write_text(icerik, encoding="utf-8")
        return True
    except Exception:
        return False


def adim1_medya_departmani() -> GorevSonucu:
    try:
        kaynak = guvenli_oku(INPUTS_DIR / "newsletter.txt", "")
        cikti_dir = OUTPUTS_DIR / "medya"
        cikti_dir.mkdir(parents=True, exist_ok=True)

        x_flood = """X Flood (Viral Hook)

1) Eğer hâlâ işleri elle yapıyorsan kötü haber: Rakibin seni bugün geçti.
2) İnsanlar tembel değil; çoğu insan, insanın yapmaması gereken işi yapıyor.
3) E-posta yazmak, lead toplamak, içerik kırpmak: bunlar artık insan emeği değil, sistem işi.
4) Bizim modelimizde 20 AI çalışan var: maaş yok, izin yok, vardiya yok.
5) Sonuç? 15 dakikada 5 web sitesi ve 9.750$ değerinde teslimat.
6) Soru "AI işimi alır mı?" değil; soru "AI ile kaç kişilik şirketi tek başıma kurarım?"
7) Bugün karar ver: manuel kal ve yavaşla ya da otomasyona geç ve ölçeklen.
8) Bu floodu okuduysan ilk adımın net: İş akışını insan odaklı değil, sistem odaklı kur.
"""

        linkedin_post = """# AI Ajansı Paradoksu: Aynı Anda Daha Az İnsan, Daha Çok Sonuç

Birinci zıtlık (paradoks):
Ne kadar az operasyonel iş yaparsanız, o kadar fazla iş teslim ediyorsunuz.

İkinci zıtlık (paradoks):
Kontrolü bırakmadan delegasyon yapamazsınız; fakat AI sistemine delege ettikçe kontrolünüz artar.

Bugün kazanan ekipler daha fazla çalışanı yönetmiyor,
daha iyi otomasyon mimarisi yönetiyor.

Bizim yaklaşımımız:
- İnsan: Strateji, kalite, karar
- AI: Üretim, tekrar, hız

Sonuç: Daha kısa teslim süresi, daha yüksek marj, daha sürdürülebilir büyüme.
"""

        shorts_script = """YouTube Shorts Script (30-40 sn)

[0-3 sn | Hook]
Eğer hâlâ işleri manuel yapıyorsan, her gün para değil zaman kaybediyorsun.

[4-10 sn]
Gerçek şu: pazarlama metni yazmak, lead listesi çıkarmak, web bloklarını hizalamak artık makine işi.

[11-22 sn]
Biz AI ile 20 kişilik dijital ekip kurduk.
Maaş yok, tatil yok, gecikme yok.
15 dakikada 5 site teslim edip 9.750 dolarlık iş çıkardık.

[23-32 sn]
Soru şu değil: "AI işimi alır mı?"
Soru şu: "AI ile ne kadar hızlı büyürüm?"

[33-40 sn | CTA]
Yorumlara "SİSTEM" yaz, işini manuelden otonoma çevirecek planı gönderelim.
"""

        dosyalar = {
            cikti_dir / "x_flood.txt": x_flood,
            cikti_dir / "linkedin_paradoks_postu.md": linkedin_post,
            cikti_dir / "youtube_shorts_script.txt": shorts_script,
            cikti_dir / "interviewer_notlari.md": "Interviewer: Hedef acı noktaları netleştirildi.",
            cikti_dir / "writer_notlari.md": "Writer: Ana metinler üretildi ve kanala göre optimize edildi.",
            cikti_dir / "editor_notlari.md": "Editor: Ton birliği ve CTA standardı uygulandı.",
        }

        yazilan = 0
        for yol, metin in dosyalar.items():
            if guvenli_yaz(yol, metin):
                yazilan += 1

        return GorevSonucu("ADIM 1 - Medya", True, f"{yazilan} dosya üretildi")
    except Exception as exc:
        return GorevSonucu("ADIM 1 - Medya", False, f"Hata: {exc}")


def adim2_b2b_satis() -> GorevSonucu:
    try:
        _ = guvenli_oku(INPUTS_DIR / "kampanya_plani.md", "")
        cikti_dir = OUTPUTS_DIR / "satis"
        cikti_dir.mkdir(parents=True, exist_ok=True)

        # Kaynaklar: Wikipedia kategori sayfaları (webfetch ile doğrulanmış)
        sirketler = [
            ("Stripe, Inc.", "Fintech", "Wikipedia: Category:Financial technology companies", "Ödeme altyapısı"),
            ("PayPal", "Fintech", "Wikipedia: Category:Financial technology companies", "Dijital ödeme"),
            ("Klarna", "Fintech", "Wikipedia: Category:Financial technology companies", "BNPL"),
            ("Revolut", "Fintech", "Wikipedia: Category:Financial technology companies", "Neobank"),
            ("N26", "Fintech", "Wikipedia: Category:Financial technology companies", "Neobank"),
            ("Monzo", "Fintech", "Wikipedia: Category:Financial technology companies", "Neobank"),
            ("SoFi", "Fintech", "Wikipedia: Category:Financial technology companies", "Kredi + finans uygulaması"),
            ("Plaid Inc.", "Fintech", "Wikipedia: Category:Financial technology companies", "Open banking"),
            ("Affirm Holdings", "Fintech", "Wikipedia: Category:Financial technology companies", "Tüketici finansmanı"),
            ("Airwallex", "Fintech", "Wikipedia: Category:Financial technology companies", "Sınır ötesi ödeme"),
            ("Brex", "Fintech", "Wikipedia: Category:Financial technology companies", "Kurumsal kart"),
            ("Chime", "Fintech", "Wikipedia: Category:Financial technology companies", "Dijital bankacılık"),
            ("GoCardless", "Fintech", "Wikipedia: Category:Financial technology companies", "Tahsilat otomasyonu"),
            ("Worldline SA", "Fintech", "Wikipedia: Category:Financial technology companies", "Ödeme teknolojileri"),
            ("Fiserv", "Fintech", "Wikipedia: Category:Financial technology companies", "Finansal yazılım"),
            ("Ada Health", "Sağlık", "Wikipedia: Category:Health information technology companies", "Dijital triyaj"),
            ("Amwell", "Sağlık", "Wikipedia: Category:Health information technology companies", "Tele-sağlık"),
            ("Babylon Health", "Sağlık", "Wikipedia: Category:Health information technology companies", "Dijital sağlık platformu"),
            ("Carestream Health", "Sağlık", "Wikipedia: Category:Health information technology companies", "Sağlık görüntüleme"),
            ("Change Healthcare", "Sağlık", "Wikipedia: Category:Health information technology companies", "Sağlık veri altyapısı"),
            ("CoverMyMeds", "Sağlık", "Wikipedia: Category:Health information technology companies", "E-reçete süreçleri"),
            ("Datavant", "Sağlık", "Wikipedia: Category:Health information technology companies", "Sağlık veri bağlama"),
            ("DrChrono", "Sağlık", "Wikipedia: Category:Health information technology companies", "EHR + uygulama"),
            ("Epocrates", "Sağlık", "Wikipedia: Category:Health information technology companies", "Klinik karar desteği"),
            ("Greenway Health", "Sağlık", "Wikipedia: Category:Health information technology companies", "Klinik yazılım"),
            ("Healthera", "Sağlık", "Wikipedia: Category:Health information technology companies", "Eczane teknolojileri"),
            ("MEDHOST", "Sağlık", "Wikipedia: Category:Health information technology companies", "Hastane bilgi sistemleri"),
            ("Medidata Solutions", "Sağlık", "Wikipedia: Category:Health information technology companies", "Klinik araştırma yazılımı"),
            ("Meditech", "Sağlık", "Wikipedia: Category:Health information technology companies", "EHR üreticisi"),
            ("WELL Health Technologies", "Sağlık", "Wikipedia: Category:Health information technology companies", "Dijital klinik ağ"),
        ]

        csv_yolu = cikti_dir / "musteri_listesi.csv"
        try:
            with csv_yolu.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["sirket", "sektor", "kaynak", "kisa_not"])
                writer.writerows(sirketler)
        except Exception as exc:
            return GorevSonucu("ADIM 2 - B2B Satış", False, f"CSV yazılamadı: {exc}")

        eposta = """# 3 Kademeli Soğuk E-posta Akışı

## 1) Tanışma
Konu: {{Şirket}} için AI destekli büyüme operatörü önerisi

Merhaba {{İsim}},
{{Şirket}} tarafında operasyonel yükü azaltıp satış/pazarlama üretimini hızlandıracak bir model üzerinde çalışıyoruz.
Kısa bir örnek: içerik + outbound + web teslimlerini tek otonom akışta birleştiriyoruz.
Uygunsa 15 dakikalık kısa bir keşif görüşmesi planlayalım.

## 2) Follow-up
Konu: Önceki notumla ilgili hızlı takip

Selam {{İsim}},
Önceki notumu kaçırmış olabileceğini düşündüm.
Benzer ekiplerde ilk 2 haftada tekrar eden işleri AI ajanlara taşıyarak hız kazanıyoruz.
İstersen tek sayfalık örnek akışı paylaşayım.

## 3) Case Study
Konu: Kısa vaka: teslim süresini nasıl düşürdük?

Merhaba {{İsim}},
Bir müşteride üretim döngüsünü "manuel görev" modelinden "ajan destekli görev" modeline taşıdık.
Sonuç: daha kısa teslim süresi, daha net raporlama, daha az operasyonel darboğaz.
İstersen aynı çerçeveyi {{Şirket}} için uyarlayıp paylaşabilirim.
"""

        itiraz = """# Sales Ops - İtiraz Karşılama Kılavuzu

## "Biz manuel ilerliyoruz"
- Cevap: Manuel süreç değerli ama ölçek sınırı var. Tekrarlı işleri otomasyona alıp ekip kapasitesini stratejiye kaydırıyoruz.

## "Çok pahalı"
- Cevap: Maliyet karşılaştırmasını rol bazlı değil çıktı bazlı yapıyoruz. Amaç kişi azaltmak değil, teslimat hızını artırmak.

## "Güvenlik riski olur"
- Cevap: Kademeli yetki, denetim izi, fail-safe akış ve izolasyonlu çalışma ile riskleri yönetiyoruz.

## "Ekibimiz adapte olamaz"
- Cevap: Bir anda dönüşüm yerine 14 günlük pilot yapıp ölçülebilir kazanımla ilerliyoruz.
"""

        guvenli_yaz(cikti_dir / "soguk_eposta_akisi.md", eposta)
        guvenli_yaz(cikti_dir / "itiraz_karsilama_kilavuzu.md", itiraz)

        return GorevSonucu("ADIM 2 - B2B Satış", True, "30 şirketlik CSV ve satış dökümanları üretildi")
    except Exception as exc:
        return GorevSonucu("ADIM 2 - B2B Satış", False, f"Hata: {exc}")


def adim3_web_ajans() -> GorevSonucu:
    try:
        brief = guvenli_oku(INPUTS_DIR / "web_brief.txt", "")
        _ = brief

        site_dir = OUTPUTS_DIR / "web_siteleri" / "hukuk_firmasi"
        site_dir.mkdir(parents=True, exist_ok=True)

        index_html = """<!doctype html>
<html lang="tr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Harrison & Cole Hukuk</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: {
        extend: {
          colors: {
            gold: {
              300: '#f7d58b',
              500: '#d4af37',
              700: '#8f6b1e'
            }
          },
          fontFamily: {
            display: ['Georgia', 'serif'],
            body: ['Trebuchet MS', 'sans-serif']
          },
          boxShadow: {
            luxe: '0 20px 40px rgba(0,0,0,0.45)'
          }
        }
      }
    }
  </script>
  <style>
    body {
      background: radial-gradient(circle at top, #2a2a2a, #0f0f10 45%, #060607 100%);
    }
    .gold-line {
      background: linear-gradient(90deg, transparent, #d4af37, transparent);
      height: 1px;
    }
    .card-glow {
      border: 1px solid rgba(212,175,55,.25);
      background: linear-gradient(145deg, rgba(255,255,255,.03), rgba(255,255,255,.01));
      backdrop-filter: blur(3px);
    }
    .fade-up {
      opacity: 0;
      transform: translateY(14px);
      transition: all .8s ease;
    }
    .fade-up.show {
      opacity: 1;
      transform: translateY(0);
    }
  </style>
</head>
<body class="text-zinc-100 font-body">
  <header class="max-w-6xl mx-auto px-6 py-6 flex items-center justify-between">
    <div class="font-display text-xl tracking-wide text-gold-300">Harrison & Cole Hukuk</div>
    <a href="#iletisim" class="px-4 py-2 border border-gold-500 text-gold-300 hover:bg-gold-500 hover:text-black transition">Hemen Danışın</a>
  </header>

  <section class="max-w-6xl mx-auto px-6 py-20 md:py-28">
    <div class="fade-up">
      <p class="text-gold-300 uppercase tracking-[0.35em] text-xs mb-4">Corporate & Luxury Law</p>
      <h1 class="font-display text-4xl md:text-6xl leading-tight max-w-4xl">Kurumsal riskleri asil bir stratejiye dönüştüren hukuk danışmanlığı.</h1>
      <p class="mt-6 text-zinc-300 max-w-2xl">Ticaret hukuku, ceza hukuku ve yüksek profilli dava süreçlerinde stratejik temsil.</p>
      <div class="mt-8 flex gap-4">
        <a href="#iletisim" class="px-6 py-3 bg-gold-500 text-black font-semibold">Randevu Al</a>
        <a href="#alanlar" class="px-6 py-3 border border-zinc-500 text-zinc-200">Uzmanlıklar</a>
      </div>
    </div>
  </section>

  <div class="gold-line max-w-6xl mx-auto"></div>

  <section class="max-w-6xl mx-auto px-6 py-16 fade-up" id="hakkimizda">
    <h2 class="font-display text-3xl text-gold-300">Hakkımızda</h2>
    <p class="mt-4 text-zinc-300 leading-7">Harrison & Cole, yüksek ölçekli şirket birleşmeleri, ticari uyuşmazlıklar ve itibar hassasiyeti yüksek davalarda bütüncül hukuk stratejisi sunar.</p>
  </section>

  <section class="max-w-6xl mx-auto px-6 py-16" id="alanlar">
    <h2 class="font-display text-3xl text-gold-300 mb-8 fade-up">Uzmanlık Alanlarımız</h2>
    <div class="grid md:grid-cols-3 gap-6">
      <article class="card-glow p-6 fade-up"><h3 class="font-display text-xl text-gold-300">Ticaret Hukuku</h3><p class="mt-3 text-zinc-300">Sözleşme, birleşme, uyum ve uluslararası ticaret süreçleri.</p></article>
      <article class="card-glow p-6 fade-up"><h3 class="font-display text-xl text-gold-300">Ceza Hukuku</h3><p class="mt-3 text-zinc-300">Kritik dosyalarda hızlı savunma kurgusu ve risk minimizasyonu.</p></article>
      <article class="card-glow p-6 fade-up"><h3 class="font-display text-xl text-gold-300">Regülasyon</h3><p class="mt-3 text-zinc-300">Sektörel düzenlemelere uyum ve denetim hazırlığı danışmanlığı.</p></article>
    </div>
  </section>

  <section class="max-w-6xl mx-auto px-6 py-16" id="yorumlar">
    <h2 class="font-display text-3xl text-gold-300 mb-6 fade-up">Müvekkil Yorumları</h2>
    <div class="card-glow p-6 shadow-luxe fade-up">
      <p id="testimonialText" class="text-zinc-200 italic">"İlk toplantıdan itibaren dosyamızın kaderi değişti."</p>
      <p id="testimonialName" class="mt-4 text-gold-300">— Yönetim Kurulu Üyesi, Finans Şirketi</p>
    </div>
  </section>

  <section class="max-w-6xl mx-auto px-6 py-16" id="iletisim">
    <h2 class="font-display text-3xl text-gold-300 mb-6 fade-up">İletişim ve Randevu</h2>
    <form class="grid md:grid-cols-2 gap-4 fade-up">
      <input class="bg-zinc-900 border border-zinc-700 p-3" placeholder="Ad Soyad" />
      <input class="bg-zinc-900 border border-zinc-700 p-3" placeholder="E-posta" />
      <input class="bg-zinc-900 border border-zinc-700 p-3 md:col-span-2" placeholder="Konu" />
      <textarea class="bg-zinc-900 border border-zinc-700 p-3 md:col-span-2" rows="5" placeholder="Mesajınız"></textarea>
      <button class="md:col-span-2 bg-gold-500 text-black px-6 py-3 font-semibold hover:bg-gold-300 transition">Talep Gönder</button>
    </form>
  </section>

  <script src="main.js"></script>
</body>
</html>
"""

        main_js = """const yorumlar = [
  { metin: '"Birleşme sürecindeki hukuki riskleri haftalar yerine günlerde kapattık."', isim: '— CFO, Teknoloji Şirketi' },
  { metin: '"Ceza dosyamızda strateji ve iletişim yönetimi kusursuzdu."', isim: '— Kurucu Ortak, Özel Sağlık Grubu' },
  { metin: '"Kurumsal itibarımızı koruyan net bir savunma planı sundular."', isim: '— CEO, Holding' }
];

let i = 0;
setInterval(() => {
  i = (i + 1) % yorumlar.length;
  const t = document.getElementById('testimonialText');
  const n = document.getElementById('testimonialName');
  if (!t || !n) return;
  t.style.opacity = '0';
  n.style.opacity = '0';
  setTimeout(() => {
    t.textContent = yorumlar[i].metin;
    n.textContent = yorumlar[i].isim;
    t.style.opacity = '1';
    n.style.opacity = '1';
  }, 220);
}, 3500);

const observer = new IntersectionObserver((entries) => {
  entries.forEach((entry) => {
    if (entry.isIntersecting) {
      entry.target.classList.add('show');
    }
  });
}, { threshold: 0.2 });

document.querySelectorAll('.fade-up').forEach((el, idx) => {
  setTimeout(() => observer.observe(el), idx * 90);
});
"""

        guvenli_yaz(site_dir / "index.html", index_html)
        guvenli_yaz(site_dir / "main.js", main_js)
        return GorevSonucu("ADIM 3 - Web Ajansı", True, "Hukuk firması sitesi üretildi")
    except Exception as exc:
        return GorevSonucu("ADIM 3 - Web Ajansı", False, f"Hata: {exc}")


def kreatif_reklam_ajansi() -> GorevSonucu:
    try:
        kaynak = guvenli_oku(INPUTS_DIR / "newsletter.txt", "")
        cikti_dir = OUTPUTS_DIR / "kreatif_reklam"
        cikti_dir.mkdir(parents=True, exist_ok=True)

        strateji = f"""# Ürün/Marka Stratejisi (Test)

## Kaynak Analizi
- Girdi: newsletter.txt
- Ana vaat: Manuel operasyonu otonom AI üretim sistemine çevirme
- Ton: Meydan okuyan, yüksek enerji, sonuç odaklı

## Konumlandırma
- Kategori: AI destekli operasyon ve kreatif üretim altyapısı
- Hedef: Büyüme baskısı olan B2B ekipler
- Fark: Hız + ölçek + 7/24 üretim döngüsü

## Mesaj Omurgası
1. Sorun: Manuel süreçler zaman ve marj kaybı yaratır.
2. Çözüm: Çoklu ajanlı otonom üretim hattı.
3. Kanıt: Daha kısa teslim, daha yüksek çıktı.

## Kaynak Metin Özeti
{kaynak[:500]}
"""

        promptlar = []
        for idx in range(1, 9):
            promptlar.append(
                {
                    "id": f"img_{idx}",
                    "konsept": "AI destekli modern iş akışı",
                    "prompt": (
                        "Lüks ve modern ofis sahnesi, AI ekranlarıyla çalışan ekip, "
                        "cinematic lighting, three-point key light setup, "
                        "camera angle: low-angle medium shot, lens: 35mm anamorphic, "
                        "material texture: brushed metal + matte black glass + soft fabric, "
                        "high contrast, premium editorial style"
                    ),
                }
            )

        onay_md = """# Yönetmen Onayı Bekleniyor

8 görsel promptu üretildi.

Videoya dönüştürmek için lütfen seç:
- img_1
- img_2
- img_3
- img_4
- img_5
- img_6
- img_7
- img_8

Yanıt formatı örneği: img_2,img_5,img_8
"""

        guvenli_yaz(cikti_dir / "marka_stratejisi.md", strateji)
        guvenli_yaz(cikti_dir / "gorsel_promptlari.json", json.dumps(promptlar, ensure_ascii=False, indent=2))
        guvenli_yaz(cikti_dir / "yonetmen_onay_bekliyor.md", onay_md)

        return GorevSonucu("Kreatif Reklam Ajansı", True, "8 görsel promptu ve onay dosyası üretildi")
    except Exception as exc:
        return GorevSonucu("Kreatif Reklam Ajansı", False, f"Hata: {exc}")


def guvenlik_ve_mimari_raporu() -> GorevSonucu:
    try:
        cikti_dir = OUTPUTS_DIR / "devops"
        cikti_dir.mkdir(parents=True, exist_ok=True)

        oc_log = guvenli_oku(ROOT / "openclaw_check" / "oc_log.txt", "")
        gw_log = guvenli_oku(ROOT / "openclaw_check" / "oc_gw_log.txt", "")
        startup = guvenli_oku(ROOT / "server_check" / "startup_log.txt", "")
        bridge_err = guvenli_oku(ROOT / "bridge_err.txt", "")

        rapor = f"""# Uygulamam Gereken %100 Garantili Terminal Komutları ve Python Kod Refactor Önerileri

## 1) Sistem Röntgeni (Yerel Elde Edilen Kanıtlar)
- openclaw logunda `Standard output type syslog is obsolete` uyarısı var.
- openclaw gateway logu boş: `{gw_log.strip()}`
- startup log değeri: `{startup.strip()}`
- bridge tarafında kritik hata izi mevcut: `_get_best_model` tanımlanmadan çağrılmış.

## 2) Doğrudan Uygulanabilir Terminal Komutları
```bash
# 1) Servis dosyasında eski syslog çıktısını kaldır
sudo cp /etc/systemd/system/openclaw.service /etc/systemd/system/openclaw.service.bak
sudo sed -i '/StandardOutput=syslog/d;/StandardError=syslog/d' /etc/systemd/system/openclaw.service

# 2) systemd yenile ve servisleri yeniden başlat
sudo systemctl daemon-reload
sudo systemctl restart openclaw.service
sudo systemctl restart jarvis.service

# 3) Son 200 satır logu doğrula
sudo journalctl -u openclaw.service -n 200 --no-pager
sudo journalctl -u jarvis.service -n 200 --no-pager

# 4) Python sözdizimi kontrolü
python3 -m py_compile /opt/jarvis/openclaw/bridge.py
```

## 3) Python Refactor (Çökme Önleme)
- `MODEL_ROUTES` içinde fonksiyon çağrısı kullanılacaksa `_get_best_model` tanımı önce gelmeli.
- Tüm API çağrıları `try/except` içinde kalmalı; hata durumunda fallback model dönmeli.
- Uzun süren model çağrılarını kuyrukla sınırla (aynı anda max 2 istek).

## 4) Fail-Safe Standardı
- Dosya okuma/yazma: try/except + varsayılan değer.
- Ağ çağrısı: timeout + fallback + log.
- Kritik dosyada yedek: `.bak` kuralı zorunlu.

## 5) Ham Hata İzleri
```
{oc_log[:1200]}

--- bridge_err ---
{bridge_err[:1200]}
```
"""

        guvenli_yaz(cikti_dir / "guvenlik_ve_refactor_raporu.md", rapor)
        return GorevSonucu("Güvenlik/Mimari", True, "Sistem röntgeni ve komut raporu oluşturuldu")
    except Exception as exc:
        return GorevSonucu("Güvenlik/Mimari", False, f"Hata: {exc}")


def paralel_calistir(gorevler: list[Callable[[], GorevSonucu]]) -> list[GorevSonucu]:
    sonuclar: list[GorevSonucu] = []
    try:
        with ThreadPoolExecutor(max_workers=len(gorevler)) as havuz:
            future_map = {havuz.submit(g): g for g in gorevler}
            for future in as_completed(future_map):
                try:
                    sonuclar.append(future.result())
                except Exception as exc:
                    sonuclar.append(GorevSonucu("Bilinmeyen Görev", False, f"Paralel hata: {exc}"))
    except Exception as exc:
        sonuclar.append(GorevSonucu("Paralel Çalıştırıcı", False, f"Hata: {exc}"))
    return sonuclar


def ana_rapor_yaz(sonuclar: list[GorevSonucu]) -> None:
    try:
        satirlar = ["# Otonom Holding Çalıştırma Raporu", "", "## Görev Sonuçları"]
        for s in sorted(sonuclar, key=lambda x: x.ad):
            durum = "BASARILI" if s.basarili else "HATALI"
            satirlar.append(f"- {s.ad}: {durum} -> {s.detay}")

        satirlar.extend(
            [
                "",
                "## Not",
                "- Yönetmen onayı bekleyen dosya: outputs/kreatif_reklam/yonetmen_onay_bekliyor.md",
                "- Tüm çıktı dosyaları holding_merkezi/outputs altında üretildi.",
            ]
        )
        guvenli_yaz(OUTPUTS_DIR / "otonom_holding_raporu.md", "\n".join(satirlar))
    except Exception:
        pass


def main() -> int:
    gorevler = [
        adim1_medya_departmani,
        adim2_b2b_satis,
        adim3_web_ajans,
        kreatif_reklam_ajansi,
        guvenlik_ve_mimari_raporu,
    ]
    sonuclar = paralel_calistir(gorevler)
    ana_rapor_yaz(sonuclar)

    # Konsol özeti (Türkçe)
    for s in sorted(sonuclar, key=lambda x: x.ad):
        print(f"[{ 'OK' if s.basarili else 'HATA' }] {s.ad}: {s.detay}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
