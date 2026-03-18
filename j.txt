Aynen. FAZ 1’de hedefimiz: **Jarvis / Mission Control’un çekirdek mimarisini** “modüler, genişletilebilir, denetlenebilir” şekilde kurmak.

Aşağıdaki tasarım; **Core Agent + Sub-agent + Memory + Skills** yapısını netleştirir, aynı zamanda “görev orkestrasyonu, durum yönetimi, güvenlik/izin, log/izlenebilirlik, geri dönüş (rollback)” gibi Mission Control’ün olmazsa olmazlarını kapsar.

---

## 1) Sistem Bileşenleri (Yüksek seviye)

**A) Mission Control (Orchestrator)**

* Kullanıcıdan gelen isteği “görev”e çevirir.
* Plan üretir, alt ajanlara böler, yürütmeyi yönetir.
* Çalışma boyunca: durum, log, çıktı, hata, tekrar deneme akışını yönetir.

**B) Core Agent (Executive / Brain)**

* Tek “karar verici” merkez.
* Alt ajanları görevlendirir, sonuçları birleştirir, final çıktıyı üretir.
* Kurallar: izin, politika, güvenlik, kalite barajları.

**C) Sub-Agents (Uzmanlar)**

* Her biri tek rol/uzmanlık: “planner”, “researcher”, “coder”, “reviewer”, “ops”, “qa”, “summarizer” gibi.
* Core Agent tarafından çağrılır.
* Kendi “tool/skill” setine sahiptir (kısıtlı yetki).

**D) Skills (Yetenekler)**

* Tek bir iş yapan, tekrar kullanılabilir fonksiyonlar.
* “Saf fonksiyon” gibi düşün: giriş → deterministik işleme → çıkış (+ log).
* Örn: `parse_requirements`, `create_task_graph`, `write_patch`, `run_tests`, `summarize_results`.

**E) Memory (Bellek Katmanları)**

* Kısa vadeli çalışma belleği + uzun vadeli “proje hafızası” + “bilgi tabanı”.
* “Ne zaman yazılır / ne zaman okunur” kuralları net.

**F) State + Observability (Durum/İzleme)**

* Her görevin: durum makinesi, olay günlüğü, artefaktlar, karar kayıtları.
* Debug ve kalite için şart.

---

## 2) Çekirdek Veri Modeli (Net terminoloji)

### Task (Görev)

* `id`, `title`, `goal`, `constraints`, `inputs`, `acceptance_criteria`
* `status`: `queued | planning | running | waiting | blocked | done | failed | cancelled`
* `plan`: adımlar / alt görevler
* `artifacts`: dosyalar, notlar, linkler
* `events`: log + kararlar

### Run (Çalıştırma / Oturum)

* “Bu görev şu zaman şu konfigle yürüdü” kaydı.
* Reproducibility için: model/konfig/skill sürümleri.

### Agent Call

* “Core → Sub-agent” çağrısı.
* `agent_role`, `prompt`, `inputs`, `outputs`, `confidence`, `cost` (FAZ 1’de saymıyoruz), `tool_calls`, `trace_id`

### Skill Invocation

* “Agent → Skill” çağrısı.
* `skill_name`, `args`, `result`, `side_effects`, `logs`

---

## 3) Bellek Tasarımı (3 katman)

### 3.1 Working Memory (WM) — anlık

* Sadece mevcut görev için.
* Plan, ara çıktılar, kısa notlar.
* Oturum bitince arşivlenir (kalıcı değil).

### 3.2 Project Memory (PM) — kalıcı “Jarvis hafızası”

* Projenin kuralları, tercihleri, mimari kararlar, checklist’ler, “bunu böyle yapıyoruz”lar.
* “CLAUDE.md” benzeri: **MISSION.md / MEMORY.md**.
* Yazma kuralı: sadece **tekrarlı veya stratejik** bilgi.

### 3.3 Knowledge Store (KS) — referans

* Döküman özetleri, standartlar, snippet’ler, şablonlar.
* İndekslenebilir yapı: etiketler, kaynak, tarih.

**Memory Gate (kritik)**

* Her şey belleğe yazılmaz.
* Core Agent “Memory Curator” mantığıyla:

  * “Bu bilgi tekrar lazım mı?”
  * “Genel mi proje özel mi?”
  * “Güncellenebilir mi / sürüm gerekir mi?”

---

## 4) Agent Rolleri (Önerilen minimum set)

### Core Agent (Executive)

* Görev analizi, planlama, delegasyon, birleştirme, final.
* “Policy + Quality Gate” burada.

### Sub-Agents

1. **Planner**

   * Hedef → adımlar → bağımlılıklar → riskler
   * Task graph çıkarır.
