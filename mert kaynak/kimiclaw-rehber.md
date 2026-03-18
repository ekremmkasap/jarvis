# KimiClaw Rehberi: Tarayıcıda OpenClaw Agent'ını Kur ve Çalıştır

Moonshot'ın bulut tabanlı OpenClaw çözümü. Tek tıkla deploy, kalıcı hafıza, zamanlanmış görevler, ClawHub skill kütüphanesi - hepsi tarayıcıdan.

---

## KimiClaw Nedir?

KimiClaw, Moonshot'ın OpenClaw framework'ü üzerine inşa ettiği bulut tabanlı AI agent platformu.

**OpenClaw Sorunu:**
- OpenClaw normalde "her zaman açık" bir makine gerektirir
- İnsanlar bunun için Mac Mini alıyor veya VPS kiralıyor
- Kurulum ve bakım gerekiyor → plug-and-play değil

**KimiClaw Çözümü:**
- Bulutta çalışır → local kurulum yok, sunucu yapılandırması yok
- Kimi K2.5 thinking modeli ile çalışır
- Kalıcı hafıza + 40 GB bulut depolama
- Tarayıcıyı kapatsan bile görevler çalışmaya devam eder
- Tek tıkla deploy

**Normal Chatbot'tan Farkı:**
- ChatGPT/Claude → tab'ı kapatırsan hiçbir şey çalışmaz
- KimiClaw → agent her zaman açık, görevleri arka planda yürütür
- Kişisel bulut çalışanı gibi düşün, chat oturumu değil

---

## Adım 1: KimiClaw Hesabı Oluştur ve Deploy Et

1. **KimiClaw sitesine git**
2. "One-Click Setup" seçeneğini tıkla
   - Zaten OpenClaw kullanıyorsan → "Link Existing OpenClaw" seçeneği de var
   - Biz sıfırdan kuruyoruz → one-click setup
3. **Ücretli hesap gerekli** → $39/ay
4. "Create" butonuna tıkla
5. "Kimi Claw is starting up" mesajı çıkar → **~1 dakika bekle**
6. Hazır olduğunda → Agent workspace açılır

**Artık elinde:**
- Kimi'nin bulutunda çalışan tam bir OpenClaw agent'ı var
- Her yerden erişebilirsin (Kimi hesabına giriş yaparak)
- Agent her zaman açık (always-on)

---

## Adım 2: Workspace'i Tanı

Deploy sonrası karşına chat arayüzü gelir.

**Arayüz Yapısı:**
- **Ana alan:** Chat penceresi (agent ile konuşma)
- **Settings sekmesi:** Şu an sadece bot adını değiştirebilirsin (beta)
- **Sağ taraf:** Agent'ın yaptığı aksiyonlar

**Temel Özellikler:**
- Kalıcı hafıza → bilgileri oturumlar arası hatırlar
- Zamanlanmış görevler → tarayıcı kapalıyken bile çalışır
- Skill kurulumu → ClawHub kütüphanesinden yetenek ekle
- Mesajlaşma entegrasyonları → Telegram, WhatsApp, Slack, Discord

---

## Adım 3: İlk Zamanlanmış Görevi (Cron Job) Oluştur

Bu, KimiClaw'un normal chatbot'lardan en büyük farkı.

**Prompt:**
```
Send me AI news every morning at 9:00 AM
```

**Ne olur:**
- Agent sadece bilgi vermez → gerçek bir zamanlanmış görev (cron job) oluşturur
- Cron job = zamanlayıcı tabanlı otomasyon
- Her sabah 9'da otomatik çalışır → AI haberlerini arar → özet üretir → sana gönderir
- Tarayıcı kapalı olsa bile çalışır (agent bulutta her zaman açık)

**Bu neden önemli:**
- ChatGPT'ye "her sabah bana haber gönder" dersen → tab kapatılınca biter
- KimiClaw'a dersen → gerçekten her sabah 9'da çalışır, sen uyurken bile

---

## Adım 4: Zamanlanmış Görevleri Yönet

**Sorun:** KimiClaw beta'da henüz görev listesi UI'ı yok (Zapier gibi bir panel yok). Settings'te sadece bot adı değiştirilebiliyor.

