"""
Orchestrator Commands for JARVIS Bridge
/orchestrator, /switch-account, /account-status commands
"""

from server.orchestrator_gateway import get_orchestrator_gateway

async def handle_orchestrator_status(chat_id: int, telegram_bot) -> str:
    """
    /orchestrator-status — Show account orchestration dashboard
    """
    gateway = get_orchestrator_gateway()
    status = gateway.get_status()

    response = "🔀 **Account Orchestrator Status**\n\n"

    for provider, data in status["accounts"].items():
        response += f"📍 **{provider.upper()}**\n"
        response += f"  Total accounts: {data['total']}\n"

        if data['active_account']:
            response += f"  🟢 Active: {data['active_email']}\n"
        else:
            response += f"  🔴 No active account\n"

        for acc in data['accounts']:
            icon = "🟢" if acc['status'] == "active" else "⚫"
            response += f"    {icon} {acc['id']}: {acc['email']} ({acc['status']})\n"

        response += "\n"

    response += "💡 Use `/switch-account <account_id>` to switch\n"
    response += "➕ Use `/add-account <provider> <key> <email>` to add\n"

    return response


async def handle_switch_account(chat_id: int, args: str, telegram_bot) -> str:
    """
    /switch-account <account_id> — Switch to different account
    Example: /switch-account codex_1
    """
    if not args:
        return "❌ Usage: `/switch-account <account_id>`\nExample: `/switch-account codex_1`"

    account_id = args.strip()
    gateway = get_orchestrator_gateway()

    success = gateway.switch_account(account_id)

    if success:
        status = gateway.get_status()
        provider = account_id.split('_')[0]
        active = status['accounts'].get(provider, {}).get('active_account')
        email = status['accounts'].get(provider, {}).get('active_email')

        return f"✅ Switched to **{account_id}**\n📧 {email}\n\nProvider {provider.upper()} now routing through this account."
    else:
        return f"❌ Failed to switch to {account_id}"


async def handle_add_account(chat_id: int, args: str, telegram_bot) -> str:
    """
    /add-account <provider> <api_key> <email> — Add new account
    Example: /add-account codex sk-... admin@example.com
    """
    parts = args.strip().split()

    if len(parts) < 3:
        return "❌ Usage: `/add-account <provider> <api_key> <email>`\nExample: `/add-account codex sk-... admin@example.com`"

    provider, api_key, email = parts[0], parts[1], parts[2]

    if provider not in ["codex", "claude", "gemini"]:
        return f"❌ Unknown provider: {provider}\nSupported: codex, claude, gemini"

    gateway = get_orchestrator_gateway()
    acc_id = gateway.add_account(provider, api_key, email)

    return f"✅ Added account **{acc_id}**\n📧 {email}\n🔑 Provider: {provider.upper()}"


async def handle_account_list(chat_id: int, args: str, telegram_bot) -> str:
    """
    /account-list [provider] — List all accounts
    """
    gateway = get_orchestrator_gateway()
    accounts = gateway.account_manager.get_all_accounts()

    if not accounts:
        return "❌ No accounts configured\nUse `/add-account` to add one"

    response = "📋 **All Accounts**\n\n"

    for acc in accounts:
        icon = "🟢" if acc.status == "active" else "⚫"
        response += f"{icon} **{acc.id}**\n"
        response += f"   Provider: {acc.provider}\n"
        response += f"   Email: {acc.email}\n"
        response += f"   Status: {acc.status}\n"
        response += f"   Last used: {acc.last_used or 'Never'}\n\n"

    return response
