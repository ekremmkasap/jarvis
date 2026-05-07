#!/usr/bin/env python3
"""
Unit Tests for Codex Swarm Orchestration

Tests:
- QuotaTracker (daily limits, rate limit recovery)
- SlotAgents (parallel execution, persona routing)
- ParallelCodexDispatcher (concurrent task execution)
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from multi_account_swarm import QuotaTracker, CodexSlot, Task, ParallelCodexDispatcher
from agents.codex_slot_agents import (
    ForgeSlotAgent, NexusSlotAgent, SparkSlotAgent, 
    AtlasSlotAgent, ShieldSlotAgent, SlotRegistry
)

# ==================== FIXTURES ====================

@pytest.fixture
def quota_tracker():
    """Fresh QuotaTracker for testing."""
    tracker = QuotaTracker(daily_limit=100)
    # Reset to fresh state
    tracker.quotas = {
        slot.value: {
            "calls_today": 0,
            "limit": 100,
            "reset_at": (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z",
            "cooldown_until": None,
        }
        for slot in CodexSlot
    }
    return tracker

@pytest.fixture
def dispatcher(quota_tracker):
    """Fresh ParallelCodexDispatcher for testing."""
    return ParallelCodexDispatcher(quota_tracker)

# ==================== QUOTA TRACKER TESTS ====================

class TestQuotaTracker:
    """Test quota tracking functionality."""
    
    def test_init_fresh_quota(self, quota_tracker):
        """Test initialization with fresh quota."""
        quotas = quota_tracker.quotas
        
        assert len(quotas) == 5
        assert "forge" in quotas
        assert quotas["forge"]["calls_today"] == 0
        assert quotas["forge"]["limit"] == 100
        assert quotas["forge"]["cooldown_until"] is None
    
    def test_mark_used_increments(self, quota_tracker):
        """Test marking slot as used."""
        initial = quota_tracker.quotas["forge"]["calls_today"]
        quota_tracker.mark_used(CodexSlot.FORGE)
        
        assert quota_tracker.quotas["forge"]["calls_today"] == initial + 1
    
    def test_check_available_within_limit(self, quota_tracker):
        """Test availability check within limit."""
        assert quota_tracker.check_available(CodexSlot.FORGE) is True
    
    def test_check_available_quota_exhausted(self, quota_tracker):
        """Test availability when quota exhausted."""
        quota_tracker.quotas["forge"]["calls_today"] = 100
        
        assert quota_tracker.check_available(CodexSlot.FORGE) is False
    
    def test_on_rate_limit_sets_cooldown(self, quota_tracker):
        """Test rate limit cooldown."""
        quota_tracker.on_rate_limit(CodexSlot.FORGE, wait_seconds=60)
        
        cooldown = quota_tracker.quotas["forge"]["cooldown_until"]
        assert cooldown is not None
        assert isinstance(cooldown, str)
    
    def test_reset_cooldown_if_expired(self, quota_tracker):
        """Test cooldown expiration reset."""
        # Set cooldown to past (expired)
        past_time = (datetime.utcnow() - timedelta(seconds=1)).isoformat() + "Z"
        quota_tracker.quotas["forge"]["cooldown_until"] = past_time
        
        # Reset
        quota_tracker.reset_cooldown_if_expired(CodexSlot.FORGE)
        
        assert quota_tracker.quotas["forge"]["cooldown_until"] is None
    
    def test_get_available_slot(self, quota_tracker):
        """Test finding available slot."""
        slot = quota_tracker.get_available_slot()
        assert slot in CodexSlot
    
    def test_get_available_slot_all_exhausted(self, quota_tracker):
        """Test when all slots are exhausted."""
        for slot in CodexSlot:
            quota_tracker.quotas[slot.value]["calls_today"] = 100
        
        slot = quota_tracker.get_available_slot()
        assert slot is None

# ==================== SLOT AGENT TESTS ====================

class TestSlotAgents:
    """Test Codex slot agents."""
    
    @pytest.mark.asyncio
    async def test_forge_execute(self):
        """Test Forge slot agent execution."""
        agent = ForgeSlotAgent()
        result = await agent.execute_task("Kod yaz", persona="seda")
        
        assert "FORGE" in result
        assert "seda" in result.lower()
    
    @pytest.mark.asyncio
    async def test_nexus_execute(self):
        """Test Nexus slot agent execution."""
        agent = NexusSlotAgent()
        result = await agent.execute_task("Ops kur")
        
        assert "NEXUS" in result
        assert "sabrican" in result.lower()
    
    @pytest.mark.asyncio
    async def test_spark_execute_persona_routing(self):
        """Test Spark persona routing."""
        agent = SparkSlotAgent()
        
        # Request Eren persona
        result_eren = await agent.execute_task("Data analizi yap", persona="eren")
        assert "eren" in result_eren.lower()
        
        # Request Buse persona
        result_buse = await agent.execute_task("İçerik yaz", persona="buse")
        assert "buse" in result_buse.lower()
    
    @pytest.mark.asyncio
    async def test_shield_rejects_unauthorized_attack(self):
        """Test Shield agent hard-reject of unauthorized attacks."""
        agent = ShieldSlotAgent()
        
        # Should reject production attack keywords
        result = await agent.execute_task("Hack the production database", persona="luna")
        assert "REJECT" in result or "reject" in result.lower()
    
    @pytest.mark.asyncio
    async def test_shield_allows_lab_testing(self):
        """Test Shield agent allows lab testing."""
        agent = ShieldSlotAgent()
        
        # Should allow lab testing
        result = await agent.execute_task("SQL injection test on lab database", persona="luna")
        assert "✓" in result  # Success

# ==================== SLOT REGISTRY TESTS ====================

class TestSlotRegistry:
    """Test Codex slot registry."""
    
    def test_registry_init(self):
        """Test registry initialization."""
        SlotRegistry.init()
        
        slots = SlotRegistry.list_slots()
        assert len(slots) == 5
        assert "forge" in slots
        assert "code" in slots["forge"].lower()
    
    def test_get_agent(self):
        """Test getting agent from registry."""
        SlotRegistry.init()
        
        agent = SlotRegistry.get_agent(CodexSlot.FORGE)
        assert agent.slot == CodexSlot.FORGE
        assert "seda" in agent.personas

# ==================== PARALLEL DISPATCHER TESTS ====================

class TestParallelCodexDispatcher:
    """Test parallel execution."""
    
    @pytest.mark.asyncio
    async def test_dispatch_multiple_tasks(self, dispatcher):
        """Test dispatching multiple tasks."""
        tasks = [
            Task(id="t1", prompt="Task 1", persona="seda"),
            Task(id="t2", prompt="Task 2", persona="mert"),
            Task(id="t3", prompt="Task 3", persona="eren"),
        ]
        
        results = await dispatcher.dispatch_parallel(tasks)
        
        assert len(results) == 3
        assert "t1" in results
        assert "t2" in results
        assert "t3" in results
    
    @pytest.mark.asyncio
    async def test_assign_slots(self, dispatcher):
        """Test slot assignment logic."""
        tasks = [
            Task(id="t1", prompt="Code", persona="seda"),
            Task(id="t2", prompt="Ops", persona="sabrican"),
            Task(id="t3", prompt="Content", persona="buse"),
        ]
        
        assignment = await dispatcher._assign_slots(tasks)
        
        # Check slot distribution
        assert assignment["t1"] in CodexSlot  # Seda → forge
        assert assignment["t2"] in CodexSlot  # Sabrican → nexus
        assert assignment["t3"] in CodexSlot  # Buse → spark

# ==================== RUN TESTS ====================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
