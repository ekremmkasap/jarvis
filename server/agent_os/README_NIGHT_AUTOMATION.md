# 🌙 JARVIS Night Automation System

## 📋 Genel Bakış

**Sen uyurken JARVIS kendini geliştiriyor!**

Night Runner, tamamen otonom bir geliştirme sistemi. Gece saat 02:00'de başlayıp, kod analizi, GitHub trending takibi, self-learning, ve dokümantasyon oluşturma gibi görevleri otomatik olarak yapıyor.

## 🎯 Özellikler

### ✅ Yapabilecekler

1. **Log Analizi** - Son 24 saatin hatalarını ve uyarılarını toplar
2. **TODO Taraması** - Koddaki TODO/FIXME'leri bulur ve kategorize eder
3. **GitHub Trending** - Güncel teknolojileri ve popüler repoları takip eder
4. **Ollama Kod Analizi** - Local LLM ile kod kalite analizi
5. **Self-Learning** - Web'den otomatik bilgi toplama ve öğrenme
6. **Health Check** - Sistem componentlerinin sağlık kontrolü
7. **Dokümantasyon** - Otomatik docs oluşturma

### 🔒 Güvenlik Katmanları

- **Staging Workspace** - Değişiklikler önce staging'de test edilir
- **Safe Directories** - Sadece belirlenen klasörlere erişim
- **Forbidden Files** - .env, credentials gibi hassas dosyalar blokludur
- **Max File Limit** - Gece max 20 dosya işlenir
- **Time Limit** - Max 4 saat çalışma süresi
- **Approval Queue** - Kritik dosyalar için onay gerekir

## 📁 Dosya Yapısı

```
server/
├── agent_os/
│   ├── night_runner.py              # Ana orchestrator
│   ├── ollama_agent.py              # Local LLM integration
│   ├── github_trending_scraper.py   # GitHub trending scraper
│   └── README_NIGHT_AUTOMATION.md   # Bu dosya
├── config/
│   ├── night_config.json            # Ana konfigürasyon
│   └── night_jobs.json              # Job queue
├── logs/
│   ├── night_runs/                  # Run logları
│   └── night_reports/               # Sabah raporları
└── agent_workspace/
    └── staging/                     # Staging dosyaları
```

## 🚀 Kurulum

### 1. Dependencies

```bash
pip install requests beautifulsoup4
```

### 2. Konfigürasyon

`.env` dosyasına (opsiyonel):
```env
ANTHROPIC_API_KEY=your_key_here  # Claude API (opsiyonel)
GOOGLE_API_KEY=your_key_here      # Google AI (kullanmıyoruz)
```

### 3. Ollama Kurulumu

```bash
# Ollama'yı çalıştır
ollama serve

# Model indir
ollama pull qwen3-vl:235b-cloud
```

## 🎮 Kullanım

### Manuel Test (Hemen Çalıştır)

```bash
cd c:\Users\sergen\Desktop\jarvis-mission-control
python server/agent_os/night_runner.py run
```

### Windows Task Scheduler ile Otomatik

1. **Task Scheduler** aç
2. **Create Basic Task** seç
3. **Name**: "JARVIS Night Runner"
4. **Trigger**: Daily, 02:00 AM
5. **Action**: Start a program
6. **Program**: `python.exe`
7. **Arguments**: `c:\Users\sergen\Desktop\jarvis-mission-control\server\agent_os\night_runner.py run`
8. **Start in**: `c:\Users\sergen\Desktop\jarvis-mission-control`

### PowerShell ile Zamanlanmış Görev

```powershell
$action = New-ScheduledTaskAction -Execute "python.exe" -Argument "server\agent_os\night_runner.py run" -WorkingDirectory "c:\Users\sergen\Desktop\jarvis-mission-control"
$trigger = New-ScheduledTaskTrigger -Daily -At 2am
Register-ScheduledTask -Action $action -Trigger $trigger -TaskName "JARVIS Night Runner" -Description "Autonomous development system"
```

## 📊 Job Types

### 1. **analyze_logs**
```json
{
  "id": "analyze_recent_logs",
  "type": "analyze_logs",
  "params": {
    "days_back": 1,
    "error_patterns": ["ERROR", "Exception"]
  }
}
```

### 2. **scan_todos**
```json
{
  "id": "scan_todos",
  "type": "scan_todos",
  "params": {
    "auto_categorize": true,
    "patterns": ["TODO", "FIXME", "HACK"]
  }
}
```

### 3. **github_trending**
```json
{
  "id": "scrape_github_trending",
  "type": "github_trending",
  "params": {},
  "description": "GitHub trending repos scrape"
}
```

### 4. **ollama_analysis**
```json
{
  "id": "analyze_agent_code",
  "type": "ollama_analysis",
  "params": {
    "directory": "server/agents",
    "analysis_type": "code_quality",
    "model": "qwen3-vl:235b-cloud"
  }
}
```

### 5. **research**
```json
{
  "id": "research_topics",
  "type": "research",
  "params": {
    "topics": ["Python async patterns"],
    "use_ollama": true
  }
}
```

### 6. **health_check**
```json
{
  "id": "check_system_health",
  "type": "health_check",
  "params": {
    "components": ["ollama", "vector_db"]
  }
}
```

## 📝 Sabah Raporu

Her gece çalıştıktan sonra `server/logs/night_reports/report_YYYYMMDD.md` oluşturulur:

```markdown
# 🌅 JARVIS Night Run Report
**Date:** 2026-03-26 06:30

## Summary
- **Jobs Completed:** 5
- **Jobs Failed:** 0
- **Files Analyzed:** 12
- **Files Modified:** 3

## Duration
- **Start:** 2026-03-26T02:00:00
- **End:** 2026-03-26T02:45:00

## Errors
✓ No errors

## Staging Files
Check `server/agent_workspace/staging/` for generated files.
```