**Çözüm:** Agent'a chat'ten sor.

**Çalışan görevleri listele:**
```
What scheduled tasks do you have running?
```

Agent tüm aktif cron job'ları listeler: isim, zamanlama, detaylar.

**Bir görevi durdur:**
```
Turn off the daily AI news task
```

**Bir görevi değiştir:**
```
Change the daily AI news schedule from 9:00 AM to 7:30 AM
```

**Yeni görev örnekleri:**

Haftalık rakip takibi:
```
Every Monday at 8:00 AM, search for the latest news and updates 
about [rakip şirket] and summarize the key findings for me.
```

Günlük döviz kuru:
```
Every morning at 8:30 AM, check the USD/TRY exchange rate 
and send me a brief update.
```

Haftalık içerik fikirleri:
```
Every Wednesday at 10:00 AM, generate 5 YouTube video ideas 
about AI tools. Include titles and brief descriptions.
```

Günlük sosyal medya trendi:
```
Every day at 7:00 PM, find the top 5 trending AI topics 
on X/Twitter and summarize each in 2-3 sentences.
```

**İpucu:** 10-15-20 görev birikince takip zorlaşır. Düzenli olarak "What scheduled tasks do you have running?" diye sor ve gereksizleri kapat.

---

## Adım 5: Telegram Entegrasyonu

KimiClaw'u Telegram'a bağlayabilirsin → günlük AI haberleri direkt telefonuna gelir.

**Prompt:**
```
Connect to Telegram
```

**Agent'ın talimatları:**
1. Telegram'da `@BotFather`'a git
2. `/newbot` yaz
3. Bot'a isim ver (ör. "KimiClaw Asistanım")
4. Bot'a username ver (ör. "kimiclaw_mert_bot")
5. BotFather'ın verdiği token'ı kopyala
6. KimiClaw chat'ine yapıştır
7. **Agent'ı yeniden başlat** (restart) → eşleşme tamamlanır

**Bağlantı sonrası:**
- Telegram'dan agent'ınla konuşabilirsin
- Cron job sonuçları Telegram'a da gönderilir
- Ör: Sabah 9'daki AI haber özeti direkt telefonuna gelir

**Diğer bağlanabilir platformlar:**
- WhatsApp
- Slack
- Discord

Her biri için: chat'te "Connect to [platform]" yaz → talimatları takip et.

---

## Adım 6: Güvenlik - Önemli Uyarılar

**KimiClaw'un güvenlik modeli hakkında bilmen gerekenler:**

1. **Her şey Moonshot'ın bulutunda yaşar:**
   - Token'lar, hafıza, görevler, dosyalar → hepsi Moonshot'ın sunucularında
   - Senin local cihazında değil
   - KimiClaw = kendi kontrol ettiğin bir OpenClaw değil, Moonshot'ın senin adına çalıştırdığı bir SaaS platformu

2. **Token'ların nasıl saklandığı belirsiz:**
   - Telegram bot token'ı verdiğinde → Moonshot'ın runtime'ında saklanır
   - Henüz net bir UI veya dokümantasyon yok (beta)

3. **Öneri:**
   - Şu aşamada workflow'ları kendi içinde tut:
     - Zamanlanmış görevler ✅
     - Araştırma ✅
     - Tarayıcı seviyesi otomasyonlar ✅
   - Hassas API key'leri veya kritik iş entegrasyonlarını henüz bağlama ❌
   - Platform olgunlaştıkça ve güvenlik kontrolleri netleştikçe → daha derin entegrasyonlara geç

---

## Adım 7: ClawHub Skill Kütüphanesi

KimiClaw'un en güçlü özelliklerinden biri - MaxClaw'da yok.

**ClawHub Nedir?**
- Topluluk tarafından oluşturulmuş 5000+ skill kütüphanesi
- Skill = detaylı kaydedilmiş prompt/workflow
- Agent otomatik keşfeder ve kurar
- Bir komutla istediğin zaman çağırabilirsin

**Skill Kurulumu:**

Prompt:
```
Find and install a suitable skill for AI news analysis
```

