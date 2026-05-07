# Persona Key Havuzu

## Amac

Jarvis altinda calisan 7 persona, gunluk kota kapasitesini artirmak icin tek ortak Gemini key yerine kendi key havuzunu kullanabilir. Keyler repo dosyalarina yazilmaz; sadece lokal `.env` icinde tutulur.

## Env Eslesmesi

```text
GEMINI_KEY_SEDA      -> Seda
GEMINI_KEY_MERT      -> Mert
GEMINI_KEY_BUSE      -> Buse
GEMINI_KEY_EREN      -> Eren
GEMINI_KEY_LUNA      -> Luna
GEMINI_KEY_SABRICAN  -> Sabrican
GEMINI_KEY_SABRI     -> Sabri
GEMINI_API_KEY       -> global Gemini fallback / 8. Google key
GROQ_API_KEY         -> hizli fallback ve genel route
```

## Router Davranisi

- `config/model_router.yml` icinde her persona icin optional Gemini provider vardir: `gemini_seda`, `gemini_mert`, `gemini_buse`, `gemini_eren`, `gemini_luna`, `gemini_sabrican`, `gemini_sabri`.
- `config/agents.yaml` icindeki her persona `llm_profile` ile kendi provider, model, key env, fallback model ve voice modelini belirtir.
- Key eksikse provider optional kabul edilir; Jarvis boot bozmaz ve fallback zincirine duser.
- Key varsa ilgili persona once kendi quota havuzunu kullanir.

## Ses Modeli Notu

Persona profillerinde `voice_model` alanlari vardir. Clone/swarm diyalog motoru Edge TTS tarafinda bu sesleri kullanabilir. Mark-XXXV live audio oturumu ise Gemini Live tek oturum sesiyle konusur; persona cevabini bridge uzerinden alir.

## Guvenlik

- Keyler chat'e, log'a, wikiye veya git'e yazilmaz.
- `.env.example` sadece env isimlerini gosterir.
- Canli keyler sadece lokal `.env` veya operator secret store icinde kalmalidir.
