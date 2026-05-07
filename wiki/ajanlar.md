# Jarvis — Ajan Kataloğu

## Aktif Ajanlar

| Ajan | ID | Risk | Oto-Onay | Görev |
|------|----|------|----------|-------|
| [[planner-ajan\|PlannerAgent]] | `planner` | Düşük | ✅ | Hedefi plana çevirir |
| [[developer-ajan\|DeveloperAgent]] | `developer` | Orta | ❌ | Kod yazar, bug düzeltir |
| [[reviewer-ajan\|ReviewerAgent]] | `reviewer` | Düşük | ✅ | PR inceler (read-only) |
| DebugAgent | `debug` | Düşük | ✅ | CI/runtime hataları diagnoz |
| ReleaseAgent | `release` | Orta | ✅ (taslak) | Changelog, release notları |
| DocsAgent | `docs` | Düşük | ✅ | Dokümantasyon günceller |
| VoiceNarratorAgent | `voice_narrator` | Düşük | ✅ | TTS için metin üretir |
| MissionControlAgent | `mission_control` | Düşük | ✅ | Sistem sağlık monitörü |
| RepoAnalystAgent | `repo_analyst` | Düşük | ✅ | Repo sağlık analizi |

## Otomasyon Politikası

### Otomatik Onaylanan
- Issue triage, PR review, kod analizi, CI diagnoz
- Changelog taslağı, dokümantasyon, dashboard

### Onay Gerektiren
- Protected branch merge (main/master/release/prod)
- Force push, dosya/branch silme
- Secret rotasyonu, shell komutları

### Bloklanan (Asla)
- Destructive filesystem operasyonları
- Billing/payment değişiklikleri
- Credential sızdırma

## Yeni Ajan Ekleme
1. `agents/your_agent.py` → `RuntimeAgent` extend et
2. `name`, `description`, `model_chain`, `risk_level` set et
3. `execute_task(self, task) -> str` implement et
4. `agents/registry.py`'e kaydet
5. `config/agents.yaml`'a ekle

## İlgili Sayfalar
- [[mimari-genel-bakis]]
- [[model-routing]]
