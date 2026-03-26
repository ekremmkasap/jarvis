"""
Collaboration Bridge - Claude ↔ JARVIS
OpenCode tarafından tasarlanan dual-agent collaboration protocol

Roller:
- Claude: Architect / Analyst (düşünme motoru)
- JARVIS: Operator / Runtime (çalışan sistem)

Bridge sorumluluğu:
1. Task ownership tracking
2. Handoff contract management
3. Exchange zone coordination
4. Review gate enforcement
5. State synchronization
"""

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


ROOT_DIR = Path(__file__).resolve().parents[2]
EXCHANGE_DIR = ROOT_DIR / "server" / "agent_workspace" / "exchange"
BRIDGE_STATE = ROOT_DIR / "server" / "agent_workspace" / "bridge_state.json"


class TaskContract:
    """
    Her işin standart kimlik kartı
    Claude ve JARVIS arasında geçerli ortak dil
    """

    def __init__(
        self,
        task_id: str,
        title: str,
        goal: str,
        owner: str,  # "claude" | "jarvis" | "human"
        source: str,  # hangi agent/sistem başlattı
        status: str = "pending",  # pending | in_progress | review | completed | rejected
        priority: int = 5,  # 1 (en yüksek) - 10 (en düşük)
        risk_level: str = "medium",  # low | medium | high | critical
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None
    ):
        self.task_id = task_id
        self.title = title
        self.goal = goal
        self.owner = owner
        self.source = source
        self.status = status
        self.priority = priority
        self.risk_level = risk_level
        self.tags = tags or []
        self.metadata = metadata or {}
        self.created_at = datetime.now().isoformat()
        self.updated_at = self.created_at

    def to_dict(self) -> Dict:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "goal": self.goal,
            "owner": self.owner,
            "source": self.source,
            "status": self.status,
            "priority": self.priority,
            "risk_level": self.risk_level,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "TaskContract":
        task = cls(
            task_id=data["task_id"],
            title=data["title"],
            goal=data["goal"],
            owner=data["owner"],
            source=data["source"],
            status=data.get("status", "pending"),
            priority=data.get("priority", 5),
            risk_level=data.get("risk_level", "medium"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {})
        )
        task.created_at = data.get("created_at", task.created_at)
        task.updated_at = data.get("updated_at", task.updated_at)
        return task


