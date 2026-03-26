from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import bcrypt


MIN_PASSWORD_LENGTH = 8


class AuthError(Exception):
    def __init__(self, message: str, *, code: str = "auth_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass(frozen=True)
class AuthenticatedUser:
    id: Any
    username: str
    email: str


def normalize_email(email: str) -> str:
    return email.strip().lower()


def normalize_username(username: str) -> str:
    return username.strip()


def hash_password(password: str) -> str:
    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def register_user(username: str, email: str, password: str, user_repo: Any) -> dict[str, Any]:
    normalized_username = normalize_username(username)
    normalized_email = normalize_email(email)
    _validate_registration_input(normalized_username, normalized_email, password)

    if user_repo.get_user_by_email(normalized_email):
        raise AuthError("Email is already registered.", code="email_taken")

    if user_repo.get_user_by_username(normalized_username):
        raise AuthError("Username is already in use.", code="username_taken")

    user_data = {
        "username": normalized_username,
        "email": normalized_email,
        "password_hash": hash_password(password),
    }

    created_user = user_repo.create_user(user_data)
    return _sanitize_user(created_user, fallback=user_data)


def login_user(identifier: str, password: str, user_repo: Any) -> AuthenticatedUser:
    normalized_identifier = identifier.strip()
    if not normalized_identifier or not password:
        raise AuthError("Invalid credentials.", code="invalid_credentials")

    user = _get_user_by_identifier(normalized_identifier, user_repo)
    if not user:
        raise AuthError("Invalid credentials.", code="invalid_credentials")

    password_hash = _read_user_field(user, "password_hash")
    if not verify_password(password, password_hash):
        raise AuthError("Invalid credentials.", code="invalid_credentials")

    return AuthenticatedUser(
        id=_read_user_field(user, "id"),
        username=_read_user_field(user, "username"),
        email=_read_user_field(user, "email"),
    )


def _validate_registration_input(username: str, email: str, password: str) -> None:
    if not username:
        raise AuthError("Username is required.", code="username_required")
    if not email:
        raise AuthError("Email is required.", code="email_required")
    if not password:
        raise AuthError("Password is required.", code="password_required")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters.",
            code="password_too_short",
        )


def _get_user_by_identifier(identifier: str, user_repo: Any) -> Optional[Any]:
    normalized_email = normalize_email(identifier)
    user = user_repo.get_user_by_email(normalized_email)
    if user:
        return user

    normalized_username = normalize_username(identifier)
    return user_repo.get_user_by_username(normalized_username)


def _sanitize_user(user: Any, *, fallback: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    source = user or fallback or {}
    return {
        "id": _read_user_field(source, "id"),
        "username": _read_user_field(source, "username"),
        "email": _read_user_field(source, "email"),
    }


def _read_user_field(user: Any, field_name: str) -> Any:
    if isinstance(user, dict):
        return user.get(field_name)
    return getattr(user, field_name, None)
