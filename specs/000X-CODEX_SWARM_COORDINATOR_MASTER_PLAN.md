# 🚀 CODEX SWARM COORDINATOR — MASTER PLAN

**Tarih**: 2026-04-15  
**Durum**: Planning Phase  
**Hedef**: 5 Codex hesabını orchestrate eden Jarvis CEO agent mimarisi  
**Tahmini Süre**: 40-50 saat (4-5 gün Codex parallel)  
**Zorluk**: Yüksek (multi-agent coordination + state sync)

---

## 1️⃣ CURRENT STATE (Ne var?)

### ✅ Mevcut Altyapı
- `CanonicalAgent` base class (async-ready)
- 7 personas (Seda/Mert/Buse/Eren/Sabri/Luna/Sabrican)
- 5 Codex slots (forge/spark/nexus/atlas/shield)
- bridge.py (HTTP command router)
- agents.yaml (config + definitions)

### ❌ Eksik Bileşenler
- Slot coordinator agents (5 tane)
- Master coordinator (Jarvis CEO)
- Task distribution logic
- Parallel execution engine
- State synchronization
- Progress tracking + reporting
- Error recovery + retry logic

---

## 2️⃣ ARCHITECTURE (Nasıl olacak?)

### Katmanlı Tasarım

```
┌─────────────────────────────────────────────────────────┐
│    LAYER 1: USER INTERFACE                              │
│  /swarm "build AI Instagram account in 2 days"          │
│  /swarm-status                                          │
│  /swarm-report                                          │
└────────────────┬────────────────────────────────────────┘
                 │ (Telegram/HTTP)
┌────────────────▼────────────────────────────────────────┐
│    LAYER 2: MASTER COORDINATOR (Jarvis CEO)             │
│  - Goal decomposition                                   │
│  - Task prioritization                                  │
│  - Conflict resolution                                  │
│  - Global state tracking                                │
│  - Reporting + notifications                            │
└────────────────┬────────────────────────────────────────┘
                 │
   ┌─────────────┼─────────────┬─────────────┬──────────┐
   ▼             ▼             ▼             ▼          ▼
┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐  ┌────────┐
│FORGE   │  │SPARK   │  │NEXUS   │  │ATLAS   │  │SHIELD  │
│Slot    │  │Slot    │  │Slot    │  │Slot    │  │Slot    │
├────────┤  ├────────┤  ├────────┤  ├────────┤  ├────────┤
│Seda    │  │Buse    │  │Sabrican│  │Sabri   │  │Luna    │
│(code)  │  │(content)│ │(ops)   │  │(CEO)   │  │(sec)   │
│        │  │        │  │        │  │        │  │        │
│Mert    │  │Eren    │  │        │  │        │  │        │
│(data)  │  │(data)  │  │        │  │        │  │        │
└────────┘  └────────┘  └────────┘  └────────┘  └────────┘
    │           │           │           │          │
    └───────────┴───────────┴───────────┴──────────┘
                         │
                         ▼
         ┌──────────────────────────────┐
         │  LAYER 3: SHARED STATE       │
         │  - Redis/SQLite tasks queue  │
         │  - Persona memory storage    │
         │  - Execution logs            │
         │  - Metrics + statistics      │
         └──────────────────────────────┘
```

---

## 3️⃣ COMPONENTS (Ne yapıcağız?)

### Component 1: SlotCoordinator (Base Class)
**Dosya**: `server/agents/canonical/slot_coordinator.py`  
**Amaç**: Slot-level orchestration (Forge/Spark/Nexus/Atlas/Shield)

```python
class SlotCoordinator(CanonicalAgent):
    """
    Coordinator for a single Codex slot.
    
    Responsibilities:
    - Assign personas within slot
    - Route incoming tasks to right persona
    - Manage task queue + priorities
    - Track execution state
    - Report status back to master
    """
    
    async def execute_task(self, task):
        """Main execution loop"""
        
    async def assign_to_persona(self, persona_id, task):
        """Route task to specific persona"""
        
    async def get_slot_status(self):
        """Return current workload + progress"""
```

**Responsibilities**:
- [ ] Task queue management (FIFO + priority)
- [ ] Persona assignment logic
- [ ] Error handling + retry
- [ ] State persistence
- [ ] Status reporting to master

---

### Component 2: Slot Implementations (5 tane)

#### 2a. ForgeSlot — Code/PR/Review
**Dosya**: `server/agents/canonical/forge_slot.py`

