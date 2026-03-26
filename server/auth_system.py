import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Protocol

import bcrypt


MIN_PASSWORD_LENGTH = 12
MAX_IDENTIFIER_LENGTH = 254
GENERIC_LOGIN_ERROR = "Invalid credentials."
GENERIC_REGISTRATION_ERROR = "Account could not be created."
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15
RATE_LIMIT_WINDOW_SECONDS = 300
RATE_LIMIT_MAX_ATTEMPTS = 10
DUMMY_PASSWORD_HASH = bcrypt.hashpw(b"dummy-password", bcrypt.gensalt()).decode("utf-8")
LOGIN_ATTEMPTS: dict[str, list[datetime]] = {}


class UserRepo(Protocol):
    def get_user_by_email(self, email: str) -> Optional[dict]:
        ...

    def get_user_by_username(self, username: str) -> Optional[dict]:
        ...

    def create_user(self, data: dict) -> dict:
        ...

    def record_failed_login(self, user: dict) -> None:
        ...

    def reset_failed_logins(self, user: dict) -> None:
        ...


class AuthError(Exception):
    def __init__(self, message: str, *, code: str = "auth_error"):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AuthResult:
    user_id: str
    username: str
    email: str
    created_at: str


class InMemoryUserRepo:
    def __init__(self):
        self._users_by_username: dict[str, dict] = {}
        self._users_by_email: dict[str, dict] = {}

    def get_user_by_email(self, email: str) -> Optional[dict]:
        return self._users_by_email.get(email)

    def get_user_by_username(self, username: str) -> Optional[dict]:
        return self._users_by_username.get(username)

    def create_user(self, data: dict) -> dict:
        if data["username"] in self._users_by_username or data["email"] in self._users_by_email:
            raise AuthError(GENERIC_REGISTRATION_ERROR, code="registration_failed")

        stored = dict(data)
        self._users_by_username[stored["username"]] = stored
        self._users_by_email[stored["email"]] = stored
        return stored

    def record_failed_login(self, user: dict) -> None:
        stored = self._users_by_username.get(user["username"])
        if not stored:
            return
        stored["failed_login_attempts"] = stored.get("failed_login_attempts", 0) + 1
        if stored["failed_login_attempts"] >= MAX_FAILED_ATTEMPTS:
            stored["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)).isoformat()

    def reset_failed_logins(self, user: dict) -> None:
        stored = self._users_by_username.get(user["username"])
        if not stored:
            return
        stored["failed_login_attempts"] = 0
        stored["locked_until"] = None


def normalize_username(username: str) -> str:
    value = username.strip().lower()
    if not value:
        raise AuthError("Username is required.", code="username_required")
    if len(value) < 3 or len(value) > 32:
        raise AuthError("Username must be between 3 and 32 characters.", code="username_length")
    if not re.fullmatch(r"[a-z0-9_.-]+", value):
        raise AuthError(
            "Username may contain lowercase letters, numbers, dots, dashes, and underscores only.",
            code="username_invalid",
        )
    return value


def normalize_username_for_lookup(username: str) -> Optional[str]:
    value = username.strip().lower()
    if not value or len(value) < 3 or len(value) > 32:
        return None
    if not re.fullmatch(r"[a-z0-9_.-]+", value):
        return None
    return value


def normalize_email(email: str) -> str:
    value = email.strip().lower()
    if not value:
        raise AuthError("Email is required.", code="email_required")
    if len(value) > MAX_IDENTIFIER_LENGTH:
        raise AuthError("Email is too long.", code="email_length")
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", value):
        raise AuthError("Email format is invalid.", code="email_invalid")
    return value


def validate_password(password: str) -> None:
    if not password:
        raise AuthError("Password is required.", code="password_required")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long.",
            code="password_length",
        )
    if password.isspace():
        raise AuthError("Password cannot be whitespace only.", code="password_invalid")
    checks = {
        "uppercase": any(char.isupper() for char in password),
        "lowercase": any(char.islower() for char in password),
        "digit": any(char.isdigit() for char in password),
    }
    if not all(checks.values()):
        raise AuthError(
            "Password must include uppercase, lowercase, and numeric characters.",
            code="password_complexity",
        )
    if not any(not char.isalnum() for char in password):
        raise AuthError(
            "Password must include at least one special character.",
            code="password_complexity",
        )


