# Tasks: Jarvis Autonomous Research & Personality Agent Sistemi

**Branch**: `002-autonomous-research-agent`  
**Generated**: 2026-04-13  
**Total Tasks**: 42  
**Spec**: specs/002-autonomous-research-agent/spec.md

---

## Phase 1 — Setup

Project initialization, directory structure, dependencies.

- [X] T001 Create `state/research/` directory and initialize `state/research/watch_list.json` as empty array `[]`
- [X] T002 Create `state/research/daily_brief_history.json` as empty array `[]`
- [X] T003 Create `config/external_agents.yml` with crewai and openhands entries per data-model.md AgentFramework schema
- [X] T004 Add to `requirements.txt`: `feedparser`, `instaloader`, `apscheduler`, `beautifulsoup4` (if not already present)

---

## Phase 2 — Foundational

Blocking prerequisites shared by all user stories.

- [X] T005 Read `server/bridge.py` fully — identify existing Telegram command routing section and note the insertion point for new commands
- [X] T006 Read `server/soul.md` (or `config/soul.md`) — locate file path, read current content, note tone/format structure
- [X] T007 [P] Create `server/skills/research_scheduler_skill.py` skeleton: module docstring, imports (`feedparser`, `requests`, `json`, `pathlib`, `datetime`), `BRIEF_HISTORY_PATH` constant pointing to `state/research/daily_brief_history.json`
- [X] T008 [P] Create `server/skills/instagram_skill.py` skeleton: module docstring, imports (`instaloader`, `json`, `pathlib`, `datetime`), `WATCH_LIST_PATH` constant pointing to `state/research/watch_list.json`
- [X] T009 [P] Create `server/skills/external_agent_skill.py` skeleton: module docstring, imports (`subprocess`, `shutil`, `yaml`, `pathlib`), `AGENTS_CONFIG_PATH` constant pointing to `config/external_agents.yml`

---

## Phase 3 — User Story 1: Sabah Araştırma Briefingi (P1)

**Goal**: Her sabah 08:00'de GitHub trending + Reddit + X/Twitter özetini Telegram'a gönder.  
**Independent Test**: APScheduler 08:00 job tetiklenince Telegram'a brief mesajı gidiyor mu?

- [X] T010 [US1] Implement `fetch_github_trending(max_items=5) -> list[dict]` in `server/skills/research_scheduler_skill.py` — use `feedparser` to parse `https://github.com/trending` atom feed or `requests` to hit GitHub search API; return list of `{source, title, url, summary, fetched_at}`
- [X] T011 [US1] Implement `fetch_reddit_top(subreddits: list[str], max_items=5) -> list[dict]` in `server/skills/research_scheduler_skill.py` — use `requests` to hit `https://www.reddit.com/r/{sub}/top.json?limit=5&t=day`; return same schema; handle HTTP errors with empty list fallback
- [X] T012 [US1] Implement `fetch_twitter_nitter(query: str, max_items=5) -> list[dict]` in `server/skills/research_scheduler_skill.py` — use `feedparser` on Nitter RSS `https://nitter.poast.org/search/rss?q={query}`; return same schema; on failure return `[]` (no raise)
- [X] T013 [US1] Implement `build_brief_message(items: list[dict], soul_tone: str = "") -> str` in `server/skills/research_scheduler_skill.py` — formats Türkçe Telegram mesajı (max 3000 char), groups by source, uses soul_tone prefix if provided
- [X] T014 [US1] Implement `save_daily_brief(brief: dict) -> None` and `load_today_brief() -> dict | None` in `server/skills/research_scheduler_skill.py` — read/write `state/research/daily_brief_history.json`; keep max 30 entries; never log credentials
- [X] T015 [US1] Implement `run_morning_brief(telegram_send_fn) -> dict` in `server/skills/research_scheduler_skill.py` — orchestrates fetch_github + fetch_reddit + fetch_twitter → build_brief_message → save_daily_brief → telegram_send_fn(message); returns `{ok, items_count, send_status}`; on any exception returns `{ok: False, error: str(e)}`
- [X] T016 [US1] Add APScheduler integration in `server/skills/research_scheduler_skill.py`: `start_scheduler(telegram_send_fn, hour=8, minute=0)` using `BackgroundScheduler`; reads `BRIEF_HOUR` from env (default 8); registers `run_morning_brief` as cron job; stores scheduler instance in module-level var for reuse
- [X] T017 [US1] Add bridge.py Telegram command `/sabah-brief` — calls `run_morning_brief` immediately (on-demand trigger); returns brief message or error; BACKWARD-SAFE (append only, no existing code changed)
- [X] T018 [US1] Add bridge.py Telegram command `/arastirma-durum` — returns scheduler status (running/stopped), last brief date, next scheduled time; calls `scheduler.get_jobs()` info
- [X] T019 [US1] Write `tests/test_research_scheduler.py` — mock `feedparser.parse`, `requests.get`; test `fetch_github_trending` returns list of dicts; test `run_morning_brief` with mock send_fn; test `save_daily_brief` / `load_today_brief` roundtrip with tmp path; test empty source returns graceful fallback not exception

