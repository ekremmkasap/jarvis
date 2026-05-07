# Tasks: CloudManagerSystem — Jarvis Cloud Yönetim Skill'i

**Feature**: 001-cloudmanagersystem-jarvis-entegreli  
**Generated**: 2026-04-13  
**Total Tasks**: 38  
**Phases**: 8

---

## Phase 1 — Setup

- [ ] T001 Create feature branch `001-cloudmanagersystem-jarvis-entegreli` and verify Python 3.11 + boto3 available
- [ ] T002 Add `boto3`, `botocore` to `requirements.txt` if not present
- [ ] T003 Add AWS credential keys to `.env.example`: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_DEFAULT_REGION`, `CLOUD_COST_ALERT_THRESHOLD`
- [ ] T004 Create `server/data/` directory and add `.gitkeep`; add `server/data/cloud_cost_cache.json` to `.gitignore`

---

## Phase 2 — Foundational (blocking all stories)

- [ ] T005 Create `server/skills/cloud_manager_skill.py` with boto3 session factory that redacts credentials from all log output
- [ ] T006 [P] Add `get_aws_session()` helper: reads AWS_* from env, raises `CloudConfigError` if missing, never logs key values
- [ ] T007 [P] Add `_redact(payload: dict) -> dict` utility: masks keys matching `key|secret|token|password` with `***REDACTED***`
- [ ] T008 Write `tests/test_cloud_manager_skill.py` — import smoke test + redact utility unit test

---

## Phase 3 — User Story 1: EC2 Telegram Yönetimi (P1)

- [ ] T009 [P] [US1] Implement `list_ec2_instances() -> list[dict]` in `cloud_manager_skill.py` — returns id, name, state, type, region
- [ ] T010 [P] [US1] Implement `start_instance(instance_id: str) -> dict` — returns {ok, state, message}
- [ ] T011 [P] [US1] Implement `stop_instance(instance_id: str) -> dict` — returns {ok, state, message}
- [ ] T012 [US1] Implement `reboot_instance(instance_id: str) -> dict` — returns {ok, message}
- [ ] T013 [US1] Add Telegram command routing in `server/bridge.py` (backward-safe, append-only):
  - `/cloud-ec2-liste` → `list_ec2_instances()`
  - `/cloud-ec2-baslat <id>` → `start_instance(id)`
  - `/cloud-ec2-durdur <id>` → `stop_instance(id)`
  - `/cloud-ec2-yeniden-baslat <id>` → `reboot_instance(id)`
- [ ] T014 [US1] Add tests for EC2 functions in `tests/test_cloud_manager_skill.py` using `moto` or `unittest.mock` to patch boto3

---

## Phase 4 — User Story 2: Maliyet ve Fatura Uyarıları (P2)

- [ ] T015 [P] [US2] Implement `get_monthly_cost() -> dict` — calls Cost Explorer API, returns {total_usd, by_service, period}
- [ ] T016 [P] [US2] Implement `save_cost_cache(data)` / `load_cost_cache()` — reads/writes `server/data/cloud_cost_cache.json`
- [ ] T017 [US2] Implement `check_cost_alert(threshold_usd: float, send_fn: Callable) -> dict` — sends Telegram alert if cost exceeds threshold
- [ ] T018 [US2] Add APScheduler job in bridge.py `main()` startup: run `check_cost_alert` every 6 hours
- [ ] T019 [US2] Add Telegram commands:
  - `/cloud-maliyet` → `get_monthly_cost()` formatted response
  - `/cloud-esik <tutar>` → update `CLOUD_COST_ALERT_THRESHOLD` in runtime config
- [ ] T020 [US2] Add cost tests in `tests/test_cloud_manager_skill.py` — mock Cost Explorer response, verify alert logic

---

## Phase 5 — User Story 4: S3 Sorgulama (P3, no UI dep)

- [ ] T021 [P] [US4] Implement `list_s3_buckets() -> list[dict]` — returns name, region, creation_date, object_count estimate
- [ ] T022 [P] [US4] Implement `list_bucket_objects(bucket: str, max_keys=20) -> list[dict]` — returns key, size, last_modified
- [ ] T023 [US4] Implement `generate_presigned_url(bucket: str, key: str, expires=3600) -> str`
- [ ] T024 [US4] Add Telegram commands:
  - `/cloud-s3-liste` → `list_s3_buckets()`
  - `/cloud-s3-dosyalar <bucket>` → `list_bucket_objects(bucket)`
  - `/cloud-s3-url <bucket> <key>` → `generate_presigned_url()`
- [ ] T025 [US4] Add S3 tests in `tests/test_cloud_manager_skill.py`

---

## Phase 6 — User Story 3: Web UI Cloud Dashboard (P3)

- [ ] T026 [P] [US3] Create `apps/web-ui/src/app/cloud/page.tsx` — Cloud dashboard page with Suspense loading
- [ ] T027 [P] [US3] Create `apps/web-ui/src/components/CloudDashboard.tsx` — resource cards + cost summary
- [ ] T028 [P] [US3] Create `apps/web-ui/src/components/EC2InstanceCard.tsx` — shows id, name, state chip, start/stop button
- [ ] T029 [US3] Add bridge HTTP endpoints in `server/bridge.py`:
  - `GET /api/cloud/ec2` → JSON list of instances
  - `GET /api/cloud/cost` → current month cost summary
  - `GET /api/cloud/s3` → bucket list
  - `POST /api/cloud/ec2/<id>/action` → body: {action: start|stop|reboot}
- [ ] T030 [US3] Wire CloudDashboard to fetch from `http://localhost:8081/api/cloud/*` with SWR or fetch + 30s polling
- [ ] T031 [US3] Add "Cloud" nav link in web-ui layout sidebar
- [ ] T032 [US3] Add empty state: "AWS kimlik bilgileri eksik — .env dosyasına ekle" card when credentials missing
- [ ] T033 [US3] TypeScript type-check: `npx tsc --noEmit` must pass with zero errors