2. **Implementer (Builder/Coder)**

   * Kod/konfig üretir (FAZ 1’de tasarım çıktıları üretir).
3. **Reviewer (Critic)**

   * Plan/çıktı kalite kontrol, açık/çelişki bulma.
4. **Memory Curator**

   * Proje hafızasına ne yazılacak karar verir.
5. **Operator (Ops)**

   * Komut/ortam süreçleri (FAZ 1’de sadece prosedür tasarımı).

İlk MVP için 3 sub-agent bile yeter:

* Planner + Implementer + Reviewer
  Memory Curator’ı Core içinde de tutabilirsin.

---

## 5) Skills Sistemi (Yetenek mimarisi)

**Skill = “küçük, test edilebilir, log’lanabilir, yeniden kullanılabilir”**

* “agent her seferinde promptla iş uydurmasın”, standart akışlar oluşsun.

### Skill türleri

* **Cognitive skills**: plan çıkarma, requirement parsing, risk assessment
* **Execution skills**: dosya yazma, test koşturma, komut çalıştırma
* **IO skills**: veri okuma, parse etme, format dönüştürme
* **Governance skills**: policy check, redaction, approval gate

### Skill Manifest

Her skill için:

* `name`, `version`
* `inputs schema`, `outputs schema`
* `permissions` (neye erişebilir)
* `failure modes` (ne zaman fail olur)
* `logs` (hangi eventleri üretir)

---

## 6) Orkestrasyon (Mission Control akışı)

### 6.1 Standart akış

1. **Intake**

   * Kullanıcı isteği → “Task” nesnesi
2. **Clarify (gerekirse)**

   * Eksik kritikleri tespit (FAZ 1’de minimal)
3. **Plan**

   * Planner → plan + task graph
4. **Dispatch**

   * Alt görevleri sub-agent’lara dağıt
5. **Execute**

   * Skill çağrıları ile adımları yürüt
6. **Review**

   * Reviewer → kalite/hata/çelişki kontrol
7. **Synthesize**

   * Core → final çıktı + next steps
8. **Memory update**

   * Memory Curator → PM/KS güncelle

### 6.2 Durum Makinesi

* `queued → planning → running → reviewing → done`
* Hata: `running → blocked/failed`
* Dış bağımlılık: `waiting`

---

## 7) Güvenlik / İzin Modeli (FAZ 1 tasarım)

**En önemli kural:** Sub-agent “kendi kafasına göre” yetki büyütemez.

* **Capability-based permissions**

  * Her ajan + skill’in yetkisi ayrı.
  * Örn: Reviewer sadece okur, yazamaz.
* **Policy Gate**

  * Tool/skill çağrıları “pre-check”ten geçer.
* **Audit trail**

  * Her önemli karar: “neden bu adım?” kaydı.

---

## 8) Çıktı Artefaktları (Faz 1 için hedef deliverable)

FAZ 1 sonunda elinizde şunlar net olmalı:

* `ARCHITECTURE.md` (bu mesajın resmileştirilmiş hali)
* `AGENTS.md` (roller + yetkiler)
* `SKILLS.md` (skill manifest + şablon)
* `MEMORY.md` (bellek katmanları + yazma/okuma politikası)
* `STATE_MODEL.md` (task lifecycle + event types)
* `QUALITY_GATES.md` (review checklist’leri)

---

## 9) Örnek: “Bir görev nasıl yürür?” (Somut senaryo)

Kullanıcı: “Repo’da X modülünü yeniden tasarla”

1. Core: Task oluşturur, kısıtları çıkarır.
2. Planner: adımlar + alt görevler + acceptance criteria.
3. Implementer: tasarım dokümanı + modül arayüzleri önerisi.
4. Reviewer: çelişki/risk/eksik senaryo.
5. Core: final sentez + yapılacaklar listesi.
6. Memory Curator: “Bu projede modül tasarım standardı şudur” gibi kalıcı not.

---

## 10) “Netleştirme” (Senin istediğin 4 yapı)

* **Core Agent:** tek otorite, orkestrasyon + karar + kalite kapısı
* **Sub-agents:** dar kapsamlı uzmanlar, kısıtlı yetkiyle çalışır
* **Memory:** WM (anlık) + PM (kalıcı proje hafızası) + KS (referans)
* **Skills:** tekrar kullanılabilir fonksiyonlar, manifest + izin + log ile

---

İstersen FAZ 1’i bir adım daha “tam paket” hale getireyim:
**Jarvis/Mission Control için tek sayfalık “Architecture Blueprint”** (component diagram metinsel), üstüne de **Agent/Skill permission matrix** (hangi rol hangi skill’i çağırabilir) çıkarayım.
