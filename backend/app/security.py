from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any


class TokenError(ValueError):
    pass


def _base64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _decode_base64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def hash_password(password: str, *, iterations: int = 310_000) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, iterations
    )
    return f"pbkdf2_sha256${iterations}${_base64url(salt)}${_base64url(derived)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algorithm, iterations, salt, expected = stored.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        derived = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _decode_base64url(salt),
            int(iterations),
        )
        return hmac.compare_digest(_base64url(derived), expected)
    except (ValueError, TypeError):
        return False


def create_token(
    payload: dict[str, Any], secret: str, ttl_minutes: int
) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    claims = {
        **payload,
        "iat": int(time.time()),
        "exp": int(time.time()) + ttl_minutes * 60,
    }
    encoded_header = _base64url(
        json.dumps(header, separators=(",", ":")).encode("utf-8")
    )
    encoded_payload = _base64url(
        json.dumps(claims, separators=(",", ":")).encode("utf-8")
    )
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(
        secret.encode("utf-8"), signing_input, hashlib.sha256
    ).digest()
    return f"{encoded_header}.{encoded_payload}.{_base64url(signature)}"


def decode_token(token: str, secret: str) -> dict[str, Any]:
    try:
        encoded_header, encoded_payload, encoded_signature = token.split(".")
        signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
        expected = hmac.new(
            secret.encode("utf-8"), signing_input, hashlib.sha256
        ).digest()
        if not hmac.compare_digest(
            expected, _decode_base64url(encoded_signature)
        ):
            raise TokenError("invalid_signature")
        payload = json.loads(_decode_base64url(encoded_payload))
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise TokenError("token_expired")
        return payload
    except (ValueError, KeyError, json.JSONDecodeError) as error:
        if isinstance(error, TokenError):
            raise
        raise TokenError("invalid_token") from error
