from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from server import codex_auth_refresher as refresher


def _jwt(payload: dict[str, object]) -> str:
    def _encode(part: dict[str, object]) -> str:
        raw = json.dumps(part, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return f"{_encode({'alg': 'none', 'typ': 'JWT'})}.{_encode(payload)}."


def _auth_payload(*, hours_until_expiry: int, client_id: str = "client-123") -> dict[str, object]:
    expires_at = datetime.now(timezone.utc) + timedelta(hours=hours_until_expiry)
    token = _jwt(
        {
            "exp": int(expires_at.timestamp()),
            "client_id": client_id,
        }
    )
    return {
        "auth_mode": "chatgpt",
        "last_refresh": "2026-04-02T00:00:00+00:00",
        "tokens": {
            "access_token": token,
            "refresh_token": "oaistb_rt_secret",
            "id_token": "id-secret",
        },
    }


class _DummyResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def read(self) -> bytes:
        return json.dumps(self._payload, ensure_ascii=False).encode("utf-8")

    def __enter__(self) -> "_DummyResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False


def test_get_access_token_expiry_and_client_id() -> None:
    expected_expiry = datetime(2026, 4, 20, 12, 0, tzinfo=timezone.utc)
    token = _jwt({"exp": int(expected_expiry.timestamp()), "client_id": "client-xyz"})

    assert refresher.get_access_token_expiry(token) == expected_expiry
    assert refresher.get_client_id(token) == "client-xyz"


def test_should_refresh_when_token_is_within_threshold() -> None:
    now = datetime(2026, 4, 18, 9, 0, tzinfo=timezone.utc)
    expiring = _jwt({"exp": int((now + timedelta(hours=24)).timestamp()), "client_id": "client-123"})
    fresh = _jwt({"exp": int((now + timedelta(hours=96)).timestamp()), "client_id": "client-123"})

    assert refresher.should_refresh_payload({"tokens": {"access_token": expiring}}, now=now)
    assert not refresher.should_refresh_payload({"tokens": {"access_token": fresh}}, now=now)


def test_write_auth_payload_is_atomic(tmp_path: Path) -> None:
    auth_path = tmp_path / ".codex" / "auth.json"
    payload = _auth_payload(hours_until_expiry=72)

    refresher.write_auth_payload(auth_path, payload)

    assert auth_path.exists()
    assert json.loads(auth_path.read_text(encoding="utf-8"))["tokens"]["refresh_token"] == "oaistb_rt_secret"
    assert not list(auth_path.parent.glob("*.tmp"))


def test_sanitize_auth_payload_redacts_secret_fields() -> None:
    sanitized = refresher.sanitize_auth_payload(_auth_payload(hours_until_expiry=72))
    serialized = json.dumps(sanitized, ensure_ascii=False)

    assert "oaistb_rt_secret" not in serialized
    assert "access_token" not in serialized
    assert "refresh_token" not in serialized
    assert "id_token" not in serialized


def test_refresh_auth_file_updates_tokens_and_last_refresh(tmp_path: Path, monkeypatch) -> None:
    auth_path = tmp_path / "state" / "codex-accounts" / "atlas" / ".codex" / "auth.json"
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    current_payload = _auth_payload(hours_until_expiry=1, client_id="client-abc")
    auth_path.write_text(json.dumps(current_payload, ensure_ascii=False, indent=2), encoding="utf-8")

    new_access_token = _jwt(
        {
            "exp": int(datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc).timestamp()),
            "client_id": "client-abc",
        }
    )

    def _fake_urlopen(request_obj, timeout: float = 0.0):
        body = request_obj.data.decode("utf-8")
        assert "grant_type=refresh_token" in body
        assert "client_id=client-abc" in body
        return _DummyResponse(
            {
                "access_token": new_access_token,
                "refresh_token": "oaistb_rt_new_secret",
                "id_token": "id-new-secret",
            }
        )

    monkeypatch.setattr(refresher.request, "urlopen", _fake_urlopen)

    refreshed = refresher.refresh_auth_file(
        auth_path,
        now=datetime(2026, 4, 18, 10, 0, tzinfo=timezone.utc),
    )

    saved = json.loads(auth_path.read_text(encoding="utf-8"))
    assert refreshed["tokens"]["access_token"] == new_access_token
    assert saved["tokens"]["refresh_token"] == "oaistb_rt_new_secret"
    assert saved["last_refresh"] == "2026-04-18T10:00:00+00:00"