---

## Phase 4 — User Story 2: Instagram Hesap Takibi (P2)

**Goal**: `/instagram takip @hesap` ile takip listesine ekle; yeni içerik varsa Telegram'a bildir.  
**Independent Test**: Komut → hesap listeye eklendi mi? Mock post → bildirim üretildi mi?

- [X] T020 [P] [US2] Implement `add_watched_account(username: str) -> dict` in `server/skills/instagram_skill.py` — validate username (alfanumerik+`_.`, no @, max 30 chars); check max 50 accounts limit; append WatchedAccount to `state/research/watch_list.json`; returns `{ok, message}`
- [X] T021 [P] [US2] Implement `list_watched_accounts() -> list[dict]` in `server/skills/instagram_skill.py` — reads watch_list.json, returns active accounts list
- [X] T022 [US2] Implement `remove_watched_account(username: str) -> dict` in `server/skills/instagram_skill.py` — sets `active=false` for matching username; returns `{ok, message}`
- [X] T023 [US2] Implement `check_account_new_posts(account: dict, telegram_send_fn) -> dict` in `server/skills/instagram_skill.py` — uses `instaloader.Instaloader()` to get profile; compares latest post shortcode vs `last_post_id`; if new: calls `telegram_send_fn(notification_text)`, updates `last_post_id` and `last_checked_at` in watch_list.json; handles private/deleted profile with Turkish error, no raise
- [X] T024 [US2] Implement `run_instagram_check_cycle(telegram_send_fn) -> dict` in `server/skills/instagram_skill.py` — iterates active accounts, calls `check_account_new_posts` for each with 2s sleep between; returns `{ok, checked, notified}`
- [X] T025 [US2] Add APScheduler job in `server/skills/instagram_skill.py`: `start_instagram_scheduler(telegram_send_fn, interval_minutes=30)` — registers `run_instagram_check_cycle` as interval job every 30 min
- [X] T026 [US2] Add bridge.py Telegram commands: `/instagram takip @<hesap>` → `add_watched_account`; `/instagram listele` → `list_watched_accounts`; `/instagram cikar @<hesap>` → `remove_watched_account`; all responses Turkish, max 400 chars
- [X] T027 [US2] Write `tests/test_instagram_skill.py` — mock `instaloader.Instaloader`; test `add_watched_account` success + duplicate + invalid username + over-limit; test `check_account_new_posts` with mock new post → notification sent; test private account → Turkish error returned not raised

---

## Phase 5 — User Story 3: External Agent Framework Aktivasyonu (P3)

**Goal**: `/crewai` ve `/openhands` komutları bridge üzerinden framework'leri çalıştırsın.  
**Independent Test**: `/crewai durum` → framework kurulum durumu döner; subprocess mock → görev çalışır.

- [X] T028 [P] [US3] Implement `load_agent_configs() -> list[dict]` in `server/skills/external_agent_skill.py` — reads `config/external_agents.yml`; returns list of AgentFramework dicts
- [X] T029 [P] [US3] Implement `check_framework_installed(agent_name: str) -> dict` in `server/skills/external_agent_skill.py` — uses `shutil.which(install_check)` to detect if framework CLI is available; returns `{installed: bool, message: str}`
- [X] T030 [US3] Implement `run_agent_task(agent_name: str, task: str, timeout_seconds=60) -> dict` in `server/skills/external_agent_skill.py` — checks if installed first; if not: returns Turkish install instruction message; if yes: runs `subprocess.run(entry_command + [task], capture_output=True, timeout=timeout_seconds, text=True)`; returns `{ok, output: str[:800], error}`; never raises
- [X] T031 [US3] Implement `get_agent_status(agent_name: str) -> dict` in `server/skills/external_agent_skill.py` — returns `{name, installed, repo_path_exists, bridge_command}`
- [X] T032 [US3] Add bridge.py Telegram commands: `/crewai <görev>` → `run_agent_task("crewai", görev)`; `/crewai durum` → `get_agent_status("crewai")`; `/openhands <görev>` → `run_agent_task("openhands", görev)`; `/openhands durum` → `get_agent_status("openhands")`; Turkish responses, max 400 chars
- [X] T033 [US3] Write `tests/test_external_agent_skill.py` — mock `shutil.which`; mock `subprocess.run`; test `check_framework_installed` True and False; test `run_agent_task` when installed → success; when not installed → Turkish install message; test timeout → error returned not raised

