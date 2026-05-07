from __future__ import annotations

import argparse
import base64
import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODEX_HOME = Path.home() / ".codex"
CODEX_AUTH_FILE = CODEX_HOME / "auth.json"
OPENCODE_AUTH_FILE = Path.home() / ".local" / "share" / "opencode" / "auth.json"
ACCOUNTS_DIR = PROJECT_ROOT / "state" / "codex-accounts"
REGISTRY_FILE = ACCOUNTS_DIR / "registry.json"
DEFAULT_SLOTS = ["atlas", "forge", "spark", "shield", "nexus"]
AUTH_SOURCES = {
    "codex": CODEX_AUTH_FILE,
    "opencode": OPENCODE_AUTH_FILE,
}


@dataclass
class AccountSummary:
    slot: str
    account_id: str | None
    email: str | None
    name: str | None
    saved_at: str | None
    note: str | None
    auth_source: str
    source: Path


def ensure_layout() -> None:
    ACCOUNTS_DIR.mkdir(parents=True, exist_ok=True)
    if not REGISTRY_FILE.exists():
        REGISTRY_FILE.write_text("{}", encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def auth_snapshot_path(slot: str) -> Path:
    return ACCOUNTS_DIR / f"{slot}.json"


def decode_jwt_payload(token: str | None) -> dict:
    if not token or token.count(".") < 2:
        return {}

    payload = token.split(".")[1]
    payload += "=" * (-len(payload) % 4)
    try:
        return json.loads(base64.urlsafe_b64decode(payload.encode()).decode())
    except Exception:
        return {}


def detect_auth_source(data: dict) -> str:
    if isinstance(data.get("tokens"), dict):
        return "codex"
    if isinstance(data.get("openai"), dict):
        return "opencode"
    raise ValueError("Unsupported auth file format")


def read_claims_from_auth(path: Path) -> dict:
    data = load_json(path)
    auth_source = detect_auth_source(data)
    if auth_source == "codex":
        tokens = data.get("tokens") or {}
        token = tokens.get("id_token") or tokens.get("access_token")
        return decode_jwt_payload(token)

    openai_auth = data.get("openai") or {}
    return decode_jwt_payload(openai_auth.get("access"))


def extract_account_id(data: dict, auth_source: str, claims: dict) -> str | None:
    if auth_source == "codex":
        tokens = data.get("tokens") or {}
        return tokens.get("account_id")

    openai_auth = data.get("openai") or {}
    auth_claims = claims.get("https://api.openai.com/auth") or {}
    return openai_auth.get("accountId") or auth_claims.get("chatgpt_account_id")


def extract_email(claims: dict) -> str | None:
    profile_claims = claims.get("https://api.openai.com/profile") or {}
    return claims.get("email") or profile_claims.get("email")


def extract_name(claims: dict) -> str | None:
    profile_claims = claims.get("https://api.openai.com/profile") or {}
    return claims.get("name") or profile_claims.get("name")


def load_registry() -> dict:
    ensure_layout()
    return load_json(REGISTRY_FILE)


def save_registry(registry: dict) -> None:
    save_json(REGISTRY_FILE, registry)


def summarize_auth(path: Path, slot: str, note: str | None = None) -> AccountSummary:
    data = load_json(path)
    claims = read_claims_from_auth(path)
    auth_source = detect_auth_source(data)
    account_id = extract_account_id(data, auth_source, claims)
    registry = load_registry()
    meta = registry.get(slot, {})
    return AccountSummary(
        slot=slot,
        account_id=account_id,
        email=extract_email(claims) or meta.get("email"),
        name=extract_name(claims) or meta.get("name"),
        saved_at=meta.get("saved_at"),
        note=note if note is not None else meta.get("note"),
        auth_source=meta.get("auth_source") or auth_source,
        source=path,
    )


def short_account_id(account_id: str | None) -> str:
    if not account_id:
        return "-"
    return f"{account_id[:8]}...{account_id[-4:]}"


def mask_email(email: str | None) -> str:
    if not email or "@" not in email:
        return "-"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[0] + "*"
    else:
        masked_local = local[:2] + "*" * max(2, len(local) - 4) + local[-2:]
    return f"{masked_local}@{domain}"


def get_auth_file(auth_source: str) -> Path:
    try:
        return AUTH_SOURCES[auth_source]
    except KeyError as exc:
        raise ValueError(f"Unknown auth source: {auth_source}") from exc


def resolve_auth_source(source_hint: str) -> tuple[str, Path]:
    available = {
        name: path
        for name, path in AUTH_SOURCES.items()
        if path.exists()
    }
    if source_hint != "auto":
        path = get_auth_file(source_hint)
        if not path.exists():
            raise FileNotFoundError(f"Auth file not found: {path}")
        return source_hint, path

    if not available:
        checked_paths = ", ".join(str(path) for path in AUTH_SOURCES.values())
        raise FileNotFoundError(f"No auth file found. Checked: {checked_paths}")

    if len(available) == 1:
        name, path = next(iter(available.items()))
        return name, path

    account_ids: dict[str, str | None] = {}
    for name, path in available.items():
        try:
            summary = summarize_auth(path, "current")
            account_ids[name] = summary.account_id
        except Exception:
            account_ids[name] = None

    unique_ids = {value for value in account_ids.values() if value}
    if len(unique_ids) <= 1:
        if "codex" in available:
            return "codex", available["codex"]
        name, path = next(iter(available.items()))
        return name, path

    available_text = ", ".join(f"{name}={path}" for name, path in available.items())
    raise RuntimeError(
        f"Multiple auth sources found with different accounts. Use --from codex or --from opencode. Sources: {available_text}"
    )


def current_auth_summary(source_hint: str = "auto") -> AccountSummary:
    auth_source, auth_path = resolve_auth_source(source_hint)
    return summarize_auth(auth_path, "current", note=auth_source)


def add_account(slot: str, note: str | None, source_hint: str) -> None:
    auth_source, auth_path = resolve_auth_source(source_hint)
    ensure_layout()
    destination = auth_snapshot_path(slot)
    shutil.copy2(auth_path, destination)

    current = summarize_auth(destination, slot, note)
    registry = load_registry()
    registry[slot] = {
        "account_id": current.account_id,
        "email": current.email or "",
        "name": current.name or "",
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "note": note or "",
        "auth_source": auth_source,
    }
    save_registry(registry)

    print(f"Saved active {auth_source} auth into slot '{slot}'.")
    print(f"Account ID: {short_account_id(current.account_id)}")
    if current.email:
        print(f"Email: {current.email}")
    if note:
        print(f"Note: {note}")


def list_accounts(show_emails: bool = False) -> None:
    ensure_layout()
    registry = load_registry()
    current_ids: dict[str, str | None] = {}
    for auth_source in AUTH_SOURCES:
        try:
            current_ids[auth_source] = current_auth_summary(auth_source).account_id
        except Exception:
            current_ids[auth_source] = None

    slots = sorted(set(DEFAULT_SLOTS) | set(registry.keys()))
    rows: list[str] = []
    for slot in slots:
        path = auth_snapshot_path(slot)
        if not path.exists():
            rows.append(f"{slot:<8}  EMPTY")
            continue

        summary = summarize_auth(path, slot)
        active = "ACTIVE" if current_ids.get(summary.auth_source) and summary.account_id == current_ids.get(summary.auth_source) else ""
        saved_at = summary.saved_at or "-"
        note = summary.note or "-"
        email = summary.email if show_emails else mask_email(summary.email)
        rows.append(
            f"{slot:<8}  {summary.auth_source:<8}  {short_account_id(summary.account_id):<16}  {active:<6}  {email:<28}  {saved_at:<32}  {note}"
        )

    print("slot      source    account_id        state   email                         saved_at                         note")
    print("-" * 104)
    for row in rows:
        print(row)


def switch_account(slot: str) -> None:
    source = auth_snapshot_path(slot)
    if not source.exists():
        raise FileNotFoundError(f"Saved slot not found: {slot}")

    ensure_layout()
    summary = summarize_auth(source, slot)
    target = get_auth_file(summary.auth_source)
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = ACCOUNTS_DIR / f"_last_active_{summary.auth_source}_backup.json"
    if target.exists():
        shutil.copy2(target, backup)
    shutil.copy2(source, target)

    print(f"Switched active {summary.auth_source} auth to '{slot}'.")
    print(f"Account ID: {short_account_id(summary.account_id)}")
    if summary.email:
        print(f"Email: {summary.email}")
    print("Restart the matching app/CLI if it is already open.")


def show_current(source_hint: str) -> None:
    summary = current_auth_summary(source_hint)
    print(f"Current account ID: {short_account_id(summary.account_id)}")
    print(f"Source: {summary.auth_source}")
    print(f"Auth file: {summary.source}")


def remove_account(slot: str) -> None:
    path = auth_snapshot_path(slot)
    registry = load_registry()
    if path.exists():
        path.unlink()
    registry.pop(slot, None)
    save_registry(registry)
    print(f"Removed slot '{slot}'.")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Manage multiple local Codex auth snapshots.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add_parser = sub.add_parser("add", help="Save current active auth into a named slot")
    add_parser.add_argument("slot", help="Slot name, e.g. atlas/forge/spark/shield/nexus")
    add_parser.add_argument("--note", default="", help="Optional note for this slot")
    add_parser.add_argument(
        "--from",
        dest="auth_source",
        choices=["auto", "codex", "opencode"],
        default="auto",
        help="Which active auth file to snapshot",
    )

    list_parser = sub.add_parser("list", help="List saved slots")
    list_parser.add_argument(
        "--emails",
        action="store_true",
        help="Show full email addresses instead of masked ones",
    )
    switch_parser = sub.add_parser("switch", help="Replace active auth.json from a saved slot")
    switch_parser.add_argument("slot", help="Saved slot name")

    current_parser = sub.add_parser("current", help="Show current active account id")
    current_parser.add_argument(
        "--from",
        dest="auth_source",
        choices=["auto", "codex", "opencode"],
        default="auto",
        help="Which active auth file to inspect",
    )

    remove_parser = sub.add_parser("remove", help="Delete a saved slot")
    remove_parser.add_argument("slot", help="Saved slot name")

    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    try:
        args = parse_args(argv)
        if args.command == "add":
            add_account(args.slot, args.note or None, args.auth_source)
        elif args.command == "list":
            list_accounts(show_emails=bool(getattr(args, "emails", False)))
        elif args.command == "switch":
            switch_account(args.slot)
        elif args.command == "current":
            show_current(args.auth_source)
        elif args.command == "remove":
            remove_account(args.slot)
        else:
            raise ValueError(f"Unknown command: {args.command}")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