```python
class ForgeSlot(SlotCoordinator):
    """Code generation & PR review"""
    
    personas = ["Seda", "Mert"]  # Seda=code, Mert=research
    
    domain = "engineering"
    tasks = [
        "write_code",
        "fix_bugs", 
        "review_pr",
        "refactor",
        "optimize"
    ]
```

**Task Types**:
- `write_code@seda` → Python feature implementation
- `review_pr@seda` → Code review + suggestions
- `research@mert` → GitHub trending, tech research

---

#### 2b. SparkSlot — Content/Marketing/Social
**Dosya**: `server/agents/canonical/spark_slot.py`

```python
class SparkSlot(SlotCoordinator):
    """Content creation & marketing"""
    
    personas = ["Buse", "Eren"]  # Buse=content, Eren=data
    
    domain = "marketing"
    tasks = [
        "generate_post",
        "create_reel",
        "analyze_engagement",
        "generate_captions",
        "research_trends"
    ]
```

**Task Types**:
- `generate_post@buse` → Instagram post copy
- `create_reel@eren` → Video analysis + recommendations
- `analyze_trends@eren` → Instagram/YouTube trending analysis

---

#### 2c. NexusSlot — Operations/Automation
**Dosya**: `server/agents/canonical/nexus_slot.py`

```python
class NexusSlot(SlotCoordinator):
    """Operations & automation"""
    
    personas = ["Sabrican"]
    
    domain = "ops"
    tasks = [
        "manage_aws",
        "setup_cron",
        "monitor_health",
        "scale_infra",
        "deploy_service"
    ]
```

**Task Types**:
- `manage_aws@sabrican` → EC2/S3 management
- `setup_automation@sabrican` → Cron jobs + scheduled tasks
- `monitor@sabrican` → System health tracking

---

#### 2d. AtlasSlot — Strategy/Business/CEO
**Dosya**: `server/agents/canonical/atlas_slot.py`

```python
class AtlasSlot(SlotCoordinator):
    """Business strategy & CEO decisions"""
    
    personas = ["Sabri"]
    
    domain = "strategy"
    tasks = [
        "create_strategy",
        "plan_quarter",
        "analyze_market",
        "create_pitch",
        "forecast_revenue"
    ]
```

**Task Types**:
- `generate_strategy@sabri` → Market analysis + positioning
- `create_proposal@sabri` → Ad agency proposal generation
- `forecast@sabri` → Growth projections

---

#### 2e. ShieldSlot — Security/Compliance
**Dosya**: `server/agents/canonical/shield_slot.py`

```python
class ShieldSlot(SlotCoordinator):
    """Security & compliance"""
    
    personas = ["Luna"]
    
    domain = "security"
    tasks = [
        "audit_code",
        "check_compliance",
        "security_review",
        "threat_model",
        "encrypt_secret"
    ]
```

**Task Types**:
- `audit@luna` → Code security review
- `compliance@luna` → Data protection check
- `threat_model@luna` → Security risk assessment

---

### Component 3: Master Coordinator (Jarvis CEO)
**Dosya**: `server/agents/canonical/coordinator.py`

```python
class MasterCoordinator(CanonicalAgent):
    """
    Central orchestration engine.
    
    Responsibilities:
    - Accept high-level goals
    - Decompose into tasks
    - Distribute to 5 slots
    - Monitor progress
    - Handle conflicts
    - Generate reports
    """
    
    name = "Jarvis CEO"
    slots = {
        "forge": ForgeSlot(),
        "spark": SparkSlot(),
        "nexus": NexusSlot(),
        "atlas": AtlasSlot(),
        "shield": ShieldSlot()
    }
    
    async def execute_goal(self, goal: str):
        """
        1. Decompose goal into tasks
        2. Categorize by domain
        3. Assign to slots
        4. Monitor execution
        5. Aggregate results
        """
```

**Key Algorithms**:

#### 3a. Goal Decomposition
```python
async def decompose_goal(self, goal: str) -> List[Task]:
    """
    /swarm "Build Instagram account + lead capture in 48 hours"
    
    Decomposed into:
    [
        Task("research_competitors", domain="marketing", slot="spark"),
        Task("design_api", domain="engineering", slot="forge"),
        Task("create_content_calendar", domain="marketing", slot="spark"),
        Task("audit_security", domain="security", slot="shield"),
        Task("deploy_service", domain="ops", slot="nexus"),
        Task("analyze_metrics", domain="strategy", slot="atlas")
    ]
    """
```