---

## Phase 6 — User Story 4: Jarvis Kişilik Sistemi (P4)

**Goal**: soul.md'deki kişilik briefingi biçimlendirsin; "bugün ne var?" sorusuna Türkçe agenda dönsün.  
**Independent Test**: soul.md değişince brief mesajı prefix'i değişiyor mu?

- [X] T034 [US4] Update `server/soul.md` (or wherever it lives) — add sections: `## Sabah Selamlama Tonu`, `## Günlük Agenda Formatı`, `## Araştırma Brief Prefix`; fill with Ekrem'in iş ortağı persona (proaktif, Türkçe, samimi)
- [X] T035 [US4] Implement `load_soul_context() -> dict` in `server/skills/research_scheduler_skill.py` — reads soul.md, extracts `## Araştırma Brief Prefix` section content; returns `{prefix: str, tone: str}`; graceful fallback if file missing
- [X] T036 [US4] Update `build_brief_message` in `server/skills/research_scheduler_skill.py` to call `load_soul_context()` and prepend soul prefix to message
- [X] T037 [US4] Add bridge.py Telegram command `/bugun-ne-var` — loads today's brief from `daily_brief_history.json` (or triggers fresh if none); formats as agenda summary with soul tone; returns Turkish response max 400 chars

---

## Phase 7 — Integration & Startup Wiring

**Goal**: Tüm scheduler'lar bridge.py başlarken otomatik başlasın.

- [X] T038 Read `server/bridge.py` startup section — identify where to hook scheduler start calls (after server init, before main loop)
- [X] T039 Add to `server/bridge.py` startup: import and call `start_scheduler(telegram_send_fn)` from `research_scheduler_skill`; import and call `start_instagram_scheduler(telegram_send_fn)` from `instagram_skill`; guarded with `try/except` so startup failure doesn't crash bridge
- [X] T040 Verify `telegram_send_fn` abstraction — extract or confirm existing bridge.py Telegram send function signature; pass it to both schedulers

---

## Phase 8 — Polish & Validation

- [X] T041 Run full test suite: `python -m pytest tests/test_research_scheduler.py tests/test_instagram_skill.py tests/test_external_agent_skill.py -v --tb=short` — fix all failures before marking done
- [X] T042 Smoke test: `python -c "from server.skills.research_scheduler_skill import fetch_github_trending, fetch_reddit_top, build_brief_message; from server.skills.instagram_skill import add_watched_account, list_watched_accounts; from server.skills.external_agent_skill import check_framework_installed, get_agent_status; print('All imports OK')"` — must pass without error

---

## Dependencies

```
T001-T004  (setup)        → T005-T009  (foundation)
T007, T005 (skeleton+read) → T010-T019 (US1 research scheduler)
T008, T005                → T020-T027 (US2 instagram)
T009, T005                → T028-T033 (US3 external agents)
T014, T006                → T034-T037 (US4 personality)
T017, T018, T026, T032, T037 → T038-T040 (startup wiring)
T010-T040                 → T041-T042 (validation)
```

**Parallel opportunities**:
- T007, T008, T009 can run in parallel (different files, no dependencies)
- T010, T011, T012 can run in parallel (different fetch functions, same file non-conflicting)
- T020, T021 can run in parallel (different functions, same file)
- T028, T029 can run in parallel (different functions, same file)
- US2 (T020-T027) and US3 (T028-T033) can run fully in parallel after T005

---

## Implementation Strategy

**MVP Scope (US1 only)**:
Tasks T001-T004, T005, T007, T010-T019, T041 → delivers daily morning brief to Telegram.

**Full delivery order**: US1 → US2 → US3 → US4 → Wiring → Validation

**Rule**: Never claim a slice done without passing its pytest tasks.
