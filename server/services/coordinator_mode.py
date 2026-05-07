"""
Coordinator/Worker Swarm Mode — CEO-benzeri Swarm Yönetimi

Jarvis'in CEO (Sabri) ve Worker (Seda, Mert, Eren, vb.) persona'larını
formal bir swarm mimarisine entegre et.

Coordinator Mode:
  - CEO agent (Sabri) kısıtlı olmayan araç setine sahip
  - Worker agent'ları (Seda, Mert) limited tools kullanabilir
  - Delegasyon ve team spawn formal config'den kontrol edilir

Normal Mode:
  - Tüm persona'lar eşit araç setine sahip (mevcut davranış)
"""

import os
import json
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Agent türleri"""
    COORDINATOR = "coordinator"  # CEO — full tool access
    EXECUTOR = "executor"         # Developer persona — limited tools
    RESEARCHER = "researcher"     # Research persona — web/data tools
    DELEGATOR = "delegator"       # Strategy persona — planning tools
    WORKER = "worker"            # Generic worker — basic tools


@dataclass
class CoordinatorConfig:
    """Coordinator mode konfigürasyonu"""
    enabled: bool = False
    ceo_agent_id: str = "jarvis-ceo"  # Coordinator persona ID
    team: List['AgentRole'] = field(default_factory=list)


@dataclass
class AgentRole:
    """Agent'ın team role'ü"""
    persona_id: str               # "seda", "mert", "eren"
    agent_type: AgentType
    domain: Optional[str] = None  # "dev", "research", "strategy"
    tools: Set[str] = field(default_factory=set)
    
    def to_dict(self) -> dict:
        return {
            'persona_id': self.persona_id,
            'agent_type': self.agent_type.value,
            'domain': self.domain,
            'tools': list(self.tools)
        }


# ===== Tool Definitions =====

COORDINATOR_ONLY_TOOLS = {
    'persona_switch',      # CEO → Persona switch
    'spawn_worker',         # Alt-agent spawn (async task)
    'kill_worker',         # Alt-agent terminate
    'broadcast_message'    # Team-wide message
}

EXECUTOR_TOOLS = {
    'file_read',
    'file_write',
    'bash_execute',
    'code_review',
    'test_run'
}

RESEARCHER_TOOLS = {
    'web_search',
    'google_scholar',
    'instagram_scrape',
    'data_fetch',
    'rss_parse'
}

DELEGATOR_TOOLS = {
    'task_plan',
    'dependency_check',
    'risk_assess',
    'consolidate_memory',
    'generate_report'
}

WORKER_TOOLS = {
    'message_send',
    'status_report'
}

# Her tool type'a accessible olacak base tools
BASE_TOOLS = {
    'help',
    'context_reset',
    'transcript_save'
}


# ===== Coordinator Mode Logic =====

def load_coordinator_config(config_file: str) -> CoordinatorConfig:
    """
    Coordinator config YAML/JSON'ından yükle.
    
    Örnek (coordinator_config.json):
    {
      "enabled": true,
      "ceo_agent_id": "sabri",
      "team": [
        {
          "persona_id": "seda",
          "agent_type": "executor",
          "domain": "dev",
          "tools": ["file_read", "file_write", "bash_execute", "code_review", "test_run"]
        },
        {
          "persona_id": "mert",
          "agent_type": "researcher",
          "domain": "research",
          "tools": ["web_search", "data_fetch"]
        }
      ]
    }
    """
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        config = CoordinatorConfig(
            enabled=data.get('enabled', False),
            ceo_agent_id=data.get('ceo_agent_id', 'jarvis-ceo')
        )
        
        # Team member'ları parse et
        for member_data in data.get('team', []):
            agent_type = AgentType(member_data['agent_type'])
            role = AgentRole(
                persona_id=member_data['persona_id'],
                agent_type=agent_type,
                domain=member_data.get('domain'),
                tools=set(member_data.get('tools', []))
            )
            config.team.append(role)
        
        logger.info(f"✓ Coordinator config loaded: {len(config.team)} team members")
        return config
    
    except Exception as e:
        logger.warning(f"Failed to load coordinator config: {e}. Using default (disabled).")
        return CoordinatorConfig()


def is_coordinator_mode() -> bool:
    """Coordinator modu aktif mi?"""
    return os.getenv('JARVIS_COORDINATOR_MODE', 'false').lower() == 'true'


def get_available_tools(
    agent_id: str,
    coordinator_config: Optional[CoordinatorConfig] = None
) -> Set[str]:
    """
    Agent tipine göre available tools'u döndür.
    
    Args:
      agent_id: Agent persona ID ("seda", "mert", "sabri", vb.)
      coordinator_config: Coordinator configuration
    
    Returns:
      Set[str] of available tool names
    """
    base = BASE_TOOLS.copy()
    
    # Coordinator mode kapalıysa tümü kısıtlama yok
    if not is_coordinator_mode() or coordinator_config is None:
        all_tools = (
            COORDINATOR_ONLY_TOOLS | EXECUTOR_TOOLS | RESEARCHER_TOOLS |
            DELEGATOR_TOOLS | WORKER_TOOLS | BASE_TOOLS
        )
        return all_tools
    
    # Coordinator mode açık: role-based access control
    if agent_id == coordinator_config.ceo_agent_id:
        # CEO: all tools
        return (
            COORDINATOR_ONLY_TOOLS | EXECUTOR_TOOLS | RESEARCHER_TOOLS |
            DELEGATOR_TOOLS | WORKER_TOOLS | BASE_TOOLS
        )
    
    # Team member'ı bul
    for member in coordinator_config.team:
        if member.persona_id == agent_id:
            # Config'de tanımlı tool'lar
            tools = member.tools.copy()
            tools.update(BASE_TOOLS)
            return tools
    
    # Unknown agent: minimal tools
    logger.warning(f"Unknown agent '{agent_id}', granting minimal tools")
    return BASE_TOOLS


def get_agent_role(
    agent_id: str,
    coordinator_config: Optional[CoordinatorConfig] = None
) -> Optional[AgentRole]:
    """Agent'ın team role'ünü al"""
    if coordinator_config is None or not is_coordinator_mode():
        return None
    
    for member in coordinator_config.team:
        if member.persona_id == agent_id:
            return member
    
    return None


def can_use_tool(
    agent_id: str,
    tool_name: str,
    coordinator_config: Optional[CoordinatorConfig] = None
) -> bool:
    """Agent belirli bir tool'u kullanabilir mi?"""
    available_tools = get_available_tools(agent_id, coordinator_config)
    return tool_name in available_tools


