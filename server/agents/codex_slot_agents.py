#!/usr/bin/env python3
"""
Codex Slot Agent Coordinators (5 slots)
Each slot has its own agent(s) and handles parallel task execution.

Architecture:
- ForgeSlotAgent: Seda (code) + Mert (research)
- NexusSlotAgent: Sabrican (ops/automation)
- SparkSlotAgent: Buse (content) + Eren (data)
- AtlasSlotAgent: Sabri (strategy/CEO)
- ShieldSlotAgent: Luna (security - lab only)
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, Dict, Any, List
from enum import Enum

logger = logging.getLogger(__name__)

# ==================== SLOT ENUM ====================

class CodexSlot(Enum):
    """5 Codex account slots."""
    FORGE = "forge"
    NEXUS = "nexus"
    SPARK = "spark"
    ATLAS = "atlas"
    SHIELD = "shield"

# ==================== BASE SLOT AGENT ====================

class SlotAgent(ABC):
    """Base class for all Codex slot agents."""
    
    slot: CodexSlot
    personas: List[str]
    domain: str
    
    async def execute_task(self, prompt: str, persona: Optional[str] = None) -> str:
        """
        Execute task on this slot.
        
        Args:
            prompt: Task description
            persona: Optional persona preference (e.g., "seda", "mert")
        
        Returns:
            Result string
        """
        logger.info(f"[{self.slot.value}] Executing ({persona or 'default'}): {prompt[:50]}...")
        
        try:
            result = await self._call_codex(prompt, persona)
            logger.info(f"[{self.slot.value}] ✓ Complete: {result[:100]}")
            return result
        except Exception as e:
            logger.error(f"[{self.slot.value}] ✗ Error: {str(e)}")
            raise
    
    @abstractmethod
    async def _call_codex(self, prompt: str, persona: Optional[str]) -> str:
        """Call actual Codex API - implemented per slot."""
        pass
    
    def get_persona(self, requested: Optional[str] = None) -> str:
        """Get persona for this slot (fallback if not available)."""
        if requested and requested in self.personas:
            return requested
        return self.personas[0]  # default


# ==================== FORGE SLOT (Code/Debug) ====================

class ForgeSlotAgent(SlotAgent):
    """
    Forge slot: Code writing + debugging
    Personas: Seda (code), Mert (research)
    Domain: code/debug/PR review
    """
    
    slot = CodexSlot.FORGE
    personas = ["seda", "mert"]
    domain = "code/debug/PR review"
    
    async def _call_codex(self, prompt: str, persona: Optional[str] = None) -> str:
        """Execute with persona system prompt."""
        chosen_persona = self.get_persona(persona)
        
        system_prompts = {
            "seda": "Sen Seda, expert kod yazıcısı ve debugger'sın. Türkçe açıklamalar yap.",
            "mert": "Sen Mert, research uzmanısın. Detaylı analiz yap. Kaynakları cite et.",
        }
        
        system = system_prompts.get(chosen_persona, system_prompts["seda"])
        
        # TODO: Real Codex API call
        await asyncio.sleep(0.5)  # Mock
        return f"[FORGE/{chosen_persona}] {prompt[:100]}... ✓"


# ==================== NEXUS SLOT (Ops/Automation) ====================

class NexusSlotAgent(SlotAgent):
    """
    Nexus slot: Operations + automation
    Personas: Sabrican (ops)
    Domain: ops/automation/OpenClaw
    """
    
    slot = CodexSlot.NEXUS
    personas = ["sabrican"]
    domain = "ops/automation/OpenClaw"
    
    async def _call_codex(self, prompt: str, persona: Optional[str] = None) -> str:
        """Execute ops task."""
        system = "Sen Sabrican, ops ve automation uzmanısın. Sistem yönetimi yap."
        
        # TODO: Real Codex API call
        await asyncio.sleep(0.6)  # Mock
        return f"[NEXUS/sabrican] {prompt[:100]}... ✓"


# ==================== SPARK SLOT (Content/Research) ====================

class SparkSlotAgent(SlotAgent):
    """
    Spark slot: Content creation + research
    Personas: Buse (content), Eren (data/video)
    Domain: content/research/data
    """
    
    slot = CodexSlot.SPARK
    personas = ["buse", "eren"]
    domain = "content/research/data"
    
    async def _call_codex(self, prompt: str, persona: Optional[str] = None) -> str:
        """Execute content/research task."""
        chosen_persona = self.get_persona(persona)
        
        system_prompts = {
            "buse": "Sen Buse, social media ve marketing uzmanısın. İçerik yaz.",
            "eren": "Sen Eren, data ve video analisti. Detaylı raporlar hazırla.",
        }
        
        system = system_prompts.get(chosen_persona, system_prompts["buse"])
        
        # TODO: Real Codex API call
        await asyncio.sleep(0.7)  # Mock
        return f"[SPARK/{chosen_persona}] {prompt[:100]}... ✓"


# ==================== ATLAS SLOT (Strategy/CEO) ====================

class AtlasSlotAgent(SlotAgent):
    """
    Atlas slot: Strategy + CEO decisions
    Personas: Sabri (CEO/strategy)
    Domain: strategy/planning
    """
    
    slot = CodexSlot.ATLAS
    personas = ["sabri"]
    domain = "strategy/planning/CEO"
    
    async def _call_codex(self, prompt: str, persona: Optional[str] = None) -> str:
        """Execute strategy task."""
        system = "Sen Sabri, CEO'sun. Stratejik kararlar ver. İş planlaması yap."
        
        # TODO: Real Codex API call
        await asyncio.sleep(0.5)  # Mock
        return f"[ATLAS/sabri] {prompt[:100]}... ✓"


# ==================== SHIELD SLOT (Security) ====================

class ShieldSlotAgent(SlotAgent):
    """
    Shield slot: Security (lab-only)
    Personas: Luna (security)
    Domain: security testing (lab-only, no production attacks)
    Restrictions: Hard-reject unauthorized exploits
    """
    
    slot = CodexSlot.SHIELD
    personas = ["luna"]
    domain = "security (lab-only)"
    restricted = True
    
    async def _call_codex(self, prompt: str, persona: Optional[str] = None) -> str:
        """
        Execute security task with restrictions.
        
        Hard-reject:
        - Active attacks on production systems
        - Unauthorized penetration testing
        - Exploit development for real targets
        """
        
        # Check for restricted keywords
        dangerous_words = [
            "hack", "breach", "exploit", "attack", "crack",
            "backdoor", "malware", "ransomware", "unauthorized"
        ]
        prompt_lower = prompt.lower()
        
        for word in dangerous_words:
            if word in prompt_lower:
                # Check context - reject if seems real
                if any(x in prompt_lower for x in ["production", "live", "real", "active"]):
                    return f"[SHIELD/luna] ❌ REJECT: Unauthorized attack attempt detected. Lab-only mode enforced."
        
        system = "Sen Luna, security uzmanısın. Güvenlik testleri yap (lab-only, authorized)."
        
        # TODO: Real Codex API call
        await asyncio.sleep(0.8)  # Mock
        return f"[SHIELD/luna] {prompt[:100]}... ✓"


# ==================== SLOT REGISTRY ====================

class SlotRegistry:
    """Registry of all 5 Codex slot agents."""
    
    _agents: Dict[CodexSlot, SlotAgent] = {}
    
    @classmethod
    def init(cls):
        """Initialize all slot agents."""
        cls._agents = {
            CodexSlot.FORGE: ForgeSlotAgent(),
            CodexSlot.NEXUS: NexusSlotAgent(),
            CodexSlot.SPARK: SparkSlotAgent(),
            CodexSlot.ATLAS: AtlasSlotAgent(),
            CodexSlot.SHIELD: ShieldSlotAgent(),
        }
        logger.info("✓ All 5 Codex slot agents initialized")
    
    @classmethod
    def get_agent(cls, slot: CodexSlot) -> SlotAgent:
        """Get agent for slot."""
        if not cls._agents:
            cls.init()
        return cls._agents[slot]
    
    @classmethod
    def list_slots(cls) -> Dict[str, str]:
        """List all slots + domains."""
        if not cls._agents:
            cls.init()
        return {
            agent.slot.value: agent.domain
            for agent in cls._agents.values()
        }


# ==================== CLI FOR TESTING ====================

async def test_slot_agents():
    """Test all slot agents."""
    SlotRegistry.init()
    
    test_tasks = [
        (CodexSlot.FORGE, "Python async await örneği yaz", "seda"),
        (CodexSlot.NEXUS, "Docker container setup script", None),
        (CodexSlot.SPARK, "5 viral Instagram caption", "buse"),
        (CodexSlot.ATLAS, "2026 business strategy plan", None),
        (CodexSlot.SHIELD, "SQL injection test (lab only)", "luna"),
    ]
    
    print("\n" + "="*60)
    print("TESTING 5 CODEX SLOT AGENTS")
    print("="*60)
    
    # Run all in parallel
    tasks = [
        SlotRegistry.get_agent(slot).execute_task(prompt, persona=persona)
        for slot, prompt, persona in test_tasks
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    print("\nRESULTS:")
    for (slot, prompt, persona), result in zip(test_tasks, results):
        status = "✓" if not isinstance(result, Exception) else "✗"
        print(f"{status} {slot.value:8} ({persona or 'default'}): {result}")
    
    print("="*60 + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(test_slot_agents())
