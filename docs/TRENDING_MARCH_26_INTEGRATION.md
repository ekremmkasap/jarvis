# JARVIS - Mart 2026 Trend Entegrasyon Planı

11-18 Mart 2026 tarihleri arasında trend olan 5 kritik GitHub reposundan alınan stratejiler JARVIS sistemine resmi olarak entegre edilmiştir.

## 1. Mimaride Asenkron Yönetim (Async Coding Agent Alternatifi)
- **Problem:** Senkron görev sıralaması ajanları yavaşlatıyordu.
- **Entegrasyon:** JARVIS'in `Orchestrator` yapısı, tıpkı *Open-Source Asynchronous Coding Agent* ve *Claude Code* gibi tamamen asenkronize (aynı anda birden çok skill çalıştırabilen) bir yapıya güncelleniyor.

## 2. Hafıza Mimarisi: OpenViking (Context DB) Parametresi
- **Problem:** Düz metin dosyası tabanlı basit WM/PM hafızası büyüdükçe tıkanabilir.
- **Entegrasyon:** `MEMORY.md` güncellenerek hiyerarşik dosya sistemi paradigmasını kullanan açık kaynaklı *OpenViking* veritabanı yapısına (Memory, Resource, Skill Context izolasyonu) geçiriliyor.

## 3. Ajan Uzmanlaşması: agency-agents Şablonları
- **Problem:** Genel amaçlı tek ajan her şeyi iyi yapamaz.
- **Entegrasyon:** Çekirdek ajan mimarisine ek olarak (tıpkı `agency-agents` deposundaki 51 özel ajan gibi), JARVIS için Shell ve rol tabanlı *uzman ajan havuzu* şablonu getirildi. Core ajan görevleri bunlara dağıtarak kaliteyi artıracak.

## 4. Güvenlik İzolasyonu: OpenSandbox
- **Problem:** Yerel sunucuda rastgele Python veya sistem kodları çalıştırmak riskli.
- **Entegrasyon:** Ajan sisteminin kod çalıştırdığı skill'lerinde (özellikle Coding Agent ve GUI Agent yeteneklerinde) kodların doğrudan bilgisayarı etkilememesi için *OpenSandbox* (Multi-language SDK, Docker/K8s RunTime izolasyonu) referans alınarak güvenli çit (sandbox) eklendi.

## 5. RAG ve Veri Okuma: GitNexus Modeli
- **Problem:** Devasa kod veya metin yığınlarında sadece okuyup arama yapmak mantıksal bağlantıları kaçırır.
- **Entegrasyon:** RAG (Retrieval-Augmented Generation) yeteneği olarak *GitNexus* mimarisi (Sıfır sunucu ile Graph RAG, interaktif knowledge graph yeteneği) `SKILLS.md`'ye eklendi. JARVIS artık bir repo verildiğinde bağlantı grafiği çıkararak okuyacak.