def get_coordinator_system_context(
    agent_id: str,
    coordinator_config: Optional[CoordinatorConfig] = None
) -> str:
    """
    Coordinator mode sistem prompt'u — agent'a role'ünü hatırlat.
    
    Returns:
      String system prompt addition
    """
    if not is_coordinator_mode() or coordinator_config is None:
        return ""
    
    role = get_agent_role(agent_id, coordinator_config)
    if not role:
        return ""
    
    if agent_id == coordinator_config.ceo_agent_id:
        return f"""
## Coordinator Mode: Swarm CEO

You are the CEO coordinator of the Jarvis swarm. Your capabilities:
- Spawn and manage worker agents via spawn_worker tool
- Send messages to team members via broadcast_message
- Make strategic decisions and assign tasks
- Consolidate learnings from the entire team

Team under your coordination: {', '.join(m.persona_id for m in coordinator_config.team)}

Available tools: coordinator_only (spawn_worker, kill_worker, broadcast_message) + all standard tools
"""
    else:
        role_desc = role.agent_type.value.title()
        return f"""
## Coordinator Mode: Team Role

You are a {role_desc} in the Jarvis swarm.
- Domain: {role.domain or 'General'}
- Your specialized tools: {', '.join(sorted(role.tools))}
- CEO coordinator: {coordinator_config.ceo_agent_id}

Coordinate with CEO for delegated tasks. Focus on your domain.
"""


# ===== Integration with bridge.py =====

def validate_tool_access(
    agent_id: str,
    tool_name: str,
    coordinator_config: Optional[CoordinatorConfig] = None
) -> tuple[bool, Optional[str]]:
    """
    Tool access'i validate et. Kapalı tool denenmişse error döndür.
    
    Returns:
      (is_allowed, error_message)
    """
    if can_use_tool(agent_id, tool_name, coordinator_config):
        return True, None
    
    available = get_available_tools(agent_id, coordinator_config)
    return False, (
        f"Agent '{agent_id}' cannot use tool '{tool_name}'. "
        f"Available tools: {', '.join(sorted(available))}"
    )


# Export
__all__ = [
    'AgentType',
    'AgentRole',
    'CoordinatorConfig',
    'is_coordinator_mode',
    'load_coordinator_config',
    'get_available_tools',
    'get_agent_role',
    'can_use_tool',
    'get_coordinator_system_context',
    'validate_tool_access'
]