#### 3b. Smart Routing
```python
async def route_task_to_slot(self, task: Task) -> str:
    """
    Route based on:
    - Domain (marketing → spark, code → forge, etc.)
    - Slot availability (concurrent tasks)
    - Persona expertise
    - Priority level
    
    Returns: slot_name (forge/spark/nexus/atlas/shield)
    """
```

#### 3c. Conflict Resolution
```python
async def resolve_conflict(self, 
                          task1: Task, 
                          task2: Task) -> Task:
    """
    If two tasks conflict (both need same resource):
    - Prioritize by importance
    - Schedule sequentially
    - Add dependency link
    - Notify slots
    """
```

#### 3d. Progress Tracking
```python
async def get_overall_status(self) -> Dict:
    """
    Return aggregated status:
    {
        "goal": "Build Instagram...",
        "progress": 45,  # percent
        "active_slots": 3,
        "completed_tasks": 12,
        "pending_tasks": 8,
        "eta_hours": 24,
        "slots": {
            "forge": {"progress": 60, "current_task": "..."},
            "spark": {"progress": 30, "current_task": "..."},
            ...
        }
    }
    """
```

---

## 4️⃣ DATA MODELS

### TaskRequest
```python
@dataclass
class TaskRequest:
    goal: str  # "Build Instagram account"
    description: str
    priority: int  # 1-10
    deadline: Optional[datetime]
    required_slots: List[str]  # ["spark", "forge"] veya [] (auto-detect)
    metadata: Dict  # Custom data
```

### Task (Internal)
```python
@dataclass
class Task:
    task_id: str  # UUID
    goal_id: str  # Parent goal
    description: str
    domain: str  # "marketing", "engineering", "ops", etc.
    assigned_slot: str  # "forge", "spark", etc.
    assigned_persona: str  # "Seda", "Buse", etc.
    status: str  # "pending", "running", "completed", "failed"
    priority: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    error: Optional[str]
    result: Optional[str]
    metrics: Dict  # execution time, token usage, etc.
```

### SlotStatus
```python
@dataclass
class SlotStatus:
    slot_name: str
    personas: List[str]
    active_tasks: int
    queued_tasks: int
    completed_tasks_today: int
    error_count: int
    last_activity: datetime
    utilization: float  # 0-1
    estimated_free_time: timedelta
```

---

## 5️⃣ FLOW EXAMPLES

### Örnek 1: Instagram Account Buildout

```
Ekrem: /swarm "Build AI Instagram account in 48 hours with lead capture"

Master Coordinator decomposes:
├─ Task 1: Research competitors (spark/Buse)
├─ Task 2: Create content calendar (spark/Eren)
├─ Task 3: Design lead capture API (forge/Seda)
├─ Task 4: Generate 30 posts (spark/Buse)
├─ Task 5: Security audit (shield/Luna)
├─ Task 6: Deploy service (nexus/Sabrican)
├─ Task 7: Setup automation (nexus/Sabrican)
├─ Task 8: Create strategy doc (atlas/Sabri)
└─ Task 9: Monitor metrics (atlas/Sabri)

Distribution:
┌─────────────────────────────────────────────┐
│ Spark: Research + content (Buse/Eren)       │
│ Forge: API design + review (Seda/Mert)      │
│ Shield: Security audit (Luna)                │
│ Nexus: Deploy + automation (Sabrican)       │
│ Atlas: Strategy + monitoring (Sabri)        │
└─────────────────────────────────────────────┘

Execution (Parallel):
- T+0h: All slots start
- T+6h: Content ready, Buse → Eren handoff
- T+12h: API coded (Seda), security audit (Luna)
- T+18h: Deployment ready, Sabrican → deploy
- T+24h: Launch, Sabri monitors metrics
- T+48h: Complete, report to Ekrem
```

### Örnek 2: Bug Fix + Documentation

```
Ekrem: /swarm "Fix null pointer in auth + document API"

Master decomposes:
├─ Task 1: Find bug root cause (forge/Mert)
├─ Task 2: Write fix (forge/Seda)
├─ Task 3: Review fix (forge/Seda)
├─ Task 4: Run tests (forge/Seda)
├─ Task 5: Document API (forge/Mert)
├─ Task 6: Security check (shield/Luna)
└─ Task 7: Deploy fix (nexus/Sabrican)

Timeline: 2 hours (sequential + parallel)
```

