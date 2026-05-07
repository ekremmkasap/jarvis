# 🧠 Jarvis Core Update: Master Implementation Prompt

**Görev Emirleri:** Bu metni kopyala ve doğrudan Claude'a (veya Cursor/Cline'a) yapıştır.

---
*(Buradan aşağısını kopyalayıp Claude'a ver)*

**ROLE:**  
Sen üst düzey bir Yapay Zeka Sistem Mimarı ve Python/TypeScript tam yığın (full-stack) geliştiricisisin. Şu anda "Jarvis Mission Control" (Mark-XXXV) otonom swarm (kalkan) sistemini geliştiriyoruz. Görevin, aşağıdaki 5 temel "Core Skill" (Ana Yetenek) modülünü mevcut Jarvis mimarisine entegre etmek, gerekli ajanları/fonksiyonları yazmak ve kod tabanına dahil etmektir.

**CONTEXT & WORKSPACE:**
Projenin konumu `C:\Users\sergen\Desktop\jarvis-mission-control` veya `C:\Users\sergen\jarvis` dizinlerinden aktif olanıdır. Lütfen adım adım ilerle, önce mevcut dosya yapısındaki `skills/` veya `agents/` klasörlerini analiz et ve ardından her özelliği modüler bir yapı olarak kodla. Eğer `Context7` veya diğer MCP'leri (Model Context Protocol) kullanman gerekirse API dökümanlarını oradan çekebilirsin.

### 🎯 EKLENECEK 5 ANA YETENEK (THE BACKLOG):

#### 1. File I/O & Core Notepad Skill (Dosya Yönetimi)
**Sorun:** Jarvis şu an istenen metinleri `.txt` dosyasına dönüştürüp kaydedemiyor.
**Hedef:** Sisteme bir `FileSystemAgent` veya `WriteToFileSkill` ekle.
- Kullanıcı komutuyla anında belirlenen dizinlerde (Özellikle masaüstünde) hedef uzantılı (genelde `.txt` veya `.md`) dosyalar oluşturmalı.
- Geçici veya kalıcı hafıza verilerini, kendisine dikte edilen metinleri sorunsuzca dosyaya yazabilmeli.

#### 2. WhatsApp Automation Skill (İletişim)
**Hedef:** Jarvis'in WhatsApp üzerinden işlem yapabilmesi.
- Gerekli Python kütüphaneleri (örneğin `pywhatkit`, `selenium`, `playwright` veya `WhatsApp Web.js`) kullanılarak bir `WhatsAppSkill` oluşturulmalı.
- Bu yetenek sayesinde Jarvis: Belirtilen kişiyi bulmalı, mesaj yazmalı ve göndermeli.

#### 3. Web & Google Integration Skill (Arama & Analiz)
**Hedef:** Jarvis'in tam otonom web erişimi kazanması.
- Google'da arama yapabilmesi, SERP (Search Engine Results Page) sonuçlarını okuyabilmesi ve belirtilen web sayfalarının DOM/Metin içeriğini kazıyabilmesi (örneğin `BeautifulSoup`, `Playwright` veya `Tavily API` ile).
- Herhangi bir konu sorulduğunda veya "araştır" denildiğinde otonom olarak web sub-agent'ını tetiklemeli.

#### 4. Dual-Monitor Vision System (Ekran Analiz Güncellemesi)
**Hedef:** Sadece ana ekranı değil, çoklu monitörleri analiz edebilme.
- Mevcut `VisionAgent` veya ekran okuma fonksiyonunu güncelle.
- İşletim sisteminden (`mss` veya benzeri bir kütüphane ile) tüm ekranların (Display 1 & Display 2) anlık görüntüsünü (screenshot) alıp tek bir bağlamda yapay zekaya sunacak şekilde kodu refactor et. "Ekranımı analiz et" dendiğinde *kombine* bir analiz dönmeli.

#### 5. Hologram UI Revert & Copilot Mode (Kullanıcı Arayüzü)
**Hedef:** Parçalanmış arayüzlerin birleştirilmesi ve Copilot-vari deneyim.
- Next.js / TypeScript ile yazılmış Hologram UI arayüzünü tek bir merkez eklentide birleştir. Eski "temiz" sürüme geri dön (gerekirse git history'den eski component'i bul).
- **Global Kısayol / Wake Word:** "Hey Jarvis" sesli komutu algılandığında veya global bir klavye kısayoluyla, Windows Copilot / Spotlight tarzı ekranın sağından veya ortasından kayarak/açılarak gelen bir overlay (katman) arayüzüne dönüştür.

---
### ⚙️ EXECUTION PROTOCOL (Nasıl İlerleyeceksin?)
1. **Analiz Et:** Repository içinde `skills/` veya `agents/` yapısını incele.
2. **Plan Sun:** Bu 5 yeteneği nasıl entegre edeceğine dair adım adım kısa bir plan dön.
3. **Kodla ve Test Et:** Modüler yetenek dosyalarını oluştur, ana ajan registry'sine (örn: `agents/registry.py` veya `index.ts`) kaydet.
4. **Onay İste:** Her modül bitişinde "Kullanıcı onayına hazır" şeklinde çıktı ver. Kullanıcı ve Antigravity sistemi (Codex) kodların doğrulamasını birlikte yürütecek.

*Anlaşıldıysa mevcut projedeki dosya ağacını inceleyerek çalışmaya başla.*
