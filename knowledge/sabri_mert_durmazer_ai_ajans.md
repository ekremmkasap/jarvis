---
persona: sabri
source_type: youtube
source_url: https://youtu.be/2srOFknmCnM
source_title: "Yapay Zeka Ajanlarini Calisan Gibi Ise Alin — Paperclip + Agentic (Canli Demo)"
source_channel: "Mert Durmazer | Digital Academy"
source_uploaded: 2026-04-21
source_duration_sec: 1256
source_views: 2036
source_likes: 113
ingested_at: 2026-04-24
ingested_for: "Sabri (reklam ajansi / AI creative director) - icerik/kaynak kutuphanesi"
---

# Sabri icin icerik kaynagi — Mert Durmazer: AI Ajanlari Calisan Gibi Ise Alma

Bu not, Sabri persona'sinin reklam ajansi ve AI creative director rolu icin icerik
kaynagi olarak eklenmistir. Sabri'nin system_prompt'unda zaten `@alexlindai + @ohmo.ai + Mert Durmazer modelinde` referansi var; bu kaynak o modelden somut uygulama.

## Ozet

Mert Durmazer (Digital Academy) canli demo ile 130 micro-AI-agent'li bir sirketi nasil
kurup calistirdigini gosteriyor. Iki ana arac:

1. **Agentic.com.tr** — Mert'in kurdugu, 130 hazir AI calisan (avukat, SEO, yerel SEO,
   satis, musteri hizmetleri temsilcisi, Flutter uzmanli, team lead, team implementer,
   tedavi maliyet tahminci vb.) iceren kontrol paneli. Her agent ayri CV, yetenek seti
   ve ornek komutlarla tanimli. Is akisina gerektiginde agent'lar ekleniyor, isi
   yapinca cekiliyor.
2. **Paperclip** (https://github.com/paperclipai/paperclip) — Mert'in
   "guvenilir" dedigi acik kaynakli, self-hosted AI sirket kontrol paneli. Her sabah
   briefing, cuma raporu, aylik client dekleri, ajan bazli aylik token butcesi. Dijital
   pazarlama ajansi sablonu icinde CMO, paid media, SEO, musteri temsilcisi, CEO rolleri
   hazir.

## Ana fikir (Sabri icin onemli)

- **"Mikro calisanlara donusecek butun is dunyasi."** Tek buyuk ajan yerine, her gorev
  icin dar uzmanlik alanli micro-AI agent. Sozlesme inceleyen avukat ayri, SEO uzmani
  ayri, team lead ayri.
- **Ajan orkestrasyonu otomatik.** Bir komut verildiginde sistem ihtiyac duyulan
  ajanlari kesfedip yetenek setlerine gore bir araya getiriyor; team lead gorev atamasi
  yapiyor, autonomous sekilde tamamlaniyor.
- **Is cikti turleri:** KVKK metni, hasta sablonlari, fiyat listesi, Google Isletme
  profili rehberi, web SU (SEO) ceklisti, topic cluster pillar+supporting 30 gunluk
  blog takvimi, Flutter mobil uygulama mimari dokumani, backend/odeme akisi planlari.
- **Agency Race entegrasyonu:** Musteri bulma + is bulma sistemi (Region). Ayri bir
  Mert urunu; Paperclip/Agentic ile birleserek uctan uca bir "bir kisilik firma" cikiyor.

## Sabri icin cikarilabilecek degerler

1. **Reklam ajansi paketi iskeleti:** Mert'in "dis klinigi baslangic paketi" senaryosu
   dogrudan Sabri'nin 3-tier paket yapisina uyarlanabilir — sozlesme + KVKK + SEO +
   sosyal takvim + landing + fiyat listesi = "Starter paketi".
2. **Micro-agent taksonomisi:** Sabri'nin kendi sub_agents listesine (voc_researcher,
   brand_dna_writer, ad_prompt_generator, copywriter, obsidian_writer) ek olarak
   Agentic'ten gelen "yerel SEO uzmani", "tedavi maliyet tahminci" gibi sektor-ozel
   uzmanlar eklenebilir.