**Ne olur:**
1. Agent ClawHub kütüphanesini tarar
2. Uygun skill'leri bulur (ör. "AI News Collector")
3. En uygununu seçer
4. Otomatik kurar
5. Skill'in ne yaptığını ve nasıl çalıştığını açıklar
6. Çıktı formatını gösterir

**Kurulu skill'i cron job ile birleştir:**
```
Schedule AI news daily at 9:00 AM and use this skill
```

Artık günlük AI haberlerin bu skill'in formatında gelir (çok boyutlu arama stratejisi, yapılandırılmış çıktı).

**Diğer skill arama örnekleri:**

Sosyal medya analizi:
```
Find and install a skill for social media trend analysis
```

İçerik üretimi:
```
Find and install a skill for repurposing blog posts into social media content
```

Araştırma:
```
Find and install a skill for competitive market research
```

Email yazımı:
```
Find and install a skill for writing professional cold outreach emails
```

**Skill = Prompt Şablonu:**
- Skill'i bir kez kur → istediğin zaman komutla çağır
- Manuel olarak uzun prompt yazmak yerine → kısa bir komutla aynı sonucu al
- Topluluk sürekli yeni skill'ler ekliyor (5000+)

---

## Adım 8: Agent'ı Kişiselleştir

**Bot adını değiştir:**
Settings sekmesi → Bot name → değiştir

**Hafıza bilgisi ekle:**
```
Remember the following about me:
- My name is Mert
- I run an AI automation agency
- I create YouTube content in Turkish about AI tools
- I'm based in Spain, my audience is Turkish
- I'm interested in GEO/AEO, AI agents, and SaaS
- Always keep this context when helping me
```

**Dil ve ton ayarla:**
```
From now on:
- Always respond in Turkish unless I ask otherwise
- Be casual and direct, not robotic
- Never use hashtags in any content you write
- Avoid emojis unless I specifically ask
- Don't use cliché AI phrases
```

**Yazım stili:**
```
When writing content for me:
- Write naturally like a real person
- Don't alternate between very short and very long sentences
- Keep it conversational but professional
- Match the tone of each platform (LinkedIn = professional, X = punchy)
```

---

## Adım 9: Pratik Kullanım Senaryoları

### Senaryo 1: Günlük Araştırma Asistanı
```
Every morning at 8:00 AM:
1. Search for the latest AI news from the past 24 hours
2. Find any new AI tool launches
3. Check for major updates from OpenAI, Anthropic, Google, Meta
4. Summarize everything in a brief Turkish report with links
```

### Senaryo 2: İçerik Yeniden Kullanımı
```
I'm going to paste a YouTube video transcript. Please:
1. Create a LinkedIn post (max 1300 characters, professional tone, Turkish)
2. Create an X/Twitter thread (5-7 tweets, Turkish)
3. Create 3 Instagram caption options (Turkish)
4. Suggest a blog post title and outline

Here's the transcript:
[transcript yapıştır]
```

### Senaryo 3: Rakip İzleme
```
Set up weekly monitoring for: [rakip1], [rakip2], [rakip3]

Every Monday at 9:00 AM:
- Check their websites for new features or pricing changes
- Search for news mentions about them
- Check their social media for announcements
- Summarize findings in Turkish
```

### Senaryo 4: Skill Kullanarak Gelişmiş Haber Takibi
```
Find and install a skill for AI news analysis
```
Kurulduktan sonra:
```
Schedule daily AI news at 8:00 AM using the installed AI news skill. 
Deliver results in Turkish with your own commentary on what matters 
most for AI automation businesses.
```

### Senaryo 5: Email Asistanı
```
Help me draft a cold outreach email in Turkish:
- Target: Marketing directors at mid-size Turkish companies
- Offering: AI automation consulting
- Tone: Professional but warm
- Value prop: Save 10+ hours per week with AI automation
- Keep under 150 words
- No salesy language
```

---

## Adım 10: KimiClaw vs MaxClaw vs Kendi OpenClaw

### Karşılaştırma Tablosu:

| Özellik | KimiClaw | MaxClaw | Kendi OpenClaw |
|---------|----------|---------|----------------|
| Fiyat | $39/ay | $19/ay | Ücretsiz (sunucu maliyeti hariç) |
| Model | Kimi K2.5 | MiniMax M2.5 | İstediğin model |
| Kurulum | Tek tıkla | Tek tıkla | Manuel (VPS/Mac Mini gerekir) |
| Skill Kütüphanesi | ClawHub (5000+ skill) | Expert sistemi | ClawHub (manuel bağlantı) |
| Backend Görünürlük | Hayır | Evet (dosyaları görebilirsin) | Tam kontrol |
| WhatsApp | Hayır | Evet | Evet |
| Telegram | Evet | Evet | Evet |
| Discord | Evet | Evet | Evet |
| Slack | Evet | Evet | Evet |
| Kalıcı Hafıza | Evet (40 GB) | Evet | Evet |
| Cron Jobs | Evet | Evet | Evet |
| Güvenlik Kontrolü | Moonshot'ın elinde | MiniMax'ın elinde | Tamamen senin elinde |
| Olgunluk | Beta (1 haftalık) | Çok yeni (dün çıktı) | Stabil |

### Hangisini Seçmeli?

**KimiClaw ($39/ay) seç eğer:**
- ClawHub'daki 5000+ skill'e erişmek istiyorsan
- Kimi K2.5 thinking modelini tercih ediyorsan
- Skill tabanlı workflow'lar kurmak istiyorsan

**MaxClaw ($19/ay) seç eğer:**
- Bütçen kısıtlıysa (yarı fiyat)
- Backend dosyalarını görmek ve düzenlemek istiyorsan
- WhatsApp entegrasyonu lazımsa
- Expert şablonlarını tercih ediyorsan

**Kendi OpenClaw'unu kur eğer:**
- Tam kontrol istiyorsan
- İstediğin AI modelini (Claude, GPT, Gemini) kullanmak istiyorsan
- Güvenlik kritikse (token'lar senin sunucunda)
- Teknik bilgin varsa veya öğrenmeye istekliysen

---

## HIZLI BAŞLANGIÇ ÖZETİ (10 Dakika)

```
Dakika 0-1:   Hesap oluştur → $39/ay plan seç
Dakika 1-2:   "One-Click Setup" tıkla → ~1 dk bekle → workspace açılır
Dakika 2-3:   İlk cron job kur (günlük AI haber özeti)
Dakika 3-4:   Çalışan görevleri kontrol et
Dakika 4-5:   ClawHub'dan ilk skill'i bul ve kur
Dakika 5-6:   Skill'i cron job ile birleştir
Dakika 6-7:   Hafıza bilgilerini gir (kim olduğun, ne yaptığın)
Dakika 7-8:   Dil ve ton ayarlarını yap (Türkçe, doğal)
Dakika 8-9:   Telegram bağlantısı kur (opsiyonel)
Dakika 9-10:  İlk gerçek görevini ver → test et
```

**Sırasıyla kullanacağın prompt'lar:**

```
1. [One-Click Setup tıkla → 1 dk bekle]

2. Send me AI news every morning at 9:00 AM

3. What scheduled tasks do you have running?

4. Find and install a suitable skill for AI news analysis

5. Schedule AI news daily at 9:00 AM and use this skill

6. Remember: I'm [adın], I work on [alanın], my audience is [kitle].
   Always respond in Turkish unless I ask otherwise.

7. From now on, be casual and direct. Never use hashtags or emojis.
   Write naturally like a real person.

8. Connect to Telegram
   [BotFather'dan token al → yapıştır → agent'ı restart et]

9. [İlk gerçek görevini ver - araştırma, içerik üretimi, vb.]
```

---

## SONRAKİ ADIMLAR

1. **Hafta 1:** Günlük cron job'larla alış → AI haber takibi, döviz kuru vb.
2. **Hafta 2:** ClawHub'dan 3-5 skill kur → workflow'larını güçlendir
3. **Hafta 3:** Telegram'a bağla → sonuçları mobilde al
4. **Hafta 4:** Değerlendir → KimiClaw mı, MaxClaw mı, kendi OpenClaw mı?

Her iki platform da çok yeni ve hızla gelişiyor. Yeni özellikler geldikçe rehber güncellenecek.
