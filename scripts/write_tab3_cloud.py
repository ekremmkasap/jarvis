"""Masaustune CODEX_TAB3 CloudManager + SkillRegistry promptu yazar."""
import pathlib

DESKTOP = pathlib.Path(r"C:\Users\sergen\Desktop")

CONTENT = """================================================================================
CODEX TAB-3 (3. Codex Sekmesi) — CLOUDMANAGERSYSTEM + SKILL REGISTRY
FINAL HARDCORE EXECUTION PROMPT
Repo: C:\\Users\\sergen\\Desktop\\jarvis-mission-control
Mode: PLAN-FIRST -> AUTO-EXECUTE -> VALIDATE -> CLAUDE.MD UPDATE
================================================================================

YOU ARE: Elite AI Software Engineer + Cloud Architect + Implementer
LANGUAGE: Turkish for user output, English for code/paths/configs
REPO: C:\\Users\\sergen\\Desktop\\jarvis-mission-control

================================================================================
ABSOLUTE RULES
================================================================================

1.  PLAN FIRST: read spec files before writing any code
2.  EXECUTE AUTONOMOUSLY: implement without asking user for decisions
3.  VALIDATE: pytest after every slice before moving on
4.  CLAUDE.MD UPDATE: after every slice, update CLAUDE.md, commit separately
5.  NEVER expose AWS_ACCESS_KEY_ID or any credential in logs or stdout
6.  NEVER make real AWS API calls in unit tests (always mock boto3)
7.  NEVER break existing bridge.py endpoints (backward-safe migration only)
8.  NEVER push to main/master
9.  NEVER claim success without passing tests
10. COMMIT after every slice

================================================================================
CLAUDE.MD UPDATE RULE (NON-NEGOTIABLE)
================================================================================

After every slice:
  1. Read CLAUDE.md
  2. Find or create: ### CloudManagerSystem + Skill Registry (Tab-3 Codex)
  3. Update with: status, completed, remaining, next step
  4. Commit: "chore: update CLAUDE.md — cloudmanager slice N progress"

================================================================================
MANDATORY SPEC FILES (READ BEFORE ANY CODE)
================================================================================

  specs/001-cloudmanagersystem-jarvis-entegreli/spec.md     FULL SPEC
  specs/001-cloudmanagersystem-jarvis-entegreli/plan.md     IMPLEMENTATION PLAN
  server/bridge.py                                          existing command router
  server/skills/                                            existing skills
  config/model_router.yml                                   model routing config
  .env                                                      AWS keys (NEVER log)
  apps/web-ui/src/                                          existing web UI

If spec.md or plan.md do not exist: create them first with the content below,
then proceed with implementation.

SPEC FALLBACK (use this if spec.md missing):
  Goal: AWS cloud management via Jarvis — EC2, S3, cost tracking
  Scope: list/start/stop EC2, list/browse S3, monthly cost report
  Telegram commands: /cloud-ec2-liste /cloud-ec2-baslat /cloud-s3-liste /cloud-maliyet /cloud-durum
  Web UI: /cloud page with live panels
  Skills: server/skills/aws_ec2_skill.py, aws_s3_skill.py, aws_cost_skill.py
  Auth: AWS credentials from .env (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION)
  Tests: all with mocked boto3, no real API calls

================================================================================
PART A: CLOUDMANAGERSYSTEM (SLICES A1-A6)
================================================================================

---  SLICE A1: server/skills/aws_ec2_skill.py  ---

  Implement these functions:
    list_instances() -> list[dict]
      Returns: [{id, name, state, type, region, public_ip, launch_time}]

    start_instance(instance_id: str) -> dict
      Returns: {ok: bool, message: str}

    stop_instance(instance_id: str) -> dict
      Returns: {ok: bool, message: str}

    get_instance_status(instance_id: str) -> dict
      Returns: {state, uptime_hours, type, region}

  Rules:
    - Use boto3
    - Credentials: os.getenv("AWS_ACCESS_KEY_ID") etc — NEVER hardcode
    - On any exception: return {"ok": False, "error": str(e)} — never raise to caller
    - Never log credential values

  Add: tests/test_aws_ec2_skill.py
    - Mock boto3 with unittest.mock
    - Test: list returns expected format
    - Test: start/stop returns ok dict
    - Test: exception returns error dict
    - No real AWS calls

  Commit: "feat: aws_ec2_skill — list/start/stop instances"
  CLAUDE.md update.

---  SLICE A2: server/skills/aws_s3_skill.py  ---

  Implement:
    list_buckets() -> list[dict]
      Returns: [{name, region, creation_date}]

    list_objects(bucket: str, prefix: str = "") -> list[dict]
      Returns: [{key, size_bytes, last_modified}] — max 100 objects

    get_bucket_size(bucket: str) -> dict
      Returns: {total_size_bytes, object_count}

    upload_file(bucket: str, key: str, local_path: str) -> dict
      Returns: {ok, url}

    delete_object(bucket: str, key: str) -> dict
      Returns: {ok, message}

  Same rules as A1. Mock boto3 in tests.
  Add: tests/test_aws_s3_skill.py
  Commit: "feat: aws_s3_skill — bucket and object management"
  CLAUDE.md update.

---  SLICE A3: server/skills/aws_cost_skill.py  ---

  Implement:
    get_monthly_cost() -> dict
      Returns: {total_usd, by_service: {service: usd}, period, currency: "USD"}
      Uses boto3 CostExplorer
      If CostExplorer not available: return mock data with {"mock": True}

    get_cost_trend(months: int = 3) -> list[dict]
      Returns: [{month, total_usd}]

    get_budget_alerts() -> list[dict]
      Returns: [{name, limit_usd, current_usd, pct_used}]

    save_alert_threshold(service: str, usd_limit: float) -> dict
      Saves to state/cost_alerts.json
      Returns: {ok, saved}

  Add: tests/test_aws_cost_skill.py (mock CostExplorer)
  Commit: "feat: aws_cost_skill — monthly cost + budget alerts"
  CLAUDE.md update.

---  SLICE A4: server/bridge.py — /cloud-* Telegram commands  ---

  Find the Telegram command handler section in bridge.py.
  Add these commands (backward-safe, skip if already exists):

    /cloud-durum
      -> list_instances() + list_buckets() + get_monthly_cost()
      -> Turkish summary: "EC2: N aktif / S3: N bucket / Maliyet: $X"

    /cloud-ec2-liste
      -> list_instances()
      -> Turkish: "EC2 Sunucular:\n- i-xxx (calisiyor) t3.micro us-east-1"

    /cloud-ec2-baslat <instance_id>
      -> start_instance(instance_id)
      -> Turkish: "Sunucu baslatildi: i-xxx" or error

    /cloud-ec2-durdur <instance_id>
      -> stop_instance(instance_id)
      -> Turkish: "Sunucu durduruldu: i-xxx" or error

    /cloud-s3-liste
      -> list_buckets()
      -> Turkish: "S3 Bucket'lar:\n- my-bucket (us-east-1)"

    /cloud-maliyet
      -> get_monthly_cost()
      -> Turkish: "Bu ay: $X.XX\nEC2: $Y / S3: $Z"

  All responses: max 400 chars, truncate with ... if longer
  Do NOT remove or change existing bridge.py commands
  Commit: "feat: /cloud-* Telegram commands in bridge.py"
  CLAUDE.md update.

---  SLICE A5: apps/web-ui/src/app/cloud/page.tsx  ---

  Add new page at /cloud route.
  Live polling every 10 seconds to new bridge endpoints.

  Add bridge endpoints first (GET only, backward-safe):
    GET /api/cloud/ec2
      -> aws_ec2_skill.list_instances()
    GET /api/cloud/s3
      -> aws_s3_skill.list_buckets()
    GET /api/cloud/cost
      -> aws_cost_skill.get_monthly_cost()
    POST /api/cloud/ec2/action
      -> Body: {instance_id, action: "start"|"stop"}
      -> Calls start_instance or stop_instance

  UI panels (use existing Tailwind classes, no new npm packages):

    EC2 PANEL:
      - Instance table: ID, Name, State (green=running/red=stopped), Type, Region, IP
      - Per-row buttons: [Start] [Stop] (calls /api/cloud/ec2/action)
      - Refresh indicator

    S3 PANEL:
      - Bucket list: name, region, creation date
      - No destructive actions in UI

    COST PANEL:
      - Monthly total in USD
      - USD to TRY conversion (static rate: 1 USD = 38 TRY, show note it is approximate)
      - Top services list: service name + cost

    ALERTS PANEL:
      - If budget alerts exist: show name, limit, current, pct bar
      - If no alerts: "Butce uyarisi yok" message

  TypeScript types must match API response format exactly.
  Commit: "feat: /cloud dashboard UI — EC2, S3, cost panels"
  CLAUDE.md update.

---  SLICE A6: Part A integration test  ---

  Run:
    python -m pytest tests/test_aws_ec2_skill.py tests/test_aws_s3_skill.py
      tests/test_aws_cost_skill.py -v --tb=short

  Smoke test:
    python -c "
    import sys; sys.path.insert(0, 'server/skills')
    from aws_ec2_skill import list_instances, start_instance, stop_instance
    from aws_s3_skill import list_buckets, list_objects
    from aws_cost_skill import get_monthly_cost
    print('All cloud skill imports: OK')
    print('ALL PART A SMOKE TESTS PASSED')
    "

  Fix all failures before Part B.
  CLAUDE.md update: Part A TAMAMLANDI
  Commit: "feat: CloudManagerSystem complete — EC2, S3, cost, Telegram, cloud UI"

================================================================================
PART B: SKILL REGISTRY REFACTOR
================================================================================

Goal: replace the large if/elif command routing chain in bridge.py with a
clean SkillRegistry. This is the highest code-quality ROI change in the repo.

Read bridge.py Telegram command section fully before starting.
Count the number of elif branches. Write that count in a comment.

---  SLICE B1: server/skill_registry.py  ---

  Implement:

    from dataclasses import dataclass, field
    from typing import Callable, Optional

    @dataclass
    class SkillEntry:
        command: str           # exact command e.g. "/cloud-durum"
        handler: Callable      # async or sync function(args: str, context: dict) -> str
        description: str       # Turkish one-line description
        aliases: list = field(default_factory=list)
        requires_args: bool = False
        min_args: int = 0
        category: str = "general"

    class SkillRegistry:
        def __init__(self):
            self._registry: dict[str, SkillEntry] = {}

        def register(self, entry: SkillEntry):
            self._registry[entry.command] = entry
            for alias in entry.aliases:
                self._registry[alias] = entry

        def dispatch(self, command: str, args: str = "", context: dict = None) -> str:
            entry = self._registry.get(command)
            if not entry:
                return f"Bilinmeyen komut: {command}"
            try:
                import asyncio, inspect
                if inspect.iscoroutinefunction(entry.handler):
                    result = asyncio.run(entry.handler(args, context or {}))
                else:
                    result = entry.handler(args, context or {})
                return str(result)[:400]
            except Exception as e:
                return f"Hata ({command}): {e}"

        def list_commands(self, category: str = None) -> list:
            seen = set()
            result = []
            for cmd, entry in self._registry.items():
                if entry.command not in seen:
                    if category is None or entry.category == category:
                        result.append(entry)
                        seen.add(entry.command)
            return result

        def get_help(self, command: str) -> str:
            entry = self._registry.get(command)
            if not entry:
                return f"{command}: bilinmiyor"
            return f"{entry.command}: {entry.description}"

  Add: tests/test_skill_registry.py
    - Test: register + dispatch works
    - Test: unknown command returns Turkish error
    - Test: alias routing works
    - Test: exception returns Turkish error string
    - Test: list_commands category filter

  Commit: "feat: SkillRegistry base class in server/skill_registry.py"
  CLAUDE.md update.

---  SLICE B2: Migrate cloud commands to registry  ---

  Create: server/skills/registry_entries/cloud_entries.py

    from server.skill_registry import SkillRegistry, SkillEntry
    from server.skills.aws_ec2_skill import list_instances, start_instance, stop_instance
    from server.skills.aws_s3_skill import list_buckets
    from server.skills.aws_cost_skill import get_monthly_cost

    def register_cloud_skills(registry: SkillRegistry):
        registry.register(SkillEntry(
            command="/cloud-durum",
            handler=lambda args, ctx: ...,
            description="Tum cloud servislerinin ozet durumu",
            category="cloud"
        ))
        # ... all /cloud-* commands

  In bridge.py:
    - Import and call register_cloud_skills(registry) at startup
    - Remove the /cloud-* elif branches (they now live in registry)
    - bridge.py calls registry.dispatch(command, args) for /cloud-* prefix

  Test: all cloud Telegram commands still work
  Commit: "refactor: migrate /cloud-* commands to SkillRegistry"
  CLAUDE.md update.

---  SLICE B3: /yardim command  ---

  Add /yardim (help) command via registry:
    -> registry.list_commands()
    -> group by category
    -> return formatted Turkish list

  Example output:
    Komutlar:
    [cloud] /cloud-durum, /cloud-ec2-liste, /cloud-maliyet
    [sistem] /durum, /saglik
    [notion] /not-ekle, /not-ara
    ...max 400 chars

  Add to registry_entries and register in bridge.py.
  Test: /yardim returns a non-empty Turkish command list
  Commit: "feat: /yardim help command via SkillRegistry"
  CLAUDE.md update.

---  SLICE B4: Migrate 5 more high-traffic commands  ---

  Read bridge.py and find the 5 most commonly referenced commands
  (check README.md, CLAUDE.md, or comment frequency in bridge.py as signal).

  Migrate those 5 to registry entries.
  Behavior must be IDENTICAL — this is refactor only.
  Add regression test for each migrated command.

  Commit: "refactor: migrate 5 more commands to SkillRegistry"
  CLAUDE.md update.

---  SLICE B5: Part B integration test  ---

  Run:
    python -m pytest tests/test_skill_registry.py -v --tb=short

  Smoke test:
    python -c "
    import sys; sys.path.insert(0, 'server')
    from skill_registry import SkillRegistry, SkillEntry
    r = SkillRegistry()
    r.register(SkillEntry('/test', lambda a,c: 'ok', 'test komutu', category='test'))
    result = r.dispatch('/test')
    assert result == 'ok', f'FAIL: {result}'
    cmds = r.list_commands()
    assert len(cmds) == 1
    print('SkillRegistry smoke test: PASSED')
    "

  CLAUDE.md update: Part B TAMAMLANDI
  Commit: "feat: SkillRegistry foundation + cloud migration + /yardim"

================================================================================
FINAL: Integration + Handoff
================================================================================

Run full combined test suite:
  python -m pytest tests/test_aws_ec2_skill.py tests/test_aws_s3_skill.py
    tests/test_aws_cost_skill.py tests/test_skill_registry.py -v --tb=short

Write OPS/408_CLOUDMANAGER_HANDOFF.md:
  - Part A: what works, what needs real AWS credentials
  - Part B: SkillRegistry — how many commands migrated, how to add a new skill
  - How to add a new cloud skill (4-step guide)
  - Telegram commands summary table
  - Known limitations and TODOs

Final CLAUDE.md update:
  ### CloudManagerSystem + Skill Registry (Tab-3 Codex)
  - Durum: TAMAMLANDI
  - EC2/S3/Cost: server/skills/aws_*.py
  - Cloud UI: /cloud page
  - Telegram: /cloud-durum /cloud-ec2-liste /cloud-maliyet /yardim
  - Registry: server/skill_registry.py — N commands migrated
  - Tests: pytest N passed
  - Handoff: OPS/408_CLOUDMANAGER_HANDOFF.md

Final commit: "feat: CloudManagerSystem + SkillRegistry foundation complete"

================================================================================
ANTI-HALLUCINATION RULES
================================================================================

- Do NOT log or print AWS_ACCESS_KEY_ID or any credential
- Do NOT call real AWS in tests — always use unittest.mock.patch("boto3.client")
- Do NOT break existing bridge.py commands during registry migration
- Do NOT migrate all commands at once — migrate incrementally
- Do NOT add packages not in requirements.txt (boto3 should already be present)
- Do NOT claim success without passing pytest

================================================================================
GO. READ SPEC. PLAN. EXECUTE. TEST. COMMIT. UPDATE CLAUDE.MD. HANDOFF.
================================================================================
"""

out = DESKTOP / "CODEX_TAB3_CLOUDMANAGER_SKILLREGISTRY.txt"
out.write_text(CONTENT, encoding="utf-8")
print(f"Written: {out}")
print(f"Lines: {len(CONTENT.splitlines())}")