3. **Brief -> orchestration ornegi:** Mert'in "yeni bir dis klinigi aciyorum, baslangic
   paketi hazirla" komutu Sabri'nin brief -> VOC -> Brand DNA -> 40 reklam promptu
   akisina paralel. Sabri ayni tetikleyiciyi reklam domain'ine uygulayabilir.
4. **Open source alternatif (Paperclip):** Sabrican ve Seda icin teknik bir referans —
   self-hosted alternative control panel olarak kullanilabilir.

## Mert'in referans verdigi kaynaklar (not)

- https://agentic.com.tr/ — 130 calisanli sistem
- https://digitalacademy.com.tr/ — Mert'in kursu
- https://digitalacademy.com.tr/webinar — 3 gunluk ucretsiz webinar
- https://www.skool.com/otomasyon — topluluk
- https://github.com/paperclipai/paperclip — acik kaynakli AI sirket kontrol paneli

## Dogrudan kullanilabilir is akisi ornekleri

### 1) Dis klinigi baslangic paketi (reklam ajansi ekseninde)
Komut: `yeni bir dis klinigi aciyorum. Baslangic paketi hazirla.`
Cikti (video'da gosterilen): Google Isletme profili rehberi, web sitesi teknik SEO
ceklisti, KVKK aydinlatma metni, hasta takip sablonlari, tedavi fiyat listesi
taslagi, konum/hedef kitle/tedavi kapsaminda ozellestirme.

### 2) 30 gunluk blog icerik takvimi (topic cluster)
Komut: `sosyal medyayla ilgili 30 gunluk blog icerik takvimi hazirla. topic cluster
yapisinda pillar + supporting makaleler olsun.`
Cikti: Anahtar kelime taramasi, domain kalite kontrolu, toxic link kontrolu, 30 gunluk
pillar + supporting makale takvimi, hedef trafikle (ornek: 150 organik ziyaret/ay).

### 3) Flutter mobil uygulama (easy entegrasyonlu)
Komut: `Flutter ile easy entegrasyonlu bir dis klinigi randevu uygulamasi istiyorum.`
Cikti: Mobil uygulama mimari dokumani, ekok klasor duzeni, temel evraklar, ekiko
entegrasyonu, backend, odeme akisi.

## Tam transkript (otomatik, kaba)

> Kaynak: YouTube otomatik Turkce altyazi. Duzeltilmemis — referans amacli.

Selam. Bugun cok guzel bir konu konusacagiz. AI sirketinizi AI calisanlarla nasil
kurarsiniz bunu anlatacagim. Ama bundan once cok guclu bir sistem olusturduk biz ve
bu sistemle sirketinize 130 calisani birden alabiliyorsunuz ve bu 130 calisan sizin
icin calisiyor, islemler yapiyor ve otomatik olarak bir sirket halinde hareket
edebiliyorsunuz. Siz nasil sifirdan 130 calisanli sirkete cikarabilirsiniz? Kendi AI
sirketinizi olusturabilirsiniz. Bu neden onemli? Cunku girisim yapiyorsaniz, startup
kuruyorsaniz, AI ajansiniz varsa ya da is hayatinda ihracattan ajanslara ve dijital
pazarlama ajansina, e-ticaretten her alana yapay zeka calisanlarini, sirketlere, is
akislarina dahil etmenin yolu bu. Bu sistem yurt disinda bizim musterilerimize
kurdugumuz sistemin bir versiyonu. Bunu agent uzerinden kullanabileceksiniz.

Ben Mert yapay zeka girisimcisiyim. Su anda da cok karli bir otomasyon isi yurutuyorum.
Son bir yil icerisinde dortten fazla startup kurdum ve ikisi su an dunyanin en buyuk
teyile rekabet ediyor. Topluluga katilmak istiyorsaniz skool.com/otomasyon. Mobil
uygulamadan web tasarimina, AI otomasyon ajansindan Claude Code derslerine her sey
iceride var.

Simdi agentik.com.tr'den kullanabileceksiniz. 130 tane cok iyi calisan var ve
ihtiyacinizin oldugu anda ise geliyorlar, isi yapiyorlar, gidiyorlar. Mikro
calisanlara donusecek butun is dunyasi. Her sirkette o gorev icin tasarlanmis micro
AI agentlar olacak. Burada 130 tane calisan var. Mesela avukat sozlesme inceleyici.
Normal bir avukat degil, sadece sozlesmeler konusunda uzman bir calisan. Her islem
icin farkli ozelliklerde, farkli CV'li calisanlar var. Kendisine isim verebiliyorsun,
CV'si var, ornek komutlari var. Mesela satis calisanimiz, musteri hizmetleri
temsilcisi. 130 tane calisan var. Iste takimin basinda bir yonlendirici var, digerleri
team leadin yonlendirmesiyle is yapiyor. Hepsinin farkli yetenek setleri var.

Senaryo: yeni bir dis klinigi aciyorum, baslangic paketi hazirla bana, sozlesmeler
dahil. Komutu verdigim anda sistem calisanlari kesfetmeye basliyor: kurulum, SEO,
hasta KVKK, hasta sablonlari, fiyat listesi. Birkac bilgi istedi: konum Istanbul,
genel dis hekimligi, implant orta dutu yok, estetik var. Yerel SEO uzmani, tedavi
maliyet tahminci calisti. Sonuc: Google Isletme profili rehberi, web sitesi teknik
SEO ceklisti, KVKK aydinlatma metni, hasta takip sablonlari, tedavi fiyat listesi
taslagi. 2026 Turkiye piyasa ortalamasi aciklamasiyla birlikte. Tum belgeleri
olusturdu. Bunu AI calisanlariniza yaptirabiliyorsunuz.

Ikinci senaryo sosyal medyayla ilgili: 30 gunluk blog icerik takvimi, topic cluster
yapisinda pillar + supporting makaleler. Teknik tarama yapiliyor, anahtar kelime
arastirmasi, domain kalite kontrolu, toxic link kontrolu. Tam istedigim seyleri
yapiyorlar. Agent 2'yi cagiriyor, oradan calisanlari cagiriyor. 30 gunluk, hangi
amacla ne yapilacagini soyleyen detayli rapor. Pillar + supporting yapisinda, hedef
150 organik ziyaret.

Ucuncu senaryo: Flutter ile easy entegrasyonlu dis klinigi randevu uygulamasi. Mobil
uygulama mimari dokumantasyonu yazma gorevi verdi. Flutter uzmani calisti. Ecoik
klasor duzeni, temel evraklar, eciko entegrasyonu, backend, odeme akisi, uygulamanin
yapisi. Mimari kararlarin hepsini planladi.

Bu 130 calisandan is akislari, modeller, yetenekler ekleyebiliyorsunuz.
Sistem prompt ekleyebiliyorsunuz, kisilik verebiliyorsunuz, calisirken nasil
calisacagini ogretebiliyorsunuz. Ayrica projede kendi hafizalari var. Gelecegin
calisma sistemi bu.

Simdi sirket kurmak istiyorsaniz Paperclip: https://github.com/paperclipai/paperclip.
Acik kaynakli, kendi sunucunda calisan, otonom AI sirket kontrol paneli. Dijital
pazarlama ajansi sablonu: CMO, paid media, SEO, musteri temsilcisi, CEO. Her sabah
briefing, cuma raporu, ayda bir client dekleri, her ajan aylik token butcesi. Buradan
basladiginizda direkt sistem kullanilabilir. Agency Race (Region) ile birlestirirseniz
uctan uca bir musteri bulma + is yapma sistemi ciktisi var.