---

## Phase 7 — Integration & Security Gate

- [ ] T034 Verify `_redact()` is called before every boto3 exception log — grep `cloud_manager_skill.py` for bare `str(e)` in logger calls
- [ ] T035 [P] Integration smoke test: start bridge.py locally, send `/cloud-ec2-liste` via Telegram, verify response arrives in < 10s
- [ ] T036 [P] Add `/cloud-durum` command → returns {ec2_count, s3_count, last_cost_check, alert_threshold} as health summary
- [ ] T037 Add `CLOUD_COST_ALERT_THRESHOLD` to `.env.example` with comment `# USD threshold for monthly cost alert`

---

## Phase 8 — Polish

- [ ] T038 Run full test suite: `python -m pytest tests/test_cloud_manager_skill.py -v --tb=short` — all pass
- [ ] T039 Update `CLAUDE.md` CloudManagerSystem status to TAMAMLANDI
- [ ] T040 Commit: `feat: 001-cloudmanagersystem — EC2/S3/Cost + web dashboard`

---

## Dependencies

```
Phase 1 → Phase 2 → Phase 3
Phase 2 → Phase 4
Phase 2 → Phase 5
Phase 3 + Phase 4 + Phase 5 → Phase 6 (web UI needs all API endpoints)
Phase 3-6 → Phase 7 → Phase 8
```

## Parallel Execution

- T009, T010, T011 can run in parallel (different functions, same file sections)
- T021, T022 can run in parallel
- T026, T027, T028 can run in parallel (different component files)
- T034, T035, T036 can run in parallel

## Implementation Strategy

**MVP (Phase 1-3)**: EC2 list/start/stop via Telegram. No UI. One Telegram command works end-to-end.  
**Full (Phase 4-8)**: Add cost alerts, S3, web dashboard, security hardening.
