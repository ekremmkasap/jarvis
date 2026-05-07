# CloudManagerSystem + SkillRegistry Handoff

## Part A

Calisanlar:
- `server/skills/aws_ec2_skill.py`: EC2 listeleme, baslatma, durdurma, durum ozeti
- `server/skills/aws_s3_skill.py`: bucket listeleme, obje listeleme, bucket boyutu, upload, delete
- `server/skills/aws_cost_skill.py`: aylik maliyet, trend, budget alert fallback, local threshold kaydi
- `server/bridge.py`: `/cloud-*` Telegram komutlari ve `/api/cloud/*` endpointleri
- `apps/web-ui/src/app/cloud/page.tsx`: `/cloud` operator dashboard

Gercek AWS credential gerektirenler:
- EC2 start/stop/list/status
- S3 bucket/object islemleri
- Cost Explorer verisi
- AWS Budgets verisi icin ek olarak `AWS_ACCOUNT_ID`

Credential olmadan ne olur:
- Testler boto3 mock ile calisir
- `aws_cost_skill.get_monthly_cost()` mock fallback donebilir
- UI yine acilir, cost paneli mock notu gosterebilir

## Part B

SkillRegistry:
- Dosya: `server/skill_registry.py`
- Migre edilen komut sayisi: `12`
- Alias: `/codex-status` -> `/codex-durum`

Migre edilen komutlar:
- Cloud: `/cloud-durum`, `/cloud-ec2-liste`, `/cloud-ec2-baslat`, `/cloud-ec2-durdur`, `/cloud-s3-liste`, `/cloud-maliyet`
- Help: `/yardim`
- Ops: `/codex`, `/codex-swarm`, `/codex-durum`, `/codex-sonuc`, `/wiki`

Yeni skill ekleme:
1. Handler yaz: `server/..._command_handlers.py` veya uygun skill modulunde `(args, context) -> str`
2. Registry entry ekle: `server/skills/registry_entries/*.py`
3. `bridge.py` icinde `register_*_skills(COMMAND_REGISTRY)` ile bagla
4. Regresyon testi ekle: `tests/test_*registry*.py`

Yeni cloud skill ekleme:
1. `server/skills/aws_<name>_skill.py` olustur, boto3 kullan ve hata halinde dict don
2. Gerekirse `server/cloud_command_handlers.py` icine Telegram formatter ekle
3. `server/skills/registry_entries/cloud_entries.py` ve/veya `bridge.py` endpointlerine bagla
4. Mock boto3 ile pytest ekle

## Telegram Komut Ozeti

| Komut | Islev |
|---|---|
| `/cloud-durum` | EC2/S3/maliyet ozeti |
| `/cloud-ec2-liste` | EC2 sunucu listesi |
| `/cloud-ec2-baslat <id>` | EC2 baslat |
| `/cloud-ec2-durdur <id>` | EC2 durdur |
| `/cloud-s3-liste` | S3 bucket listesi |
| `/cloud-maliyet` | Aylik cost ozeti |
| `/yardim` | Registry tabanli komut listesi |
| `/codex` | Codex gorev dispatch |
| `/codex-swarm` | Coklu Codex dispatch |
| `/codex-durum` | Codex queue/quota ozeti |
| `/codex-sonuc <job_id>` | Tek job sonucu |
| `/wiki` | Wiki sorgu/ekleme |

## Known Limitations

- `bridge.py` icindeki ana legacy `handle_command` zinciri halen duruyor; registry incremental katman olarak eklendi
- Cloud bridge testleri agir import yerine wiring/regression seviyesinde
- `/cloud` sayfasi bridge URL icin `NEXT_PUBLIC_BRIDGE_API` bekler, varsayilan `http://127.0.0.1:8081`
- Cost Explorer fallback mock veri donebilir; bu production basarisizligini gizlemek icin degil, operator yuzeyini ayakta tutmak icin
- Budget alerts local threshold dosyasi (`state/cost_alerts.json`) ile destekleniyor; AWS Budgets entegrasyonu `AWS_ACCOUNT_ID` olmadan bos donebilir

## TODO

- Cloud endpointleri icin daha derin davranis testleri
- `SkillRegistry` kapsamini legacy `handle_command` zincirinden daha fazla komuta yaymak
- `/cloud` route icin operator aksiyon toast/feedback katmani
- Budget threshold guncelleme UI'si