---

## 6️⃣ IMPLEMENTATION ROADMAP

### Phase 1: Base Infrastructure (6 saat)
- [ ] Create SlotCoordinator base class
- [ ] Implement task queue (asyncio.Queue)
- [ ] Setup state persistence (SQLite)
- [ ] Create Task + SlotStatus dataclasses

**Deliverable**: `server/agents/canonical/slot_coordinator.py`

---

### Phase 2: Slot Implementations (10 saat)
- [ ] ForgeSlot (code domain)
- [ ] SparkSlot (marketing domain)
- [ ] NexusSlot (ops domain)  
- [ ] AtlasSlot (strategy domain)
- [ ] ShieldSlot (security domain)

**Deliverable**: 5 slot coordinator files

---

### Phase 3: Master Coordinator (12 saat)
- [ ] Goal decomposition algorithm
- [ ] Smart routing logic
- [ ] State synchronization
- [ ] Progress tracking
- [ ] Conflict resolution
- [ ] Reporting engine

**Deliverable**: `server/agents/canonical/coordinator.py` (200+ lines)

---

### Phase 4: Bridge Integration (6 saat)
- [ ] `/swarm` command (goal submission)
- [ ] `/swarm-status` command (progress tracking)
- [ ] `/swarm-report` command (final report)
- [ ] Error handling + notifications

**Deliverable**: bridge.py modifications

---

### Phase 5: Testing + Refinement (8 saat)
- [ ] Unit tests (coordinator logic)
- [ ] Integration tests (end-to-end flow)
- [ ] Load tests (5+ concurrent goals)
- [ ] Error recovery tests

**Deliverable**: `tests/test_coordinator.py`

---

## 7️⃣ BRIDGE COMMANDS

### Command 1: Submit Swarm Goal
```
/swarm "Build Instagram account with lead capture system in 48 hours"

Response:
✅ Goal submitted!

Goal ID: GOAL_20260415_001
Estimated Duration: 48 hours
Required Slots: spark, forge, nexus, shield, atlas
Status: DECOMPOSING_GOAL...

Track progress: /swarm-status GOAL_20260415_001
```

### Command 2: Check Status
```
/swarm-status GOAL_20260415_001

Response:
🚀 SWARM EXECUTION STATUS

Goal: Build Instagram account...
Progress: ████████░░ 45%
Time Elapsed: 24 hours
ETA: 24 hours

Active Slots (3/5):
┌─ Spark: 65% (4 tasks completed, 2 running)
├─ Forge: 55% (3 tasks completed, 2 running)
└─ Shield: 40% (1 task completed, 1 running)

Current Tasks:
• spark/Buse: Generating 30 Instagram posts
• forge/Seda: Finalizing lead capture API
• shield/Luna: Security audit in progress

Next Milestone: T+36h (Deploy service)
```

### Command 3: Final Report
```
/swarm-report GOAL_20260415_001

Response:
✅ SWARM EXECUTION COMPLETE

Goal: Build Instagram account...
Status: SUCCESS
Duration: 48 hours 15 minutes
Slots Used: 5/5 (forge, spark, nexus, atlas, shield)

Results:
├─ Content Created: 30 Instagram posts
├─ Lead Captures: Setup complete
├─ API Deployments: 2 (main + backup)
├─ Security: Passed all audits
└─ Strategy: Growth plan for Q2

Metrics:
├─ Code Lines: 2,400
├─ Personas Involved: 7
├─ Tasks Completed: 42/42 (100%)
├─ Errors: 0
├─ Cost Estimate: ₺X,XXX

Detailed Report: /outputs/swarm_reports/GOAL_20260415_001.json
```

---

## 8️⃣ FILES TO CREATE

### New Files (8 tane)

| Dosya | LOC | Amaç |
|-------|-----|------|
| `server/agents/canonical/slot_coordinator.py` | 150 | Base class |
| `server/agents/canonical/forge_slot.py` | 120 | Code slot |
| `server/agents/canonical/spark_slot.py` | 120 | Content slot |
| `server/agents/canonical/nexus_slot.py` | 100 | Ops slot |
| `server/agents/canonical/atlas_slot.py` | 100 | Strategy slot |
| `server/agents/canonical/shield_slot.py` | 100 | Security slot |
| `server/agents/canonical/coordinator.py` | 250 | Master orchestrator |
| `tests/test_coordinator.py` | 200 | Unit + integration tests |

