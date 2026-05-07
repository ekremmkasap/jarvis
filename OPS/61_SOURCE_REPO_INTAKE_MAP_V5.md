# OPS/61_SOURCE_REPO_INTAKE_MAP_V5

Tarih: 2026-04-04

## Intake Rules
- Repo var diye merge-ready sayilmaz.
- Pattern harvest, narrow donor extraction ve explicit gating kullan.
- Eksik repo veya eksik docs varsa “missing” denir, icerik uydurulmaz.

| Path | Classification | Confidence | Notes |
| --- | --- | --- | --- |
| `external-repos/Mark-XXXV` | feature donor | orta | Voice continuity, mute state, keyboard input, persistent memory, PC-control direction; direct merge degil. |
| `external-repos/ClawRouter` | architecture donor | orta | Agent-native routing and OpenClaw plugin orientation; future model/payment architecture donor. |
| `external-repos/OpenHands` | architecture donor | orta | CLI/local GUI/cloud/enterprise ayrimi SaaS ascent icin guclu referans. |
| `external-repos/youtube-mcp-server` | runtime candidate | orta | YouTube intelligence lane icin pratik MCP surface. |
| `external-repos/mcp-server-youtube-transcript` | runtime candidate | orta | Transcript extraction icin lightweight candidate. |
| `external-repos/awesome-codex-subagents` | prompt donor | yuksek | Local `.codex/agents/` ve delegation prompt patternleri icin donor. |
| `external-repos/awesome-agent-skills` | prompt donor | dusuk | Skill catalog donor. |
| `external-repos/claude-skills` | prompt donor | dusuk | Prompt donor; runtime integration proof yok. |
| `external-repos/aider` | feature donor | dusuk | Self-coding workflow donor. |
| `external-repos/devika` | architecture donor | dusuk | Autonomous coding UX reference. |
| `external-repos/crewAI` | architecture donor | dusuk | Multi-agent pattern donor. |
| `external-repos/swarms` | architecture donor | dusuk | Agent topology donor. |
| `external-repos/CLI-Anything` | feature donor | dusuk | CLI automation ideas; guvenlik gate gerekir. |
| `external-repos/cline` | reference only | dusuk | Adjacent coding-agent reference. |

## Missing / Unverified Intake
- “520k-line downloaded repo” icin tekil yerel proof bu sprintte bulunmadi; claim `UNVERIFIED` tutuldu.
- Microsoft voice assistant inspiration lane icin dedike local donor bulunmadi; status `desired but unavailable`.

## Directional Notes
- `Mark-XXXV` voice interruption, mute, state indicator ve PC-mode gating icin en degerli donor.
- `OpenHands` runtime bugfix donor degil; architecture and SaaS donor.
- YouTube MCP reposlari daily intelligence lane icin en uygulanabilir intake baslangici.

