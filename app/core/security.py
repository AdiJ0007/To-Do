from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass

from app.core.config import get_settings


PASSWORD_HASH_ITERATIONS = 210_000
TOKEN_SEPARATOR = "."
OAUTH_STATE_TTL_SECONDS = 600


@dataclass(frozen=True)
class TokenPayload:
    user_id: int
    expires_at: int


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )
    return f"pbkdf2_sha256${PASSWORD_HASH_ITERATIONS}${_b64encode(salt)}${_b64encode(derived_key)}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, key_text = password_hash.split("$", 3)
    except ValueError:
        return False

    if algorithm != "pbkdf2_sha256":
        return False

    iterations = int(iterations_text)
    salt = _b64decode(salt_text)
    expected_key = _b64decode(key_text)
    derived_key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
    )
    return hmac.compare_digest(derived_key, expected_key)


def create_access_token(user_id: int, expires_in_seconds: int = 60 * 60 * 24 * 7) -> str:
    settings = get_settings()
    payload = {
        "user_id": user_id,
        "expires_at": int(time.time()) + expires_in_seconds,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_text = _b64encode(payload_bytes)
    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload_text.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload_text}{TOKEN_SEPARATOR}{_b64encode(signature)}"


def decode_access_token(token: str) -> TokenPayload | None:
    settings = get_settings()
    try:
        payload_text, signature_text = token.split(TOKEN_SEPARATOR, 1)
        expected_signature = hmac.new(
            settings.secret_key.encode("utf-8"),
            payload_text.encode("ascii"),
            hashlib.sha256,
        ).digest()
        actual_signature = _b64decode(signature_text)
        if not hmac.compare_digest(expected_signature, actual_signature):
            return None

        payload = json.loads(_b64decode(payload_text).decode("utf-8"))
        payload_obj = TokenPayload(
            user_id=int(payload["user_id"]),
            expires_at=int(payload["expires_at"]),
        )
        if payload_obj.expires_at < int(time.time()):
            return None
        return payload_obj
    except (ValueError, KeyError, json.JSONDecodeError, TypeError):
        return None


def create_oauth_state() -> str:
    settings = get_settings()
    payload = {
        "nonce": secrets.token_urlsafe(16),
        "expires_at": int(time.time()) + OAUTH_STATE_TTL_SECONDS,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    payload_text = _b64encode(payload_bytes)
    signature = hmac.new(
        settings.secret_key.encode("utf-8"),
        f"oauth-state:{payload_text}".encode("ascii"),
        hashlib.sha256,
    ).digest()
    return f"{payload_text}{TOKEN_SEPARATOR}{_b64encode(signature)}"


def verify_oauth_state(state_token: str) -> bool:
    settings = get_settings()
    try:
        payload_text, signature_text = state_token.split(TOKEN_SEPARATOR, 1)
        expected_signature = hmac.new(
            settings.secret_key.encode("utf-8"),
            f"oauth-state:{payload_text}".encode("ascii"),
            hashlib.sha256,
        ).digest()
        actual_signature = _b64decode(signature_text)
        if not hmac.compare_digest(expected_signature, actual_signature):
            return False

        payload = json.loads(_b64decode(payload_text).decode("utf-8"))
        return int(payload["expires_at"]) >= int(time.time())
    except (ValueError, KeyError, json.JSONDecodeError, TypeError):
        return False