## 🔧 Konfigürasyon

### night_config.json

```json
{
  "enabled": true,
  "schedule": {
    "run_at_hour": 2,
    "run_duration_max_hours": 4
  },
  "safety": {
    "staging_only": true,
    "max_files_per_run": 20,
    "safe_directories": [
      "server/agents",
      "server/skills",
      "docs"
    ],
    "forbidden_files": [
      ".env",
      "credentials.json"
    ]
  }
}
```

### night_jobs.json

Job'ları enable/disable edebilirsin:

```json
{
  "jobs": [
    {
      "id": "my_custom_job",
      "type": "ollama_analysis",
      "priority": 1,
      "enabled": true,  // false yap devre dışı bırak
      "params": {}
    }
  ]
}
```

## 🎯 Workflow

```
02:00 AM - Night Runner Başlar
    ↓
Job Queue Yükle
    ↓
Her Job için:
    ├─ Log Analizi
    ├─ TODO Tarama
    ├─ GitHub Trending
    ├─ Ollama Kod Analizi
    ├─ Self-Learning
    └─ Health Check
    ↓
Staging'e Kaydet
    ↓
Sabah Raporu Oluştur
    ↓
06:00 AM - Tamamlandı
```

## 🌐 Entegrasyonlar

### Ollama (Local LLM)
- Model: `qwen3-vl:235b-cloud`
- Kod analizi, dokümantasyon, research
- API key gerektirmez

### GitHub Trending
- Python, JavaScript trending repos
- Trending developers
- Otomatik knowledge base'e eklenir

### Self-Learning System
- Web crawler
- Vector DB (ChromaDB)
- RAG for enhanced responses

## 📈 Performans

- **Ortalama Süre**: 30-45 dakika
- **Max Job Count**: ~10 job/night
- **Max Files**: 20 dosya/night
- **API Calls**: 0 (sadece local Ollama)

## 🚨 Troubleshooting

### Ollama bağlanamıyor
```bash
# Ollama servisini başlat
ollama serve

# Model kontrol et
ollama list
```

### GitHub scraping hatası
```bash
# beautifulsoup4 kur
pip install beautifulsoup4

# Test et
python server/agent_os/github_trending_scraper.py digest
```

### Night Runner çalışmıyor
```bash
# Manuel test
python server/agent_os/night_runner.py run

# Logları kontrol et
cat server/logs/night_runs/run_*.json
```

## 💡 İleri Seviye

### Custom Job Eklemek

1. `night_runner.py` içinde yeni handler ekle:

```python
def _job_my_custom_task(self, params: Dict):
    """Custom task"""
    # Your logic here
    pass
```

2. `_execute_job` içinde ekle:

```python
elif job_type == "my_custom_task":
    self._job_my_custom_task(job.get("params", {}))
```

3. `night_jobs.json`'a ekle:

```json
{
  "id": "my_task",
  "type": "my_custom_task",
  "priority": 10,
  "enabled": true,
  "params": {}
}
```

### Telegram Bildirimi

Sabah raporunu Telegram'a göndermek için:

```python
# night_runner.py içinde _generate_morning_report sonuna ekle:
import requests

telegram_token = os.environ.get("TELEGRAM_BOT_TOKEN")
chat_id = os.environ.get("TELEGRAM_CHAT_ID")

if telegram_token and chat_id:
    message = f"🌅 JARVIS Night Run Completed\n\nJobs: {self.run_stats['jobs_completed']}\nFiles: {self.run_stats['files_modified']}"

    requests.post(
        f"https://api.telegram.org/bot{telegram_token}/sendMessage",
        json={"chat_id": chat_id, "text": message}
    )
```

## 🎨 Özelleştirme

### Farklı Saatte Çalıştırma

`night_config.json`:
```json
{
  "schedule": {
    "run_at_hour": 3  // 03:00'de çalışsın
  }
}
```

### Daha Agresif Mod

```json
{
  "safety": {
    "staging_only": false,  // DİKKAT: Tehlikeli!
    "max_files_per_run": 50
  }
}
```

## 🔐 Güvenlik Notları

⚠️ **ÖNEMLİ**:
- `staging_only: false` yapma (prod dosyalarını bozabilir)
- `.env` ve credentials her zaman forbidden listede kalsın
- Yeni job'lar eklerken önce manuel test et
- Kritik dosyaları `require_approval_for` listesine ekle

## 📚 Örnekler

### Örnek 1: Sadece Log Analizi

```json
{
  "jobs": [
    {
      "id": "logs_only",
      "type": "analyze_logs",
      "enabled": true,
      "params": {"days_back": 7}
    }
  ]
}
```

### Örnek 2: GitHub + Self-Learning

```json
{
  "jobs": [
    {
      "id": "github",
      "type": "github_trending",
      "enabled": true
    },
    {
      "id": "learn",
      "type": "research",
      "params": {
        "topics": ["Latest AI trends", "Python 3.12 features"]
      }
    }
  ]
}
```

### Örnek 3: Full Automation

Tüm job'lar enabled, her gece tam otomasyon.

## 🎉 Sonuç

Night Runner sayesinde:
- ✅ Her sabah fresh kod analizi
- ✅ Güncel teknoloji takibi
- ✅ Otomatik dokümantasyon
- ✅ Self-improving system
- ✅ Zero manual intervention

**Sen uyurken, JARVIS gelişiyor! 🚀**

---

*Made with ❤️ by Ekrem & Claude Code*
*Version 1.0.0 - 2026-03-26*
