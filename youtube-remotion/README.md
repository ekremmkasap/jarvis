# Jarvis YouTube Video Pipeline
Kie.ai + ElevenLabs + Remotion ile tek prompt'tan tam video.

## Kurulum
1. API key'lerini girin:
   cp .env.example .env
   # .env dosyasini ac ve key'leri gir

2. Bagimliliklari yukle:
   npm install
   cd my-video && npm install && cd ..

3. Kontrol:
   node produce-video.js --check

## Kullanim
node produce-video.js --prompt "Istanbul'un Fethi"

## Cikti
my-video/out/video.mp4
