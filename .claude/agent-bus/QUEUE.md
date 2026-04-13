# Görev Kuyruğu

_Yapılacak işler buraya yazılır. Bir agent alırsa LOCKS.md'ye taşır._

## Bekleyen Görevler

| # | Görev | Hedef dosyalar | Öncelik | Kim alacak |
|---|-------|---------------|---------|-----------|
| 1 | antigravity 10 skill → server/skills/antigravity_skills.py | server/skills/antigravity_skills.py, server/bridge.py | P1 | Claude-Tab2 |
| 2 | soul.md kişilik güncellemesi | server/soul.md | P2 | Claude-Main |
| 3 | APScheduler startup wiring (bridge.py) | server/bridge.py | P2 | Claude-Main (Tab2 bridge işi bitince) |
| 4 | hologram persona renk geçişi | apps/desktop-hologram/ | P1 | Anti |
| 5 | /repos + /worktrees web UI sayfaları | apps/web-ui/src/app/ | P3 | beklemede |

## Tamamlananlar

| Görev | Kim | Commit |
|-------|-----|--------|
| research_scheduler_skill.py | Claude-Main | 3a71b94 |
| instagram_skill.py | Claude-Main | 3a71b94 |
| external_agent_skill.py | Claude-Main | 3a71b94 |
| 23 pytest passed | Claude-Main | 3a71b94 |