def hash_password(password: str) -> str:
    validate_password(password)
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password or not password_hash:
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_result(user_record: dict) -> AuthResult:
    return AuthResult(
        user_id=user_record["user_id"],
        username=user_record["username"],
        email=user_record["email"],
        created_at=user_record["created_at"],
    )


def _is_locked(user_record: dict) -> bool:
    locked_until = user_record.get("locked_until")
    if not locked_until:
        return False
    try:
        return datetime.fromisoformat(locked_until) > datetime.now(timezone.utc)
    except ValueError:
        return False


def _record_failed_login(user_repo: UserRepo, user_record: Optional[dict]) -> None:
    if user_record and hasattr(user_repo, "record_failed_login"):
        user_repo.record_failed_login(user_record)


def _reset_failed_logins(user_repo: UserRepo, user_record: dict) -> None:
    if hasattr(user_repo, "reset_failed_logins"):
        user_repo.reset_failed_logins(user_record)


def _consume_login_attempt(password: str, password_hash: str) -> bool:
    return verify_password(password, password_hash)


def _enforce_rate_limit(identifier: str) -> None:
    now = datetime.now(timezone.utc)
    attempts = LOGIN_ATTEMPTS.get(identifier, [])
    attempts = [item for item in attempts if (now - item).total_seconds() < RATE_LIMIT_WINDOW_SECONDS]
    if len(attempts) >= RATE_LIMIT_MAX_ATTEMPTS:
        raise AuthError("Too many login attempts. Please try again later.", code="rate_limited")
    attempts.append(now)
    LOGIN_ATTEMPTS[identifier] = attempts


def _clear_rate_limit(identifier: str) -> None:
    LOGIN_ATTEMPTS.pop(identifier, None)


def register_user(username: str, email: str, password: str, user_repo: UserRepo) -> AuthResult:
    normalized_username = normalize_username(username)
    normalized_email = normalize_email(email)

    username_exists = user_repo.get_user_by_username(normalized_username)
    email_exists = user_repo.get_user_by_email(normalized_email)
    if username_exists or email_exists:
        raise AuthError(GENERIC_REGISTRATION_ERROR, code="registration_failed")

    password_hash = hash_password(password)
    user_record = user_repo.create_user(
        {
            "user_id": secrets.token_hex(16),
            "username": normalized_username,
            "email": normalized_email,
            "password_hash": password_hash,
            "created_at": _utc_now(),
            "failed_login_attempts": 0,
            "locked_until": None,
        }
    )
    return _build_result(user_record)


def login_user(identifier: str, password: str, user_repo: UserRepo) -> AuthResult:
    if not identifier or not identifier.strip():
        raise AuthError(GENERIC_LOGIN_ERROR, code="invalid_credentials")
    if not password:
        raise AuthError(GENERIC_LOGIN_ERROR, code="invalid_credentials")

    normalized_identifier = identifier.strip().lower()
    _enforce_rate_limit(normalized_identifier)
    user_record_by_email = user_repo.get_user_by_email(normalized_identifier) if "@" in normalized_identifier else None
    normalized_username = normalize_username_for_lookup(normalized_identifier)
    user_record_by_username = user_repo.get_user_by_username(normalized_username) if normalized_username else None

    user_record = user_record_by_email or user_record_by_username
    stored_hash = user_record.get("password_hash", DUMMY_PASSWORD_HASH) if user_record else DUMMY_PASSWORD_HASH
    password_ok = _consume_login_attempt(password, stored_hash)

    if not user_record or _is_locked(user_record) or not password_ok:
        _record_failed_login(user_repo, user_record)
        raise AuthError(GENERIC_LOGIN_ERROR, code="invalid_credentials")

    _reset_failed_logins(user_repo, user_record)
    _clear_rate_limit(normalized_identifier)
    return _build_result(user_record)


if __name__ == "__main__":
    repo = InMemoryUserRepo()
    created = register_user("alice", "alice@example.com", "SecurePassword123!", repo)
    print(created)
    logged_in = login_user("alice@example.com", "SecurePassword123!", repo)
    print(logged_in)
