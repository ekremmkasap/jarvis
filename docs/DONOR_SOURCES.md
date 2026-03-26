# Donor Sources

Jarvis Mission Control artik `C:\pinokio\api\ekrem\app` kodunu calisan runtime olarak kullanmaz. Bu klasor sadece secici donor kaynaktir.

## Allowed

- `agent_prompts/*` altindaki secili markdown prompt dosyalari
- role/policy/dashboard fikirleri
- skill isimlendirme ve department patternleri

## Not Allowed

- Pinokio launcher dosyalari
- `.env`, `logs`, `data`, `memory.json` ve benzeri runtime artefact'lar
- plaintext secret iceren config veya bridge kopyalari
- eski `bridge.py` monolitlerini dogrudan tasima

## Deterministic Import Flow

Curated prompt aktarimi `config/donor_prompts.yml` ile tanimlidir.

Calistirma:

```powershell
python scripts/import_donor_prompts.py
```

Bu komut sadece izin verilen markdown prompt dosyalarini `prompts/donor/` altina kopyalar ve kaynak bilgisini basliga yazar.
