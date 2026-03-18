# MaxClaw Rehberi: OpenClaw Agent'ını 10 Dakikada Kur ve Çalıştır

MiniMax'ın bulut tabanlı OpenClaw çözümü. Agent'ını deploy et, mesajlaşma uygulamalarına bağla, otomasyonlar kur - hepsi tarayıcıdan.

---

## MaxClaw Nedir?

MaxClaw, MiniMax'ın OpenClaw framework'ü üzerine inşa ettiği bulut tabanlı AI agent platformu. Rakibi KimClaw'dan (Moonshot/Kimi) farklı olarak:

- Fiyat: $19/ay (KimClaw $39/ay → yarı fiyat)
- Model: MiniMax M2.5 (KimClaw = Kimi K2.5)
- Özel özellik: Backend dosyalarını görebilir ve düzenleyebilirsin
- Expert sistemi: Hazır agent şablonları (KimClaw'da "skills marketplace" var)
- WhatsApp desteği var (KimClaw'da yok)
- Agent her zaman bulutta çalışır → tarayıcıyı kapatsan bile görevler devam eder

---

## Adım 1: Hesap Oluştur

1. **MaxClaw sitesine git** ve "Start" butonuna tıkla
2. MiniMax hesabına giriş yap (veya yeni hesap oluştur)
3. **Ücretli plan seç** → En düşük plan: Basic ($19/ay)
   - MaxClaw'a erişim için ücretli hesap zorunlu
   - Öneri: 1 aylık dene, beğenirsen devam et
4. Ödemeyi tamamla → "Start Now" tıkla

---

## Adım 2: Expert Seç ve Agent'ı Deploy Et

Hesap açıldıktan sonra karşına "Expert seçim" ekranı gelir. Bu, KimClaw'dan farklı olan ilk şey - boş agent yerine hazır şablonlardan başlıyorsun.

**Mevcut Expert'ler:**
- **Default** → Genel amaçlı agent (başlangıç için önerilen)
- **Topic Tracker** → Konu takibi
- **Trend Intel** → Sosyal medya trend izleme
- **Industry Research Expert** → Sektör araştırması
- **Image Craft** → Görsel oluşturma
- **Multi-Agent Trading Setup** → Çoklu agent ile trading
- Sağ üstteki "All Experts" → tüm seçenekleri gösterir

**Yapılacak:**
1. "Default" seç (genel amaçlı, ilk deneme için ideal)
2. "I'm Ready" butonuna tıkla
3. **10 saniye bekle** → Agent deploy edilir
4. Workspace açılır → chat arayüzü karşına gelir

---

## Adım 3: Workspace'i Tanı

Agent deploy edildikten sonra bir chat arayüzü açılır. Agent seni karşılar ve neler yapabileceğini anlatır.

**Arayüz Yapısı:**
- **Sol taraf:** Chat alanı (agent ile konuşma)
- **Sağ taraf:** İşlem paneli (agent'ın yaptığı aksiyonları gösterir)
- **Sol sidebar:** Expert'leri keşfet, ayarlar

**Önemli Fark (KimClaw'dan):**
- Bu sadece bir chatbot DEĞİL
- Agent her zaman bulutta çalışır
- Zamanlı görev verirsen → tarayıcıyı kapatsan bile çalışmaya devam eder
- Ertesi gün girdiğinde sonuçları görürsün

---

## Adım 4: Backend Dosyalarını İncele

Bu MaxClaw'un en ilginç özelliği - KimClaw'da yok.

**Yapılacak:**
1. Sağ panelde "Files" sekmesine tıkla
2. Agent'ı oluşturan tüm dosyaları görürsün

**Dosyalar ve Anlamları:**

| Dosya | Ne İşe Yarar |
|-------|-------------|
| `soul.md` | Agent'ın kişiliği ve kimliği - "Sen kimsin" tanımı |
| `heartbeat.md` | Agent'ın sürekli çalışan arka plan görevleri |
| `bootstrap` | Agent'ın başlangıç yapılandırması |
| `agents.mmd` | Agent davranış kuralları ve akış şeması |

**İki Yolla Düzenleyebilirsin:**
1. Dosyaya tıkla → doğrudan düzenle → kaydet
2. Chat'te agent'a söyle → o düzenlesin

**Örnek - Kişiliği Değiştirme:**
Chat'te şunu yaz:
```
Update your soul.md file. Change your personality to be more professional 
and formal. Respond in Turkish by default. Your name is "Asistan".
```

---

## Adım 5: Telegram'a Bağla

Agent'ını Telegram'da kullanmak için:

**Chat'te şu prompt'u yaz:**
```
Connect to Telegram
```

**Agent'ın cevabı:**
- "Telegram bot token'ı lazım" der
- Token alma talimatlarını verir

**Telegram Bot Token Alma:**
1. Telegram'da `@BotFather`'a git
2. `/newbot` yaz
3. Bot'a isim ver (ör. "MaxClaw Asistanım")
4. Bot'a username ver (ör. "maxclaw_mert_bot")
5. BotFather sana bir token verir (uzun bir metin)
6. Bu token'ı MaxClaw chat'ine yapıştır

**Yapıştırdıktan sonra:**
- Agent Telegram bağlantısını kurar
- Artık Telegram'dan da agent'ınla konuşabilirsin
- Telegram'dan verdiğin görevler de bulutta çalışır

**Diğer Bağlanabilir Platformlar:**
- Slack
- Discord
- WhatsApp (MaxClaw'a özel, KimClaw'da yok)

Her biri için benzer şekilde chat'te "Connect to [platform]" yaz → talimatları takip et.

---

## Adım 6: Zamanlanmış Görev (Cron Job) Oluştur

Bu, MaxClaw'un en güçlü özelliği - otomatik tekrarlayan görevler.

**Örnek Prompt - Günlük AI Haber Özeti:**
```
Send me daily AI news summary every morning at 9:00 AM
```

**Ne olur:**
- Agent bir "cron job" oluşturur
- Sağ panelde istek ve yanıtı görürsün
- "Done. Daily AI news summary is scheduled for every morning at 9:00 AM" der
- Tarayıcıyı kapatsan bile yarın sabah 9'da çalışır

**Çalışan Görevleri Kontrol Et:**
```
What scheduled tasks do you have running currently?
```

**Cevap şöyle görünür:**
- Görev adı: Daily AI News Summary
- Zamanlama: Her gün 09:00
- Sonraki çalışma: [yarının tarihi] 09:00

**Diğer Cron Job Örnekleri:**

Haftalık rakip analizi:
```
Every Monday at 8:00 AM, search the web for the latest news about 
[rakip şirket adı] and summarize the key updates for me.
```

Günlük sosyal medya trend raporu:
```
Every day at 7:00 PM, find the top 5 trending topics on X/Twitter 
related to AI and automation. Summarize each in 2-3 sentences.
```

Haftalık içerik fikri üretimi:
```
Every Wednesday at 10:00 AM, generate 5 YouTube video ideas about 
AI tools and automation. Include potential titles and brief descriptions.
```

Günlük döviz kuru takibi:
```
Every morning at 8:30 AM, check the USD/TRY exchange rate and 
send me a brief update with the current rate and daily change.
```

**Cron Job Silme:**
```
Delete the daily AI news summary cron job
```

**Tüm Cron Job'ları Listeleme:**
```
List all my active cron jobs with their schedules
```

---

## Adım 7: Custom Expert Oluştur

Hazır expert'ler yetmiyorsa kendi özel agent'ını oluşturabilirsin.

**Yapılacak:**
1. Sol sidebar → "Explore Experts" tıkla
2. Sağ üst köşe → "Create" tıkla
3. Custom expert oluşturma penceresi açılır

**Ne Olur:**
- Oluşturduğun expert için tüm dosyalar otomatik üretilir:
  - `soul.md` → kişilik
  - `agents.mmd` → davranış kuralları
  - `heartbeat.md` → arka plan görevleri
- Hepsi senin tanımına göre özelleştirilir

**Örnek - Türkçe İçerik Asistanı Expert'i:**
Create ekranında şunu tanımla:
```
Expert Name: Turkish Content Assistant
Description: An expert that helps create and repurpose Turkish content 
for YouTube, LinkedIn, X/Twitter, and Instagram. It should understand 
Turkish internet culture, use natural Turkish language (not formal/robotic), 
and optimize content for each platform's algorithm. It should be able to 
take a blog post or video transcript and create platform-specific content.
```

**Hazır Expert Kurma:**
1. "Explore Experts" sayfasında bir expert seç (ör. "Landing Page Builder")
2. Tıkla → Kur
3. O expert'e özel dosyalar otomatik oluşturulur
4. Backend dosyalarını inceleyerek nasıl yapılandırıldığını öğrenebilirsin

**İpucu:** Hazır expert'lerin dosyalarını incelemek, kendi custom expert'ini yaparken ilham kaynağı olur. `soul.md` ve `agents.mmd` dosyalarına bak → kendi agent'ın için benzer yapı oluştur.

---

## Adım 8: Agent'ı Kişiselleştir

**Kişilik Değiştirme:**
```
Update your personality. From now on:
- Always respond in Turkish
- Be casual and friendly, not robotic
- Use "sen" instead of "siz"
- When giving news summaries, add your own brief commentary
- Your name is "Max"
```

**Hafıza Özelliği:**
MaxClaw her konuşmadan öğrenir. Bunu hızlandırmak için:
```
Remember the following about me:
- I run an AI automation agency
- I create YouTube content about AI tools
- I'm based in Spain but my audience is Turkish
- I'm interested in GEO/AEO, AI agents, and SaaS
- My main platforms are YouTube, LinkedIn, and X/Twitter
```

**Yazım Stili Belirleme:**
```
When writing content for me, follow these rules:
- Never use hashtags
- Avoid emojis unless I specifically ask
- Don't alternate between very short and very long sentences
- Write naturally, as if a real person is writing
- Avoid cliché AI phrases like "game-changer", "revolutionize", "unleash"
```

---

## Adım 9: Pratik Kullanım Senaryoları

### Senaryo 1: Günlük Araştırma Asistanı
```
Every morning at 8:00 AM:
1. Search for the latest AI news from the past 24 hours
2. Find any new AI tool launches
3. Check if there are any major updates from OpenAI, Anthropic, Google, or Meta
4. Summarize everything in a brief Turkish report
5. Include links to the most important articles
```

### Senaryo 2: Rakip Takip Sistemi
```
Set up monitoring for these competitors: [rakip1], [rakip2], [rakip3]

Every Monday and Thursday at 9:00 AM:
- Check their websites for new features or pricing changes  
- Search for any news mentions
- Check their social media for new announcements
- Send me a summary of findings
```

### Senaryo 3: İçerik Yeniden Kullanımı
```
I'm going to paste a YouTube video transcript. Please:
1. Create a LinkedIn post (max 1300 characters, professional tone)
2. Create an X/Twitter thread (5-7 tweets)
3. Create 3 Instagram caption options
4. Create a blog post outline with key points

Here's the transcript:
[transcript'i yapıştır]
```

### Senaryo 4: Email Taslağı Asistanı
```
Help me draft a cold outreach email:
- Target: Marketing directors at mid-size Turkish companies
- Offering: AI automation consulting
- Tone: Professional but warm, in Turkish
- Include a specific value proposition about saving 10+ hours per week
- Keep it under 150 words
```

### Senaryo 5: Günlük Görev Hatırlatıcısı
```
Every weekday at 8:00 AM, remind me to:
1. Check and respond to LinkedIn messages
2. Review yesterday's analytics
3. Create one piece of content

Every Friday at 5:00 PM, ask me to:
1. Review the week's performance
2. Plan next week's content calendar
3. Update my project tracker
```

---

## Adım 10: İpuçları ve Dikkat Edilecekler

### MaxClaw'un Güçlü Yanları:
- Backend dosyalarını görebilir ve düzenleyebilirsin (KimClaw'da yok)
- WhatsApp desteği (KimClaw'da yok)
- Yarı fiyat ($19 vs $39)
- Expert sistemi ile hızlı başlangıç
- Cron job'lar tarayıcı kapalıyken bile çalışır

### Sınırlamalar:
- Henüz çok yeni (dün çıktı) → özellikler hızla değişecek
- KimClaw'un 5000+ skill marketplace'i yok → bunun yerine expert sistemi var
- MiniMax M2.5 modeli kullanıyor (kendi OpenClaw'unda istediğin modeli seçebilirsin)

### MaxClaw vs KimClaw Karşılaştırması:

| Özellik | MaxClaw | KimClaw |
|---------|---------|---------|
| Fiyat | $19/ay | $39/ay |
| Model | MiniMax M2.5 | Kimi K2.5 |
| Skill Sistemi | Expert şablonları | ClawHub (5000+ skill) |
| Backend Görünürlük | Evet (dosyaları görebilirsin) | Hayır |
| WhatsApp | Evet | Hayır |
| Telegram | Evet | Evet |
| Discord | Evet | Evet |
| Slack | Evet | Evet |
| Cloud Hosted | Evet | Evet |
| Cron Jobs | Evet | Evet |

### Kendi OpenClaw vs Hosted Çözümler:
- Kendi OpenClaw'unu kurarsın → istediğin modeli seçersin (Claude, GPT, Gemini vb.)
- Ama kurulum ve bakım senin sorumluluğun
- MaxClaw/KimClaw → tek tıkla deploy, sıfır bakım
- Yeni başlıyorsan → MaxClaw ($19) ile dene, sonra kendi OpenClaw'unu kur

---

## HIZLI BAŞLANGIÇ ÖZETİ (10 Dakika)

```
Dakika 0-1:   Hesap oluştur → Basic plan ($19/ay) seç
Dakika 1-2:   "Default" expert seç → "I'm Ready" tıkla → 10 sn deploy
Dakika 2-3:   Files sekmesinden backend dosyalarını incele
Dakika 3-4:   Kişiliği Türkçe'ye çevir (soul.md güncelle)
Dakika 4-5:   "Connect to Telegram" → bot token al → yapıştır
Dakika 5-7:   İlk cron job'ı kur (günlük AI haber özeti)
Dakika 7-8:   "Explore Experts" → hazır expert'leri incele
Dakika 8-9:   Hafıza bilgilerini gir (kim olduğun, ne yaptığın)
Dakika 9-10:  İlk gerçek görevini ver → test et
```

**İlk 10 dakikada kullanacağın prompt'lar sırasıyla:**

```
1. [Expert seçim ekranında] → Default seç → I'm Ready

2. Update your soul.md. Respond in Turkish. Your name is "Max". 
   Be casual and helpful.

3. Connect to Telegram
   [BotFather'dan token al → yapıştır]

4. Send me daily AI news summary every morning at 9:00 AM

5. What scheduled tasks do you have running currently?

6. Remember: I'm [adın], I work on [alanın], my audience is [kitle]. 
   Always keep this context in mind.

7. [İlk gerçek görevini ver - ör. içerik üretimi, araştırma, vb.]
```

---

## SONRAKİ ADIMLAR

1. **Hafta 1:** Günlük cron job'larla AI haber takibi yap
2. **Hafta 2:** Telegram entegrasyonunu aktif kullan
3. **Hafta 3:** Custom expert oluştur (kendi iş alanına özel)
4. **Hafta 4:** Değerlendir → MaxClaw yeterli mi yoksa kendi OpenClaw mı kurmalısın?

Platform çok yeni - MiniMax sürekli güncelleme yapacak. Yeni özellikler geldikçe bu rehber güncellenecek.
