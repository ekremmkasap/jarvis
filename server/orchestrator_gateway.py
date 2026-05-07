"""
Orchestrator Gateway - Integration layer between JARVIS bridge and AI-Agents-Orchestrator
Routes requests to multiple AI providers (Codex, Claude, Gemini) with intelligent failover
"""

import asyncio
import os
from typing import Optional, Dict, List
from server.account_manager import get_account_manager, Account
from server.orchestrator.adapters.codex_adapter import CodexAdapter
from server.orchestrator.adapters.claude_adapter import ClaudeAdapter
from server.orchestrator.adapters.gemini_adapter import GeminiAdapter

class OrchestratorGateway:
    """Unified gateway for multi-account AI orchestration"""

    def __init__(self):
        self.account_manager = get_account_manager()
        self.adapters: Dict[str, any] = {}
        self._initialize_adapters()

    def _initialize_adapters(self):
        """Initialize adapters from active accounts"""
        self.adapters = {}
        for provider in ["codex", "claude", "gemini"]:
            cred = self.account_manager.get_credential(provider)
            if cred:
                if provider == "codex":
                    self.adapters[provider] = CodexAdapter(api_key=cred)
                elif provider == "claude":
                    self.adapters[provider] = ClaudeAdapter(api_key=cred)
                elif provider == "gemini":
                    self.adapters[provider] = GeminiAdapter(api_key=cred)

    async def query(self, prompt: str, provider: Optional[str] = None, **kwargs) -> str:
        """
        Route query to AI provider with intelligent failover

        Args:
            prompt: User prompt
            provider: Specific provider (codex, claude, gemini) or None for auto-select
            **kwargs: Additional provider-specific arguments

        Returns:
            Response text from AI
        """

        if provider:
            # Use specific provider
            providers = [provider]
        else:
            # Use default priority order
            providers = ["codex", "claude", "gemini"]

        for prov in providers:
            if prov not in self.adapters:
                continue

            try:
                adapter = self.adapters[prov]
                account = self.account_manager.get_active_account(prov)

                if not account:
                    continue

                # Set CODEX_HOME for Codex accounts (isolation)
                if prov == "codex" and account.codex_home:
                    os.environ["CODEX_HOME"] = account.codex_home

                # Execute query
                response = await adapter.query(prompt, **kwargs)

                # Mark account as used
                self.account_manager.mark_used(account.id)

                return response

            except Exception as e:
                print(f"[FAILED] {prov} failed: {e}")
                if account:
                    self.account_manager.mark_failed(account.id)
                continue

        raise Exception("All providers failed")

    async def stream_query(self, prompt: str, provider: Optional[str] = None, **kwargs):
        """Stream response from AI provider"""

        if provider:
            providers = [provider]
        else:
            providers = ["codex", "claude", "gemini"]

        for prov in providers:
            if prov not in self.adapters:
                continue

            try:
                adapter = self.adapters[prov]
                account = self.account_manager.get_active_account(prov)

                if not account:
                    continue

                # Set CODEX_HOME for Codex accounts (isolation)
                if prov == "codex" and account.codex_home:
                    os.environ["CODEX_HOME"] = account.codex_home

                # Stream query
                async for chunk in adapter.stream_query(prompt, **kwargs):
                    yield chunk

                self.account_manager.mark_used(account.id)
                return

            except Exception as e:
                print(f"[FAILED] {prov} stream failed: {e}")
                if account:
                    self.account_manager.mark_failed(account.id)
                continue

        raise Exception("All providers failed for streaming")

    def get_status(self) -> Dict:
        """Get orchestrator status"""
        provider_status: Dict[str, Dict[str, object]] = {}
        healthy = 0
        for provider in ["codex", "claude", "gemini"]:
            active_account = self.account_manager.get_active_account(provider)
            adapter_ready = provider in self.adapters
            provider_state = {
                "available": adapter_ready,
                "active_account": active_account.id if active_account else None,
                "active_email": active_account.email if active_account else None,
                "status": "ready" if adapter_ready and active_account else "unavailable",
            }
            provider_status[provider] = provider_state
            if adapter_ready and active_account:
                healthy += 1

        overall_status = "healthy" if healthy == len(provider_status) else "degraded" if healthy > 0 else "unhealthy"
        return {
            "status": overall_status,
            "accounts": self.account_manager.get_status(),
            "adapters": provider_status,
            "summary": {
                "provider_count": len(provider_status),
                "ready_provider_count": healthy,
            },
        }

    def switch_account(self, account_id: str) -> bool:
        """Switch to specific account"""
        success = self.account_manager.switch_account(account_id)
        if success:
            account = self.account_manager.accounts.get(account_id)
            if account and account.provider == "codex" and account.codex_home:
                os.environ["CODEX_HOME"] = account.codex_home
                print(f"[SWITCH] Set CODEX_HOME={account.codex_home}")
            self._initialize_adapters()
        return success

    def add_account(self, provider: str, credential: str, email: str, codex_home: str = None) -> str:
        """
        Add new account and reinitialize
        For Codex: credential is ignored (uses codex_home path)
        For Claude/Gemini: credential is auth token
        """
        if provider == "codex":
            # For Codex, codex_home path is required
            if not codex_home:
                raise ValueError("codex_home path required for Codex accounts")
            acc_id = f"codex_{codex_home.split('/')[-1]}"
            account = __import__('server.account_manager', fromlist=['Account']).Account(
                id=acc_id,
                provider=provider,
                codex_home=codex_home,
                email=email
            )
            self.account_manager.accounts[acc_id] = account
            self.account_manager._save_accounts()
        else:
            acc_id = self.account_manager.add_account(provider, credential, email)

        self._initialize_adapters()
        return acc_id


# Global instance
_gateway: Optional[OrchestratorGateway] = None

def get_orchestrator_gateway() -> OrchestratorGateway:
    """Get or create global gateway"""
    global _gateway
    if _gateway is None:
        _gateway = OrchestratorGateway()
    return _gateway
