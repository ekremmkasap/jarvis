# Claude Code Kaynak Kodu — Quickstart

Bu kaynak Bun ile derlenir.

## Gereksinimler

- [Bun](https://bun.sh) >= 1.1.0
- Node.js >= 18 (isteğe bağlı, Bun tek başına yeterli)

## Adımlar

```bash
# 1. claude-code-main dizinine gir
cd claude-code-main

# 2. Bağımlılıkları yükle
bun install

# 3. Kaynak kodu çalıştır
bun run src/main.tsx
```

## Alternatif: Sadece tip kontrolü

```bash
bun x tsc --noEmit
```

## Önemli Notlar

- `bun:bundle` modülü standart Node.js'de bulunmaz; yalnızca Bun runtime ile çalışır.
- `@ant/*` ve `@anthropic-ai/mcpb` gibi dahili Anthropic paketleri npm'de herkese açık değildir; bu importlar derleme hatası verebilir — `tsconfig.json`'da `skipLibCheck: true` ile tip hataları bastırılır.
- `feature('FLAG_NAME')` çağrıları Bun'ın dead-code elimination mekanizmasına dayanır; ortam değişkenleri ile kontrol edilir.
- Gerçek `ANTHROPIC_API_KEY` olmadan API çağrıları başarısız olur.

## Dizin Yapısı

```
claude-code-main/
├── src/
│   ├── main.tsx          # CLI giriş noktası
│   ├── commands.ts       # Komut tanımları
│   └── ...               # Diğer modüller
├── package.json          # Bun bağımlılıkları
└── tsconfig.json         # TypeScript konfigürasyonu
```