**Total LOC**: 1,140 new lines

### Modified Files (3 tane)

| Dosya | Değişiklik | LOC |
|-------|-----------|-----|
| `bridge.py` | Add `/swarm` commands (3) | +80 |
| `agents.yaml` | Add slot definitions + config | +50 |
| `requirements.txt` | Add dependencies (if needed) | +5 |

---

## 9️⃣ SUCCESS CRITERIA

- ✅ SlotCoordinator base class works
- ✅ All 5 slots can execute tasks in parallel
- ✅ Master coordinator decomposes complex goals
- ✅ `/swarm` command submits goals
- ✅ `/swarm-status` returns accurate progress
- ✅ 95%+ goal completion rate (48h timeout)
- ✅ Error recovery working (failed task retry)
- ✅ All tests passing
- ✅ Zero race conditions (state sync working)
- ✅ Performance: Can handle 5+ concurrent goals

---

## 🔟 EXECUTION TIMELINE

### Week 1
- Mon-Tue: Phase 1 (Base infrastructure)
- Wed-Thu: Phase 2 (Slot implementations)
- Fri: Phase 3 (Master coordinator) start

### Week 2
- Mon-Wed: Phase 3 continuation + Phase 4 (Bridge)
- Thu-Fri: Phase 5 (Testing + refinement)

### End Result
- production-ready swarm orchestration
- All tests passing
- Ready for Ekrem's AI influencer automation launch

---

## 1️⃣1️⃣ CODEX WORK DISTRIBUTION

### Codex forge/Seda (Code Expert)
- [ ] SlotCoordinator base class
- [ ] ForgeSlot implementation
- [ ] Task queue + state management
- [ ] Unit test framework

### Codex spark/Buse (Content Expert)
- [ ] SparkSlot implementation
- [ ] Content decomposition logic
- [ ] Integration tests

### Codex nexus/Sabrican (Ops Expert)
- [ ] NexusSlot implementation
- [ ] Deployment coordination
- [ ] Error recovery + retries

### Codex atlas/Sabri (Strategy Expert)
- [ ] AtlasSlot implementation
- [ ] Goal decomposition algorithm
- [ ] Progress reporting

### Codex shield/Luna (Security Expert)
- [ ] ShieldSlot implementation
- [ ] Security audit logic
- [ ] Data protection review

---

## 1️⃣2️⃣ QUICK START

### Run Phase 1 Locally
```bash
# Create base coordinator
cd server/agents/canonical
touch slot_coordinator.py

# Copy template (from below)
```

### Template: SlotCoordinator
```python
"""Base class for slot-level coordination"""

import asyncio
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
from server.agents.canonical.base import CanonicalAgent

@dataclass
class Task:
    task_id: str
    description: str
    domain: str
    assigned_persona: str
    status: str = "pending"
    created_at: datetime = field(default_factory=datetime.now)
    result: Optional[str] = None

class SlotCoordinator(CanonicalAgent):
    """Base coordinator for Codex slots"""
    
    name: str = "SlotCoordinator"
    personas: List[str] = []
    domain: str = ""
    
    def __init__(self):
        super().__init__()
        self.task_queue = asyncio.Queue()
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: List[Task] = []
    
    async def execute_task(self, task: Task):
        """Main execution loop"""
        pass
    
    async def get_status(self) -> Dict[str, Any]:
        """Return slot status"""
        return {
            "slot": self.name,
            "active_tasks": len(self.active_tasks),
            "completed": len(self.completed_tasks),
            "utilization": len(self.active_tasks) / len(self.personas)
        }

# Implementation files:
# - forge_slot.py (extends SlotCoordinator)
# - spark_slot.py (extends SlotCoordinator)
# - nexus_slot.py (extends SlotCoordinator)
# - atlas_slot.py (extends SlotCoordinator)
# - shield_slot.py (extends SlotCoordinator)
```

---

## NEXT STEP: Bunu Codex'lere dağıtalım mı?

**Option A**: Fork off 5 parallel Codex tasks
- Each persona builds their own slot
- Takımlardan geri geliş: 4-6 saat
- Integration: 2 saat

**Option B**: Sequence (bir sonra diğeri)
- Daha güvenli ama yavaş
- 40+ saatlik çalışma

**Tavsiye**: **Option A** (parallel = hızlı + efficient)

Hazır mısın? 🚀