class HandoffContract:
    """
    Claude -> JARVIS devir teslim paketi

    Claude'un önerisi bu formatta staging'e düşer
    JARVIS onu okur, işler, sonuç yazar
    """

    def __init__(
        self,
        handoff_id: str,
        task_id: str,
        from_agent: str,
        to_agent: str,
        handoff_type: str,  # analysis | recommendation | pattern | architecture | task
        content: Dict[str, Any],
        confidence: float = 0.8,  # 0.0 - 1.0
        requires_human_review: bool = False
    ):
        self.handoff_id = handoff_id
        self.task_id = task_id
        self.from_agent = from_agent
        self.to_agent = to_agent
        self.handoff_type = handoff_type
        self.content = content
        self.confidence = confidence
        self.requires_human_review = requires_human_review
        self.created_at = datetime.now().isoformat()
        self.status = "pending"  # pending | accepted | rejected

    def to_dict(self) -> Dict:
        return {
            "handoff_id": self.handoff_id,
            "task_id": self.task_id,
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "handoff_type": self.handoff_type,
            "content": self.content,
            "confidence": self.confidence,
            "requires_human_review": self.requires_human_review,
            "created_at": self.created_at,
            "status": self.status
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "HandoffContract":
        handoff = cls(
            handoff_id=data["handoff_id"],
            task_id=data["task_id"],
            from_agent=data["from_agent"],
            to_agent=data["to_agent"],
            handoff_type=data["handoff_type"],
            content=data["content"],
            confidence=data.get("confidence", 0.8),
            requires_human_review=data.get("requires_human_review", False)
        )
        handoff.created_at = data.get("created_at", handoff.created_at)
        handoff.status = data.get("status", "pending")
        return handoff


class CollaborationBridge:
    """
    Claude ↔ JARVIS köprüsü

    Görevleri:
    1. Exchange zone'ları yönet (claude/incoming, claude/outgoing, jarvis/staging)
    2. Task ownership'i takip et
    3. Handoff contract'ları işle
    4. Review gate'leri uygula
    5. State'i senkronize et
    """

    def __init__(self):
        self.exchange_dir = EXCHANGE_DIR
        self.bridge_state_path = BRIDGE_STATE

        # Exchange zone klasörleri
        self.claude_incoming = self.exchange_dir / "claude" / "incoming"
        self.claude_outgoing = self.exchange_dir / "claude" / "outgoing"
        self.jarvis_staging = self.exchange_dir / "jarvis" / "staging"
        self.jarvis_approved = self.exchange_dir / "jarvis" / "approved"
        self.jarvis_rejected = self.exchange_dir / "jarvis" / "rejected"

        self._ensure_exchange_zones()
        self.state = self._load_state()

    def _ensure_exchange_zones(self):
        """Exchange zone klasörlerini oluştur"""
        for zone in [
            self.claude_incoming,
            self.claude_outgoing,
            self.jarvis_staging,
            self.jarvis_approved,
            self.jarvis_rejected
        ]:
            zone.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> Dict:
        """Bridge state'ini yükle"""
        if self.bridge_state_path.exists():
            try:
                return json.loads(self.bridge_state_path.read_text(encoding="utf-8"))
            except:
                pass
        return {
            "tasks": {},
            "handoffs": {},
            "stats": {
                "total_tasks": 0,
                "total_handoffs": 0,
                "successful_handoffs": 0,
                "failed_handoffs": 0
            },
            "updated_at": datetime.now().isoformat()
        }

    def _save_state(self):
        """Bridge state'ini kaydet"""
        self.state["updated_at"] = datetime.now().isoformat()
        self.bridge_state_path.write_text(
            json.dumps(self.state, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def create_task(
        self,
        title: str,
        goal: str,
        owner: str,
        source: str,
        priority: int = 5,
        risk_level: str = "medium",
        tags: Optional[List[str]] = None
    ) -> TaskContract:
        """
        Yeni task oluştur
        """
        task_id = str(uuid.uuid4())[:8]
        task = TaskContract(
            task_id=task_id,
            title=title,
            goal=goal,
            owner=owner,
            source=source,
            priority=priority,
            risk_level=risk_level,
            tags=tags
        )

        self.state["tasks"][task_id] = task.to_dict()
        self.state["stats"]["total_tasks"] += 1
        self._save_state()

        return task

    def create_handoff(
        self,
        task_id: str,
        from_agent: str,
        to_agent: str,
        handoff_type: str,
        content: Dict[str, Any],
        confidence: float = 0.8,
        requires_human_review: bool = False
    ) -> HandoffContract:
        """
        Yeni handoff contract oluştur

        Claude -> JARVIS devir teslim paketi
        """
        handoff_id = str(uuid.uuid4())[:8]
        handoff = HandoffContract(
            handoff_id=handoff_id,
            task_id=task_id,
            from_agent=from_agent,
            to_agent=to_agent,
            handoff_type=handoff_type,
            content=content,
            confidence=confidence,
            requires_human_review=requires_human_review
        )

        self.state["handoffs"][handoff_id] = handoff.to_dict()
        self.state["stats"]["total_handoffs"] += 1
        self._save_state()

        # Handoff paketini ilgili exchange zone'a yaz
        self._write_handoff_to_zone(handoff)

        return handoff

    def _write_handoff_to_zone(self, handoff: HandoffContract):
        """
        Handoff paketini uygun exchange zone'a yaz
        """
        if handoff.to_agent == "jarvis":
            # Claude -> JARVIS
            target_dir = self.jarvis_staging
        elif handoff.to_agent == "claude":
            # JARVIS -> Claude
            target_dir = self.claude_incoming
        else:
            return

        filename = f"handoff_{handoff.handoff_id}_{handoff.handoff_type}.json"
        filepath = target_dir / filename

        filepath.write_text(
            json.dumps(handoff.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def get_pending_handoffs(self, for_agent: str) -> List[HandoffContract]:
        """
        Belirli bir agent için bekleyen handoff'ları getir
        """
        handoffs = []
        for handoff_data in self.state["handoffs"].values():
            if handoff_data["to_agent"] == for_agent and handoff_data["status"] == "pending":
                handoffs.append(HandoffContract.from_dict(handoff_data))
        return handoffs

    def accept_handoff(self, handoff_id: str, result: Optional[Dict] = None):
        """
        Handoff'ı kabul et ve işle
        """
        if handoff_id not in self.state["handoffs"]:
            return False

        self.state["handoffs"][handoff_id]["status"] = "accepted"
        self.state["handoffs"][handoff_id]["result"] = result or {}
        self.state["handoffs"][handoff_id]["accepted_at"] = datetime.now().isoformat()
        self.state["stats"]["successful_handoffs"] += 1
        self._save_state()

        return True

    def reject_handoff(self, handoff_id: str, reason: str):
        """
        Handoff'ı reddet
        """
        if handoff_id not in self.state["handoffs"]:
            return False

        self.state["handoffs"][handoff_id]["status"] = "rejected"
        self.state["handoffs"][handoff_id]["rejection_reason"] = reason
        self.state["handoffs"][handoff_id]["rejected_at"] = datetime.now().isoformat()
        self.state["stats"]["failed_handoffs"] += 1
        self._save_state()

        return True

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """
        Task durumunu getir
        """
        return self.state["tasks"].get(task_id)

    def get_bridge_stats(self) -> Dict:
        """
        Bridge istatistiklerini getir
        """
        return {
            "total_tasks": self.state["stats"]["total_tasks"],
            "active_tasks": len([t for t in self.state["tasks"].values() if t["status"] in ["pending", "in_progress"]]),
            "total_handoffs": self.state["stats"]["total_handoffs"],
            "pending_handoffs": len([h for h in self.state["handoffs"].values() if h["status"] == "pending"]),
            "successful_handoffs": self.state["stats"]["successful_handoffs"],
            "failed_handoffs": self.state["stats"]["failed_handoffs"],
            "success_rate": self.state["stats"]["successful_handoffs"] / max(1, self.state["stats"]["total_handoffs"])
        }


# Global instance
_bridge = None

def get_bridge() -> CollaborationBridge:
    """Global bridge instance"""
    global _bridge
    if _bridge is None:
        _bridge = CollaborationBridge()
    return _bridge


if __name__ == "__main__":
    # Test
    bridge = get_bridge()

    # Örnek task oluştur
    task = bridge.create_task(
        title="GitHub trending repos analizi",
        goal="Son 7 günün trending Python repo'larını analiz et",
        owner="claude",
        source="night_runner",
        priority=3,
        risk_level="low",
        tags=["analysis", "github", "trending"]
    )

    print(f"[OK] Task olusturuldu: {task.task_id}")

    # Ornek handoff olustur
    handoff = bridge.create_handoff(
        task_id=task.task_id,
        from_agent="claude",
        to_agent="jarvis",
        handoff_type="analysis",
        content={
            "analysis": "25 trending repo bulundu",
            "patterns": ["MCP", "multi-agent", "RAG"],
            "recommendation": "MCP integration oncelikli"
        },
        confidence=0.85,
        requires_human_review=False
    )

    print(f"[OK] Handoff olusturuldu: {handoff.handoff_id}")
    print(f"[STATS] Bridge stats: {bridge.get_bridge_stats()}")
