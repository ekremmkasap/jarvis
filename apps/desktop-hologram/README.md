# Jarvis Desktop Hologram

Electron overlay for the local Jarvis runtime.

## Start

```bash
npm install
npm start
```

## Runtime

The overlay polls these bridge endpoints:

- `GET http://127.0.0.1:8081/api/desktop-assistant`
- `GET http://127.0.0.1:8081/api/office/presence`
- `GET http://127.0.0.1:8081/api/persona/active`

Launch together with `master_launcher.py` if you want bridge, voice, and hologram to come up in one flow.
